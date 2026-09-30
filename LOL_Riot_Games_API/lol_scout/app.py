"""LoL Scout v3 主窗口"""

from __future__ import annotations

import queue
import threading
import webbrowser
from collections import Counter
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk
from customtkinter import CTkImage

from . import __version__, fuzzy
from .config import (COLORS, DB_PATH, LEGACY_HISTORY_PATH, PLATFORM_TO_REGIONAL, format_duration,
                     load_config, save_config)
from .ddragon import DataDragon
from .lcu import LCUError, detect_game_exe
from .models import LiveGame, LivePlayer, Match
from .opgg import web_links
from .service import Profile, ScoutError, ScoutService
from .spectator import SpectateParams
from .storage import Storage
from .widgets import (EntryVar, LivePlayerRow, MatchCard, Suggestions, Toast, font, kda_color,
                      participant_row, rank_text, tier_color)

PLATFORMS = list(PLATFORM_TO_REGIONAL.keys())
QUEUE_FILTERS = {"全部": None, "排位": {420, 440}, "匹配": {400, 430, 480, 490}, "大乱斗": {450}, "其它": "other"}
PHASE_CN = {
    "None": "空闲", "Lobby": "房间中", "Matchmaking": "匹配中", "ReadyCheck": "等待接受",
    "ChampSelect": "选人阶段", "GameStart": "游戏启动中", "InProgress": "游戏中", "Reconnect": "等待重连",
    "WaitingForStats": "等待结算", "PreEndOfGame": "结算中", "EndOfGame": "对局结束",
}


class LoLScoutApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title(f"LoL Scout v{__version__} · 战绩 / 观战 / OP.GG")
        self.geometry("1360x860")
        self.minsize(1120, 720)
        self.configure(fg_color=COLORS["bg_dark"])

        self.config_data = load_config()
        self.storage = Storage(DB_PATH)
        self.storage.import_legacy_history(LEGACY_HISTORY_PATH)
        self.storage.purge_expired()
        self.dd = DataDragon(self.storage, self.config_data.get("locale", "zh_CN"))
        self.svc = ScoutService(self.config_data, self.storage, self.dd)

        self._ui_queue: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self._img_pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="img")
        self._images: Dict[tuple, CTkImage] = {}
        self._pending_img: Dict[tuple, List[ctk.CTkLabel]] = {}
        self._busy = 0

        self.profile: Optional[Profile] = None
        self.matches: List[Match] = []
        self.cards: List[MatchCard] = []
        self.live: Optional[LiveGame] = None
        self.live_rows: Dict[int, LivePlayerRow] = {}
        self._gen = 0
        self._suggest_job: Optional[str] = None
        self._filter_job: Optional[str] = None
        self._last_phase = ""
        self._lcu_polling = False

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(20, self._drain)
        self.run_async(self._warmup, ok=lambda _: self._on_warm())
        self.after(1500, self._poll_lcu)

    # ================================================================ async
    def post(self, fn: Callable[[], None]) -> None:
        """工作线程 -> UI 线程"""
        self._ui_queue.put(fn)

    def _drain(self) -> None:
        try:
            for _ in range(200):
                fn = self._ui_queue.get_nowait()
                try:
                    fn()
                except Exception as exc:  # UI 回调异常不应让循环停止
                    print("UI callback error:", exc)
        except queue.Empty:
            pass
        self.after(16, self._drain)

    def run_async(self, fn: Callable[[], Any], ok: Optional[Callable[[Any], None]] = None,
                  err: Optional[Callable[[Exception], None]] = None, busy: str = "") -> Future:
        if busy:
            self._set_busy(busy, +1)

        def done(f: Future) -> None:
            def cb() -> None:
                if busy:
                    self._set_busy("", -1)
                exc = f.exception()
                if exc is not None:
                    (err or self._default_err)(exc)
                elif ok:
                    ok(f.result())
            self.post(cb)

        fut = self.svc.pool.submit(fn)
        fut.add_done_callback(done)
        return fut

    def _default_err(self, exc: Exception) -> None:
        self.toast(str(exc), "error")
        self.set_status(f"错误：{exc}")

    # ================================================================ images
    def set_image(self, label: ctk.CTkLabel, kind: str, ident: Any, size: int) -> None:
        url = self.dd.image_url(kind, ident)
        if not url:
            return
        key = (url, size)
        img = self._images.get(key)
        if img is not None:
            label.configure(image=img)
            return
        waiters = self._pending_img.setdefault(key, [])
        waiters.append(label)
        if len(waiters) > 1:
            return

        def work() -> None:
            pil = self.dd.load_image(url, (size * 2, size * 2))  # 2x 采样，高分屏更清晰

            def apply() -> None:
                labels = self._pending_img.pop(key, [])
                if pil is None:
                    return
                ci = CTkImage(light_image=pil, dark_image=pil, size=(size, size))
                self._images[key] = ci
                for lb in labels:
                    try:
                        if lb.winfo_exists():
                            lb.configure(image=ci)
                    except Exception:
                        pass
            self.post(apply)

        self._img_pool.submit(work)

    # ================================================================ build
    def _build(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        main = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)
        self.main = main
        self._build_header(main)
        self.tabs = ctk.CTkTabview(main, fg_color=COLORS["bg_card"], segmented_button_fg_color=COLORS["bg_card2"],
                                   segmented_button_selected_color=COLORS["accent_dark"],
                                   segmented_button_unselected_color=COLORS["bg_card2"],
                                   segmented_button_selected_hover_color=COLORS["accent"],
                                   command=self._on_tab)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 6))
        for name in ("📜 战绩", "📋 对局详情", "👁 实时观战", "🖥 客户端", "🌐 OP.GG"):
            self.tabs.add(name)
        self._build_matches_tab(self.tabs.tab("📜 战绩"))
        self._build_detail_tab(self.tabs.tab("📋 对局详情"))
        self._build_live_tab(self.tabs.tab("👁 实时观战"))
        self._build_client_tab(self.tabs.tab("🖥 客户端"))
        self._build_opgg_tab(self.tabs.tab("🌐 OP.GG"))
        self._build_statusbar(main)

    # -------------------------------------------------------------- sidebar
    def _build_sidebar(self) -> None:
        sb = ctk.CTkFrame(self, width=300, fg_color=COLORS["bg_card"], corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.pack_propagate(False)
        self.sidebar = sb

        ctk.CTkLabel(sb, text="⚔ LoL Scout", font=font(24, True), text_color=COLORS["accent"]).pack(
            anchor="w", padx=18, pady=(18, 0))
        ctk.CTkLabel(sb, text="战绩 · 模糊搜索 · 观战 · 客户端 · OP.GG", font=font(11),
                     text_color=COLORS["text_muted"]).pack(anchor="w", padx=18, pady=(0, 12))

        self.platform_var = ctk.StringVar(value=self.config_data.get("default_platform", "KR"))
        ctk.CTkOptionMenu(sb, values=PLATFORMS, variable=self.platform_var, height=32, font=font(12),
                          fg_color=COLORS["bg_card2"], button_color=COLORS["accent_dark"],
                          command=lambda v: self._save_platform(v)).pack(fill="x", padx=16)

        self.search_entry = ctk.CTkEntry(sb, height=38, font=font(13),
                                         placeholder_text="名字#Tag，可只输名字 / 模糊搜",
                                         fg_color=COLORS["bg_dark"], border_color=COLORS["border"])
        self.search_var = EntryVar(self.search_entry)
        self.search_entry.pack(fill="x", padx=16, pady=(10, 6))
        self.search_entry.bind("<KeyRelease>", self._on_search_key)
        self.search_entry.bind("<Return>", self._on_search_enter)
        self.search_entry.bind("<Down>", lambda e: self.suggest.move(1))
        self.search_entry.bind("<Up>", lambda e: self.suggest.move(-1))
        self.search_entry.bind("<Escape>", lambda e: self.suggest.hide())
        self.search_entry.bind("<FocusOut>", lambda e: self.after(200, self.suggest.hide))

        row = ctk.CTkFrame(sb, fg_color="transparent")
        row.pack(fill="x", padx=16)
        ctk.CTkButton(row, text="🔍 搜索", height=34, font=font(13, True), fg_color=COLORS["accent"],
                      hover_color=COLORS["accent_dark"], command=self.search).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="🖥 我自己", width=90, height=34, font=font(12), fg_color=COLORS["bg_card2"],
                      hover_color=COLORS["bg_hover"], command=self.search_me).pack(side="left", padx=(6, 0))

        self.profile_card = ctk.CTkFrame(sb, fg_color=COLORS["bg_card2"], corner_radius=12)
        self.profile_card.pack(fill="x", padx=16, pady=12)
        ctk.CTkLabel(self.profile_card, text="搜索一个玩家开始", font=font(12),
                     text_color=COLORS["text_muted"]).pack(pady=24)

        self.source_label = ctk.CTkLabel(sb, text="", font=font(11), justify="left", anchor="w",
                                         text_color=COLORS["text_dim"])
        self.source_label.pack(fill="x", padx=18)

        ctk.CTkLabel(sb, text="最近 / 收藏", font=font(12, True), text_color=COLORS["text_dim"]).pack(
            anchor="w", padx=18, pady=(10, 2))
        self.recent_frame = ctk.CTkScrollableFrame(sb, fg_color="transparent", height=180)
        self.recent_frame.pack(fill="both", expand=True, padx=10)

        ctk.CTkButton(sb, text="⚙ 设置", height=32, font=font(12), fg_color=COLORS["bg_card2"],
                      hover_color=COLORS["bg_hover"], command=self.open_settings).pack(fill="x", padx=16, pady=12)

        self.suggest = Suggestions(sb, self._pick_suggestion)
        self._render_recent()
        self._render_sources()

    # --------------------------------------------------------------- header
    def _build_header(self, parent) -> None:
        hd = ctk.CTkFrame(parent, fg_color="transparent")
        hd.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 8))
        hd.grid_columnconfigure(1, weight=1)
        self.head_icon = ctk.CTkLabel(hd, text="", width=56, height=56, fg_color=COLORS["bg_card"], corner_radius=12)
        self.head_icon.grid(row=0, column=0, rowspan=2, padx=(0, 12))
        self.head_title = ctk.CTkLabel(hd, text="LoL Scout", font=font(22, True), text_color=COLORS["text"], anchor="w")
        self.head_title.grid(row=0, column=1, sticky="w")
        self.head_sub = ctk.CTkLabel(hd, text="输入 Riot ID 查询战绩；启动客户端可查看自己与队友", font=font(12),
                                     text_color=COLORS["text_dim"], anchor="w")
        self.head_sub.grid(row=1, column=1, sticky="w")
        btns = ctk.CTkFrame(hd, fg_color="transparent")
        btns.grid(row=0, column=2, rowspan=2)
        self.fav_btn = ctk.CTkButton(btns, text="☆ 收藏", width=80, height=32, font=font(12),
                                     fg_color=COLORS["bg_card2"], hover_color=COLORS["bg_hover"],
                                     command=self.toggle_favorite)
        self.fav_btn.pack(side="left", padx=3)
        ctk.CTkButton(btns, text="⟳ 刷新", width=80, height=32, font=font(12), fg_color=COLORS["bg_card2"],
                      hover_color=COLORS["bg_hover"], command=self.refresh_all).pack(side="left", padx=3)
        ctk.CTkButton(btns, text="👁 观战", width=80, height=32, font=font(12, True), fg_color=COLORS["accent"],
                      hover_color=COLORS["accent_dark"], command=self.check_live).pack(side="left", padx=3)
        ctk.CTkButton(btns, text="OP.GG", width=70, height=32, font=font(12, True), fg_color=COLORS["opgg"],
                      command=lambda: self.open_link("OP.GG 主页")).pack(side="left", padx=3)

    # ---------------------------------------------------------- matches tab
    def _build_matches_tab(self, tab) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        fe = ctk.CTkEntry(bar, width=280, height=32, font=font(12),
                          placeholder_text="模糊筛选：英雄 / 模式 / 位置 / 队友名", fg_color=COLORS["bg_dark"],
                          border_color=COLORS["border"])
        self.filter_var = EntryVar(fe)
        fe.pack(side="left")
        fe.bind("<KeyRelease>", lambda e: self._schedule_filter())
        self.queue_seg = ctk.CTkSegmentedButton(bar, values=list(QUEUE_FILTERS), font=font(12),
                                                command=lambda v: self.apply_filter(),
                                                selected_color=COLORS["accent_dark"])
        self.queue_seg.set("全部")
        self.queue_seg.pack(side="left", padx=10)
        self.more_btn = ctk.CTkButton(bar, text="加载更多", width=90, height=32, font=font(12),
                                      fg_color=COLORS["bg_card2"], command=self.load_more)
        self.more_btn.pack(side="right")
        self.summary_label = ctk.CTkLabel(tab, text="", font=font(12), anchor="w", text_color=COLORS["text_dim"])
        self.summary_label.grid(row=1, column=0, sticky="ew", padx=4)
        self.match_list = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.match_list.grid(row=2, column=0, sticky="nsew")
        self.empty_label = ctk.CTkLabel(self.match_list, text="暂无战绩", font=font(14), text_color=COLORS["text_muted"])
        self.empty_label.pack(pady=80)

    # ----------------------------------------------------------- detail tab
    def _build_detail_tab(self, tab) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        self.detail = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.detail.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.detail, text="在「战绩」中点击一场对局", font=font(14),
                     text_color=COLORS["text_muted"]).pack(pady=80)

    # ------------------------------------------------------------- live tab
    def _build_live_tab(self, tab) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew")

        def b(text, cmd, color=None):
            ctk.CTkButton(bar, text=text, height=32, font=font(12, color is not None), command=cmd,
                          fg_color=color or COLORS["bg_card2"], hover_color=COLORS["bg_hover"]).pack(
                side="left", padx=3)
        b("⟳ 检测对局", self.check_live)
        b("▶ 一键观战", self.spectate, COLORS["accent"])
        b("📄 生成观战脚本", self.spectate_bat)
        b("📋 复制观战参数", self.copy_spectate)
        b("OP.GG 实时", lambda: self.open_link("OP.GG 实时对局"), COLORS["opgg"])
        b("Porofessor", lambda: self.open_link("Porofessor 实时"))
        self.live_info = ctk.CTkLabel(tab, text="点击「检测对局」查看玩家是否在游戏中", font=font(13),
                                      anchor="w", justify="left", text_color=COLORS["text_dim"])
        self.live_info.grid(row=1, column=0, sticky="ew", padx=6, pady=8)
        self.live_body = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.live_body.grid(row=2, column=0, sticky="nsew")
        self.live_body.grid_columnconfigure((0, 1), weight=1, uniform="t")

    # ----------------------------------------------------------- client tab
    def _build_client_tab(self, tab) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)
        top = ctk.CTkFrame(tab, fg_color=COLORS["bg_card2"], corner_radius=12)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.client_status = ctk.CTkLabel(top, text="客户端未连接", font=font(15, True), anchor="w",
                                          text_color=COLORS["text_dim"])
        self.client_status.pack(anchor="w", padx=16, pady=(12, 2))
        self.client_sub = ctk.CTkLabel(top, text="启动并登录英雄联盟客户端后自动连接（支持外服与国服客户端）",
                                       font=font(12), anchor="w", text_color=COLORS["text_muted"])
        self.client_sub.pack(anchor="w", padx=16, pady=(0, 12))
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew")
        ctk.CTkButton(bar, text="🔌 连接客户端", height=32, font=font(12), fg_color=COLORS["bg_card2"],
                      command=self.connect_lcu).pack(side="left", padx=3)
        ctk.CTkButton(bar, text="📜 我的战绩", height=32, font=font(12), fg_color=COLORS["bg_card2"],
                      command=self.search_me).pack(side="left", padx=3)
        ctk.CTkButton(bar, text="👥 查看选人/本局玩家", height=32, font=font(12, True), fg_color=COLORS["accent"],
                      command=self.load_my_game).pack(side="left", padx=3)
        self.auto_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(bar, text="进入选人/游戏时自动分析双方玩家", variable=self.auto_var, font=font(12),
                      progress_color=COLORS["accent"]).pack(side="left", padx=14)
        self.ingame_box = ctk.CTkTextbox(tab, font=ctk.CTkFont(family="Consolas", size=12),
                                         fg_color=COLORS["bg_dark"], text_color=COLORS["text"])
        self.ingame_box.grid(row=2, column=0, sticky="nsew", pady=8)
        self.ingame_box.insert("1.0", "游戏进行中时，这里会显示 Live Client Data（实时比分、装备、等级）。\n")
        self.ingame_box.configure(state="disabled")

    # ------------------------------------------------------------ opgg tab
    def _build_opgg_tab(self, tab) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        self.link_bar = ctk.CTkFrame(tab, fg_color="transparent")
        self.link_bar.grid(row=0, column=0, sticky="ew")
        self.opgg_body = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.opgg_body.grid(row=1, column=0, sticky="nsew", pady=8)
        self._render_opgg_tab()

    def _build_statusbar(self, parent) -> None:
        bar = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], height=30, corner_radius=0)
        bar.grid(row=2, column=0, sticky="ew")
        self.status_label = ctk.CTkLabel(bar, text="就绪", font=font(11), text_color=COLORS["text_dim"])
        self.status_label.pack(side="left", padx=14)
        self.progress = ctk.CTkProgressBar(bar, width=160, height=6, mode="indeterminate",
                                           progress_color=COLORS["accent"])

    # ================================================================ misc UI
    def toast(self, text: str, kind: str = "info") -> None:
        Toast(self, text, kind)

    def set_status(self, text: str) -> None:
        self.status_label.configure(text=text)

    def _set_busy(self, text: str, delta: int) -> None:
        self._busy = max(0, self._busy + delta)
        if text:
            self.set_status(text)
        if self._busy:
            if not self.progress.winfo_ismapped():
                self.progress.pack(side="right", padx=14)
                self.progress.start()
        else:
            self.progress.stop()
            self.progress.pack_forget()

    @staticmethod
    def _clear(frame) -> None:
        for w in frame.winfo_children():
            w.destroy()

    def _on_tab(self) -> None:
        pass

    # ================================================================ startup
    def _warmup(self) -> bool:
        self.dd.load()
        if self.config_data.get("auto_connect_lcu", True):
            self.svc.connect_lcu()
        return True

    def _on_warm(self) -> None:
        self._render_sources()
        self._render_recent()
        self.set_status(f"Data Dragon {self.dd.version or '离线'} 已就绪")
        if self.svc.lcu.connected:
            self._update_client_panel(self.svc.lcu_status())

    def _render_sources(self) -> None:
        key = "✅ Riot API Key" if self.svc.has_key else "⚪ Riot API Key 未配置（使用 OP.GG/客户端）"
        me = self.svc.lcu.me or {}
        lcu = f"✅ 客户端 {me.get('gameName', '')} [{self.svc.lcu_platform}]" if self.svc.lcu.connected else "⚪ 客户端未连接"
        op = "✅ OP.GG 数据" if self.svc.opgg_on else "⚪ OP.GG 已关闭"
        self.source_label.configure(text=f"{key}\n{lcu}\n{op}")

    def _render_recent(self) -> None:
        self._clear(self.recent_frame)
        for p in self.storage.recent_players(15):
            star = "★ " if p.get("favorite") else ""
            ctk.CTkButton(self.recent_frame, text=f"{star}{p['riot_id']}  ·  {p['platform']}", anchor="w",
                          height=26, font=font(12), fg_color="transparent", hover_color=COLORS["bg_hover"],
                          text_color=COLORS["gold"] if star else COLORS["text"],
                          command=lambda p=p: self.search(p["riot_id"], p["platform"])).pack(fill="x", pady=1)

    def _save_platform(self, value: str) -> None:
        self.config_data["default_platform"] = value
        save_config(self.config_data)

    # ================================================================ search
    def _on_search_key(self, event) -> None:
        if event.keysym in ("Up", "Down", "Return", "Escape", "Left", "Right"):
            return
        if self._suggest_job:
            self.after_cancel(self._suggest_job)
        self._suggest_job = self.after(120, self._update_suggestions)

    def _update_suggestions(self) -> None:
        q = self.search_var.get()
        items = self.svc.suggestions(q, self.platform_var.get(), limit=8)
        if items and self.focus_get() == self.search_entry._entry:
            self.suggest.show(items, self.search_entry)
        else:
            self.suggest.hide()

    def _on_search_enter(self, event=None) -> None:
        cur = self.suggest.current() if self.suggest.visible else None
        if cur:
            self._pick_suggestion(cur)
        else:
            self.search()

    def _pick_suggestion(self, p: Dict[str, Any]) -> None:
        self.suggest.hide()
        self.search(p["riot_id"], p["platform"])

    def search(self, query: Optional[str] = None, platform: Optional[str] = None) -> None:
        self.suggest.hide()
        q = (query if query is not None else self.search_var.get()).strip()
        if not q:
            self.toast("请输入召唤师名", "error")
            return
        platform = platform or self.platform_var.get()
        self.search_var.set(q)
        self.platform_var.set(platform)

        def work() -> Profile:
            self.dd.ready.wait(15)
            return self.svc.resolve(q, platform)
        self.run_async(work, ok=self._on_profile, busy=f"正在查找 {q} …")

    def search_me(self) -> None:
        def work() -> Profile:
            if not self.svc.lcu.connected and not self.svc.connect_lcu():
                raise ScoutError("未检测到已登录的英雄联盟客户端")
            me = self.svc.lcu.me or {}
            self.dd.ready.wait(15)
            self.storage.touch_player(f"{me.get('gameName', '')}#{me.get('tagLine', '')}",
                                      self.svc.lcu_platform, me.get("puuid"), source="lcu", searched=True)
            return Profile(me.get("gameName", ""), me.get("tagLine", ""), self.svc.lcu_platform or
                           self.platform_var.get(), me.get("puuid", ""), level=int(me.get("summonerLevel") or 0),
                           icon_url=self.dd.image_url("profileicon", me.get("profileIconId")) or "", source="lcu")
        self.run_async(work, ok=self._on_profile, busy="读取客户端账号 …")

    def search_player(self, riot_id: str) -> None:
        if riot_id and "#" in riot_id:
            self.search(riot_id, (self.profile.platform if self.profile else self.platform_var.get()))

    def _on_profile(self, prof: Profile) -> None:
        self.profile = prof
        if prof.platform in PLATFORMS:
            self.platform_var.set(prof.platform)
        self.search_var.set(prof.riot_id)
        self._render_header()
        self._render_profile_card()
        self._render_recent()
        self._render_opgg_tab()
        self.live = None
        self._clear(self.live_body)
        self.live_info.configure(text="点击「检测对局」查看玩家是否在游戏中")
        self.run_async(lambda: self.svc.enrich_profile(prof),
                       ok=lambda p: (self._render_header(), self._render_profile_card(), self._render_opgg_tab())
                       if p is self.profile else None,
                       err=lambda e: None)
        self.load_matches()
        # 有 Key 或者是本人时，后台静默检测是否在游戏中
        me = self.svc.lcu.me or {}
        if self.svc.has_key or (me.get("puuid") and me.get("puuid") == prof.puuid):
            self.run_async(lambda: self.svc.live_game(prof),
                           ok=lambda g: self._on_live(g, silent=True) if prof is self.profile else None,
                           err=lambda e: None)

    def _render_header(self) -> None:
        p = self.profile
        if not p:
            return
        self.head_title.configure(text=p.riot_id)
        solo = next((r for r in p.ranks if r.get("queue") == "SOLORANKED"), p.ranks[0] if p.ranks else {})
        try:
            src = {"riot": "Riot API", "lcu": "本地客户端", "opgg": "OP.GG"}[self.svc.match_source(p)]
        except ScoutError:
            src = "-"
        bits = [p.platform, f"Lv.{p.level}" if p.level else "", rank_text(solo) if solo else "", p.note,
                f"战绩来源：{src}"]
        self.head_sub.configure(text="  ·  ".join(b for b in bits if b))
        fav = self.storage.is_favorite(p.riot_id, p.platform)
        self.fav_btn.configure(text="★ 已收藏" if fav else "☆ 收藏",
                               text_color=COLORS["gold"] if fav else COLORS["text"])
        if p.icon_url:
            self._set_url_image(self.head_icon, p.icon_url, 56)

    def _set_url_image(self, label, url: str, size: int) -> None:
        key = (url, size)
        if key in self._images:
            label.configure(image=self._images[key])
            return

        def work():
            pil = self.dd.load_image(url, (size * 2, size * 2))

            def apply():
                if pil is None:
                    return
                ci = CTkImage(light_image=pil, dark_image=pil, size=(size, size))
                self._images[key] = ci
                if label.winfo_exists():
                    label.configure(image=ci)
            self.post(apply)
        self._img_pool.submit(work)

    def _render_profile_card(self) -> None:
        p = self.profile
        card = self.profile_card
        self._clear(card)
        if not p:
            return
        ctk.CTkLabel(card, text=p.riot_id, font=font(15, True), text_color=COLORS["text"],
                     wraplength=250).pack(anchor="w", padx=14, pady=(12, 0))
        ctk.CTkLabel(card, text=f"{p.platform}  Lv.{p.level or '-'}  {p.note}", font=font(11),
                     text_color=COLORS["purple"] if p.note else COLORS["text_dim"]).pack(anchor="w", padx=14)
        for r in p.ranks or []:
            f = ctk.CTkFrame(card, fg_color=COLORS["bg_dark"], corner_radius=8)
            f.pack(fill="x", padx=12, pady=3)
            q = "单双排" if r.get("queue") == "SOLORANKED" else "灵活"
            ctk.CTkLabel(f, text=q, font=font(11), text_color=COLORS["text_muted"], width=40).pack(side="left", padx=6)
            ctk.CTkLabel(f, text=rank_text(r), font=font(12, True), text_color=tier_color(r)).pack(side="left")
            ctk.CTkLabel(f, text=f"{r.get('win', 0)}胜{r.get('lose', 0)}负 {r.get('winrate', 0)}%", font=font(11),
                         text_color=COLORS["text_dim"]).pack(side="right", padx=8, pady=6)
        if not p.ranks:
            ctk.CTkLabel(card, text="排位：未定级 / 加载中", font=font(11), text_color=COLORS["text_muted"]).pack(
                anchor="w", padx=14, pady=4)
        if p.top_champs:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=(4, 10))
            for c in p.top_champs[:6]:
                lb = ctk.CTkLabel(row, text="", width=34, height=34, fg_color=COLORS["bg_dark"], corner_radius=6)
                lb.pack(side="left", padx=2)
                if c.get("champion_id"):
                    self.set_image(lb, "champion", int(c["champion_id"]), 34)
        else:
            ctk.CTkFrame(card, height=8, fg_color="transparent").pack()

    def toggle_favorite(self) -> None:
        p = self.profile
        if not p:
            return
        fav = not self.storage.is_favorite(p.riot_id, p.platform)
        self.storage.touch_player(p.riot_id, p.platform, p.puuid or None, searched=True)
        self.storage.set_favorite(p.riot_id, p.platform, fav)
        self._render_header()
        self._render_recent()

    def refresh_all(self) -> None:
        if self.profile:
            self.search(self.profile.riot_id, self.profile.platform)

    # ================================================================ matches
    def load_matches(self, count: Optional[int] = None) -> None:
        prof = self.profile
        if not prof:
            return
        count = count or int(self.config_data.get("match_count", 20))
        self._gen += 1
        gen = self._gen
        for c in self.cards:
            c.destroy()
        self.cards.clear()
        self.matches.clear()
        self.empty_label.pack_forget()
        self.summary_label.configure(text="加载中 …")
        self._match_count = count

        def on_match(m: Match, done: int, total: int) -> None:
            self.post(lambda: self._add_match(gen, m, done, total))

        self.run_async(lambda: self.svc.load_matches(prof, count, on_match),
                       ok=lambda src: self._matches_done(gen, src), busy="正在加载战绩 …",
                       err=lambda e: (self._default_err(e), self._matches_done(gen, "")))

    def load_more(self) -> None:
        if not self.profile:
            return
        cur = getattr(self, "_match_count", 20)
        src = self.svc.match_source(self.profile)
        limit = 20 if src == "opgg" else 100
        if cur >= limit:
            self.toast(f"{src.upper()} 数据源最多 {limit} 场")
            return
        self.load_matches(min(limit, cur + 20))

    def _add_match(self, gen: int, m: Match, done: int, total: int) -> None:
        if gen != self._gen:
            return
        # 按时间倒序插入（并发返回顺序不定）
        idx = next((i for i, x in enumerate(self.matches) if x.start_ts < m.start_ts), len(self.matches))
        self.matches.insert(idx, m)
        card = MatchCard(self.match_list, m, self.set_image, self.show_detail)
        self.cards.insert(idx, card)
        if self._card_visible(m):
            nxt = next((c for c in self.cards[idx + 1:] if c.winfo_ismapped()), None)
            if nxt:
                card.pack(fill="x", pady=3, padx=2, before=nxt)
            else:
                card.pack(fill="x", pady=3, padx=2)
        self.set_status(f"加载对局 {done}/{total}")

    def _matches_done(self, gen: int, source: str) -> None:
        if gen != self._gen:
            return
        if not self.matches:
            self.empty_label.pack(pady=80)
        self._update_summary()
        if self.matches:
            self.show_detail(self.matches[0], switch=False)
        src_cn = {"riot": "Riot API", "lcu": "本地客户端", "opgg": "OP.GG"}.get(source, source)
        self.set_status(f"已加载 {len(self.matches)} 场对局（来源：{src_cn}）")

    def _update_summary(self) -> None:
        ms = [m for m in self.matches if not m.remake and self._card_visible(m)]
        if not ms:
            self.summary_label.configure(text="")
            return
        wins = sum(1 for m in ms if m.me.win)
        k = sum(m.me.kills for m in ms)
        d = sum(m.me.deaths for m in ms)
        a = sum(m.me.assists for m in ms)
        champs = Counter(m.me.champ_name for m in ms).most_common(3)
        pos = Counter(m.me.position for m in ms if m.me.position).most_common(1)
        from .config import POSITION_CN
        text = (f"近 {len(ms)} 场  {wins}胜{len(ms) - wins}负  胜率 {wins * 100 // len(ms)}%   "
                f"KDA {k / len(ms):.1f}/{d / len(ms):.1f}/{a / len(ms):.1f} ({(k + a) / max(1, d):.2f})   "
                f"常用：{'、'.join(f'{c}({n})' for c, n in champs)}"
                + (f"   主位置：{POSITION_CN.get(pos[0][0].upper(), pos[0][0])}" if pos else ""))
        self.summary_label.configure(text=text)

    # ---------------------------------------------------------------- filter
    def _schedule_filter(self) -> None:
        if self._filter_job:
            self.after_cancel(self._filter_job)
        self._filter_job = self.after(150, self.apply_filter)

    def _card_visible(self, m: Match) -> bool:
        qf = QUEUE_FILTERS.get(self.queue_seg.get()) if hasattr(self, "queue_seg") else None
        if qf == "other":
            known = set().union(*[v for v in QUEUE_FILTERS.values() if isinstance(v, set)])
            if m.queue_id in known:
                return False
        elif isinstance(qf, set) and m.queue_id not in qf:
            return False
        q = self.filter_var.get().strip() if hasattr(self, "filter_var") else ""
        if not q:
            return True
        texts = m.search_text()
        # 英雄额外匹配英文 id / 称号（输入 yasuo / 疾风 都能命中）
        texts += self.dd.champion_search_keys(m.me.champ_id)
        return fuzzy.best_score(q, texts) >= 60

    def apply_filter(self) -> None:
        for c in self.cards:
            c.pack_forget()
        shown = 0
        for c in self.cards:
            if self._card_visible(c.match):
                c.pack(fill="x", pady=3, padx=2)
                shown += 1
        if not shown and self.matches:
            self.summary_label.configure(text="没有匹配的对局")
        else:
            self._update_summary()

    # ================================================================ detail
    def show_detail(self, m: Match, switch: bool = True) -> None:
        self._render_detail(m)
        if switch:
            self.tabs.set("📋 对局详情")
        if not m.full:
            self.run_async(lambda: self.svc.complete_match(m),
                           ok=lambda mm: self._render_detail(mm) if getattr(self, "_detail_id", None) == mm.match_id else None,
                           busy="补全全场数据 …", err=lambda e: None)

    def _render_detail(self, m: Match) -> None:
        self._detail_id = m.match_id
        self._clear(self.detail)
        me = m.me
        head = ctk.CTkFrame(self.detail, fg_color=COLORS["bg_card2"], corner_radius=12)
        head.pack(fill="x", pady=4)
        color = COLORS["text_muted"] if m.remake else (COLORS["win"] if me.win else COLORS["lose"])
        ctk.CTkLabel(head, text="重开" if m.remake else ("胜利" if me.win else "失败"), font=font(26, True),
                     text_color=color).pack(side="left", padx=18, pady=12)
        info = ctk.CTkFrame(head, fg_color="transparent")
        info.pack(side="left", padx=8)
        ctk.CTkLabel(info, text=f"{m.queue_name}  ·  {format_duration(m.duration)}  ·  {m.date_text}"
                     + (f"  ·  均分 {m.avg_tier.title()}" if m.avg_tier else ""),
                     font=font(13), text_color=COLORS["text"]).pack(anchor="w")
        ctk.CTkLabel(info, text=f"{m.match_id}  ·  来源 {m.source.upper()}", font=font(10),
                     text_color=COLORS["text_muted"]).pack(anchor="w")
        if not m.full:
            ctk.CTkLabel(self.detail, text="正在补全全场 10 名玩家数据 …", font=font(12),
                         text_color=COLORS["text_dim"]).pack(pady=6)
        max_dmg = max((p.damage for p in m.participants), default=0)
        for team_id, label, tcolor in ((100, "蓝色方", COLORS["accent"]), (200, "红色方", COLORS["lose"])):
            players = m.team(team_id)
            if not players:
                continue
            win = players[0].win
            box = ctk.CTkFrame(self.detail, fg_color=COLORS["bg_card2"], corner_radius=12)
            box.pack(fill="x", pady=5)
            k = sum(p.kills for p in players)
            g = sum(p.gold for p in players)
            ctk.CTkLabel(box, text=f"{label}  {'胜利' if win else '失败'}   击杀 {k}   经济 {g / 1000:.1f}k",
                         font=font(13, True), text_color=tcolor).pack(anchor="w", padx=12, pady=(8, 4))
            for p in players:
                participant_row(box, m, p, self.set_image, max_dmg, self.search_player,
                                highlight=(p is me)).pack(fill="x", padx=6, pady=1)
            ctk.CTkFrame(box, height=6, fg_color="transparent").pack()
        ctk.CTkLabel(self.detail, text="提示：点击玩家名可直接查询该玩家", font=font(11),
                     text_color=COLORS["text_muted"]).pack(pady=6)

    # ================================================================ live
    def check_live(self) -> None:
        prof = self.profile
        if not prof:
            self.toast("请先搜索玩家", "error")
            return
        self.tabs.set("👁 实时观战")
        self.live_info.configure(text=f"正在检测 {prof.riot_id} 的对局 …")
        self.run_async(lambda: self.svc.live_game(prof), ok=self._on_live, busy="检测实时对局 …",
                       err=lambda e: self.live_info.configure(
                           text=f"⚠ {e}\n\n也可以点上方「OP.GG 实时」「Porofessor」在网页查看该玩家实时对局与双方段位。",
                           text_color=COLORS["gold"]))

    def load_my_game(self) -> None:
        def work():
            if not self.svc.lcu.connected and not self.svc.connect_lcu():
                raise ScoutError("未连接客户端")
            g = self.svc.my_live_game()
            if g is None:
                raise ScoutError("当前不在选人阶段或游戏中")
            return g
        self.tabs.set("👁 实时观战")
        self.run_async(work, ok=self._on_live, busy="读取客户端对局 …")

    def _on_live(self, game: Optional[LiveGame], silent: bool = False) -> None:
        if game is None:
            if not silent:
                self.live = None
                self._clear(self.live_body)
                self.live_info.configure(text="😴 当前没有进行中的对局", text_color=COLORS["text_dim"])
            return
        self.live = game
        if silent:
            self.toast(f"🎮 {self.profile.riot_id if self.profile else ''} 正在游戏中，可前往「实时观战」", "ok")
            self.head_sub.configure(text=self.head_sub.cget("text") + "  ·  🎮 游戏中")
        src = {"riot": "Riot Spectator", "lcu-ingame": "本地客户端·游戏中", "lcu-champselect": "本地客户端·选人"}[game.source]
        spect = "可一键观战" if game.source == "riot" else ("选人阶段" if game.source == "lcu-champselect" else "本人对局")
        self.live_info.configure(
            text=f"🎮 {game.queue_name or '对局'}   已进行 {format_duration(game.elapsed)}   "
                 f"GameID {game.game_id}   来源 {src}   ({spect})",
            text_color=COLORS["win"])
        self._clear(self.live_body)
        self.live_rows.clear()
        my_puuid = self.profile.puuid if self.profile else ""
        me_lcu = (self.svc.lcu.me or {}).get("puuid", "")
        for col, (team_id, label, color) in enumerate(((100, "蓝色方", COLORS["accent"]),
                                                       (200, "红色方", COLORS["lose"]))):
            box = ctk.CTkFrame(self.live_body, fg_color=COLORS["bg_card"], corner_radius=12)
            box.grid(row=0, column=col, sticky="nsew", padx=4)
            ctk.CTkLabel(box, text=label, font=font(14, True), text_color=color).pack(anchor="w", padx=12, pady=8)
            for p in game.team(team_id):
                row = LivePlayerRow(box, p, self.set_image, lambda k: self.dd.champ_name(k), self.search_player,
                                    highlight=bool(p.puuid) and p.puuid in (my_puuid, me_lcu))
                row.pack(fill="x", padx=8, pady=3)
                self.live_rows[id(p)] = row
        if game.bans:
            bans = ctk.CTkFrame(self.live_body, fg_color="transparent")
            bans.grid(row=1, column=0, columnspan=2, sticky="w", pady=8, padx=6)
            ctk.CTkLabel(bans, text="禁用：", font=font(12), text_color=COLORS["text_dim"]).pack(side="left")
            for b in game.bans:
                if b > 0:
                    lb = ctk.CTkLabel(bans, text="", width=26, height=26, fg_color=COLORS["bg_dark"])
                    lb.pack(side="left", padx=1)
                    self.set_image(lb, "champion", b, 26)

        def on_player(p: LivePlayer) -> None:
            def apply():
                if self.live is game and id(p) in self.live_rows:
                    self.live_rows[id(p)].update_player(p)
            self.post(apply)
        self.run_async(lambda: self.svc.enrich_live(game, on_player), busy="查询双方段位（OP.GG）…",
                       ok=lambda _: self.set_status("双方玩家数据已加载"), err=lambda e: None)

    def spectate(self) -> None:
        prof = self.profile
        if not prof:
            self.toast("请先搜索玩家", "error")
            return
        self.run_async(lambda: self.svc.spectate(prof, self.live), ok=lambda msg: self.toast(msg, "ok"),
                       busy="正在发起观战 …")

    def spectate_bat(self) -> None:
        if not self.live:
            self.toast("请先检测到进行中的对局", "error")
            return
        try:
            path = self.svc.spectate_bat(self.live)
            self.toast(f"已生成：{path}", "ok")
        except ScoutError as e:
            self.toast(str(e), "error")

    def copy_spectate(self) -> None:
        if not self.live or self.live.source != "riot":
            self.toast("需要 Riot API 来源的实时对局才有观战密钥", "error")
            return
        params = SpectateParams.from_active_game(self.live.raw, self.config_data.get("spectator_host", ""))
        self.clipboard_clear()
        self.clipboard_append(params.spectator_arg())
        self.toast("观战参数已复制", "ok")

    def open_link(self, label: str) -> None:
        p = self.profile
        if not p:
            self.toast("请先搜索玩家", "error")
            return
        webbrowser.open(web_links(p.platform, p.game_name, p.tag_line)[label])

    # ================================================================ OP.GG tab
    def _render_opgg_tab(self) -> None:
        self._clear(self.link_bar)
        self._clear(self.opgg_body)
        p = self.profile
        if not p:
            ctk.CTkLabel(self.opgg_body, text="搜索玩家后显示 OP.GG 等三方数据与网页入口", font=font(13),
                         text_color=COLORS["text_muted"]).pack(pady=60)
            return
        for label, url in web_links(p.platform, p.game_name, p.tag_line).items():
            ctk.CTkButton(self.link_bar, text=label, height=30, font=font(12),
                          fg_color=COLORS["opgg"] if "OP.GG" in label else COLORS["bg_card2"],
                          command=lambda u=url: webbrowser.open(u)).pack(side="left", padx=3)
        box = ctk.CTkFrame(self.opgg_body, fg_color=COLORS["bg_card2"], corner_radius=12)
        box.pack(fill="x", pady=4)
        ctk.CTkLabel(box, text="常用英雄", font=font(14, True)).pack(anchor="w", padx=14, pady=(10, 4))
        if not p.top_champs:
            ctk.CTkLabel(box, text="加载中 / 暂无数据", font=font(12), text_color=COLORS["text_muted"]).pack(
                anchor="w", padx=14, pady=(0, 10))
        for c in p.top_champs:
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=2)
            lb = ctk.CTkLabel(row, text="", width=32, height=32, fg_color=COLORS["bg_dark"], corner_radius=6)
            lb.pack(side="left")
            cid = c.get("champion_id")
            if cid:
                self.set_image(lb, "champion", int(cid), 32)
            name = c.get("name") or self.dd.champ_name(cid)
            ctk.CTkLabel(row, text=name, width=110, anchor="w", font=font(12, True)).pack(side="left", padx=8)
            if c.get("play"):
                wr = round((c.get("win") or 0) * 100 / max(1, c["play"]))
                ctk.CTkLabel(row, text=f"{c['play']} 场   胜率 {wr}%", width=150, anchor="w", font=font(12),
                             text_color=COLORS["win"] if wr >= 55 else COLORS["text"]).pack(side="left")
                if c.get("kda") is not None:
                    ctk.CTkLabel(row, text=f"KDA {c['kda']}", font=font(12),
                                 text_color=kda_color(float(c["kda"]))).pack(side="left", padx=8)
            elif c.get("points"):
                ctk.CTkLabel(row, text=f"熟练度 Lv.{c.get('level')}  {c['points']:,} 点", font=font(12),
                             text_color=COLORS["text_dim"]).pack(side="left")
        ctk.CTkFrame(box, height=8, fg_color="transparent").pack()
        ctk.CTkLabel(self.opgg_body,
                     text="说明：无 Riot Key 时，战绩/段位来自 OP.GG 官方 MCP 接口；他人实时对局可通过上方 OP.GG / Porofessor 网页查看。",
                     font=font(11), text_color=COLORS["text_muted"], wraplength=900, justify="left").pack(anchor="w", pady=8)

    # ================================================================ LCU
    def connect_lcu(self) -> None:
        self.run_async(self.svc.lcu_status, ok=self._update_client_panel, busy="连接客户端 …")

    def _poll_lcu(self) -> None:
        if not self._lcu_polling and self.config_data.get("auto_connect_lcu", True):
            self._lcu_polling = True

            def done(st):
                self._lcu_polling = False
                self._update_client_panel(st)

            def fail(e):
                self._lcu_polling = False
            self.run_async(self.svc.lcu_status, ok=done, err=fail)
        self.after(5000, self._poll_lcu)

    def _update_client_panel(self, st: Dict[str, Any]) -> None:
        was = self.source_label.cget("text")
        self._render_sources()
        if not st.get("connected"):
            self.client_status.configure(text="⚪ 客户端未连接", text_color=COLORS["text_dim"])
            self._last_phase = ""
            return
        me = st.get("me") or {}
        phase = st.get("phase", "None")
        self.client_status.configure(
            text=f"✅ {me.get('gameName', '')}#{me.get('tagLine', '')}   [{st.get('platform')}]   Lv.{me.get('summonerLevel', '-')}",
            text_color=COLORS["win"])
        self.client_sub.configure(text=f"状态：{PHASE_CN.get(phase, phase)}")
        if was != self.source_label.cget("text"):
            self._render_recent()
        if phase != self._last_phase:
            self._last_phase = phase
            if self.auto_var.get() and phase in ("ChampSelect", "InProgress"):
                self.toast(f"检测到{PHASE_CN.get(phase)}，正在分析双方玩家", "ok")
                self.load_my_game()
        if phase == "InProgress":
            self.run_async(self.svc.live_client.all_data, ok=self._render_ingame, err=lambda e: None)

    def _render_ingame(self, data: Optional[Dict[str, Any]]) -> None:
        if not data:
            return
        gd = data.get("gameData") or {}
        lines = [f"游戏时间 {format_duration(int(gd.get('gameTime', 0)))}   模式 {gd.get('gameMode', '')}", ""]
        for team in ("ORDER", "CHAOS"):
            lines.append("—— 蓝色方 ——" if team == "ORDER" else "—— 红色方 ——")
            for p in data.get("allPlayers") or []:
                if p.get("team") != team:
                    continue
                s = p.get("scores") or {}
                items = ",".join(i.get("displayName", "") for i in p.get("items") or [])
                name = p.get("riotIdGameName") or p.get("summonerName", "")
                lines.append(f"{name:<18} {p.get('championName', ''):<8} Lv{p.get('level', 0):<3} "
                             f"{s.get('kills', 0)}/{s.get('deaths', 0)}/{s.get('assists', 0):<4} "
                             f"CS {s.get('creepScore', 0):<4} {items}")
            lines.append("")
        self.ingame_box.configure(state="normal")
        self.ingame_box.delete("1.0", "end")
        self.ingame_box.insert("1.0", "\n".join(lines))
        self.ingame_box.configure(state="disabled")

    # ================================================================ settings
    def open_settings(self) -> None:
        win = ctk.CTkToplevel(self)
        win.title("设置")
        win.geometry("560x640")
        win.configure(fg_color=COLORS["bg_dark"])
        win.transient(self)
        win.after(100, win.grab_set)
        cfg = self.config_data

        def section(title: str, hint: str = "") -> ctk.CTkFrame:
            f = ctk.CTkFrame(win, fg_color=COLORS["bg_card"], corner_radius=10)
            f.pack(fill="x", padx=16, pady=5)
            ctk.CTkLabel(f, text=title, font=font(13, True)).pack(anchor="w", padx=12, pady=(8, 0))
            if hint:
                ctk.CTkLabel(f, text=hint, font=font(10), text_color=COLORS["text_muted"]).pack(anchor="w", padx=12)
            return f

        f = section("Riot API Key", "可选。填写后启用官方战绩与他人实时观战；开发者 Key 每 24 小时过期")
        key_var = ctk.StringVar(value=cfg.get("api_key", "") if "请替换" not in cfg.get("api_key", "") else "")
        ctk.CTkEntry(f, textvariable=key_var, show="•", placeholder_text="RGAPI-xxxxxxxx").pack(fill="x", padx=12, pady=8)

        exe = detect_game_exe(cfg.get("league_client_path", ""))
        f = section("游戏路径（观战用）", f"自动探测：{exe or '未找到'}；需要 Game/League of Legends.exe")
        path_var = ctk.StringVar(value=cfg.get("league_client_path", ""))
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=8)
        ctk.CTkEntry(row, textvariable=path_var).pack(side="left", fill="x", expand=True)

        def browse():
            from tkinter import filedialog
            p = filedialog.askopenfilename(parent=win, title="选择 League of Legends.exe", filetypes=[("exe", "*.exe")])
            if p:
                path_var.set(p)
        ctk.CTkButton(row, text="浏览", width=60, command=browse).pack(side="left", padx=(6, 0))

        f = section("观战服务器（可选）", "留空使用 spectator.{区服}.lol.pvp.net:8080")
        host_var = ctk.StringVar(value=cfg.get("spectator_host", ""))
        ctk.CTkEntry(f, textvariable=host_var).pack(fill="x", padx=12, pady=8)

        f = section("数据")
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(row, text="默认拉取场数", font=font(12)).pack(side="left")
        count_var = ctk.StringVar(value=str(cfg.get("match_count", 20)))
        ctk.CTkOptionMenu(row, values=["10", "20", "30", "50"], variable=count_var, width=80).pack(side="left", padx=8)
        ctk.CTkLabel(row, text="语言", font=font(12)).pack(side="left", padx=(16, 0))
        loc_var = ctk.StringVar(value=cfg.get("locale", "zh_CN"))
        ctk.CTkOptionMenu(row, values=["zh_CN", "zh_TW", "en_US", "ko_KR", "ja_JP"], variable=loc_var,
                          width=90).pack(side="left", padx=8)
        opgg_var = ctk.BooleanVar(value=cfg.get("opgg_enabled", True))
        lcu_var = ctk.BooleanVar(value=cfg.get("auto_connect_lcu", True))
        ctk.CTkSwitch(f, text="启用 OP.GG 三方数据（无 Key 时的战绩来源）", variable=opgg_var).pack(anchor="w", padx=12, pady=3)
        ctk.CTkSwitch(f, text="自动连接本地客户端", variable=lcu_var).pack(anchor="w", padx=12, pady=(3, 10))

        f = section("维护")
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=8)

        def clear_cache():
            self.storage.clear_cache(keep_permanent=True)
            self.toast("已清除临时缓存（保留对局详情与静态数据）", "ok")

        def clear_history():
            self.storage.clear_history()
            self._render_recent()
            self.toast("已清除搜索历史（保留收藏）", "ok")
        ctk.CTkButton(row, text="清除缓存", fg_color=COLORS["bg_card2"], command=clear_cache).pack(side="left", padx=3)
        ctk.CTkButton(row, text="清除搜索历史", fg_color=COLORS["bg_card2"], command=clear_history).pack(side="left", padx=3)

        def save():
            key = key_var.get().strip()
            cfg["api_key"] = key or "请替换成你的 Riot API Key"
            cfg["league_client_path"] = path_var.get().strip()
            cfg["spectator_host"] = host_var.get().strip()
            cfg["match_count"] = int(count_var.get())
            locale_changed = cfg.get("locale") != loc_var.get()
            cfg["locale"] = loc_var.get()
            cfg["opgg_enabled"] = bool(opgg_var.get())
            cfg["auto_connect_lcu"] = bool(lcu_var.get())
            save_config(cfg)
            self.svc.rebuild_clients()
            if locale_changed:
                self.dd.locale = cfg["locale"]
                self.dd.ready.clear()
                self.run_async(self.dd.load)
            self._render_sources()
            self.toast("设置已保存", "ok")
            win.destroy()
        ctk.CTkButton(win, text="保存", height=38, font=font(13, True), fg_color=COLORS["accent"],
                      command=save).pack(pady=12)

    # ================================================================ close
    def _on_close(self) -> None:
        try:
            self.svc.shutdown()
            self._img_pool.shutdown(wait=False, cancel_futures=True)
        finally:
            self.destroy()


def main() -> None:
    app = LoLScoutApp()
    app.mainloop()
