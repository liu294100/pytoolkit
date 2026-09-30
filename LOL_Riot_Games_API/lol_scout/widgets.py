"""UI 组件（CustomTkinter）"""

from __future__ import annotations

import tkinter
from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk

from .config import COLORS, POSITION_CN, TIER_CN, format_duration
from .models import LivePlayer, Match, Participant

TIER_COLORS = {
    "IRON": "#7d7d7d", "BRONZE": "#b07a62", "SILVER": "#a8b8c8", "GOLD": "#e6b450",
    "PLATINUM": "#4fc1b0", "EMERALD": "#2ecc71", "DIAMOND": "#7a95ff", "MASTER": "#b766ff",
    "GRANDMASTER": "#ff5d5d", "CHALLENGER": "#f7d774",
}
ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", "1": "I", "2": "II", "3": "III", "4": "IV"}
APEX = {"MASTER", "GRANDMASTER", "CHALLENGER"}
QUEUE_LABEL = {"SOLORANKED": "单双排", "FLEXRANKED": "灵活"}


def font(size: int = 12, bold: bool = False) -> ctk.CTkFont:
    return ctk.CTkFont(family="Microsoft YaHei UI", size=size, weight="bold" if bold else "normal")


def rank_text(rank: Dict[str, Any], short: bool = False) -> str:
    tier = (rank or {}).get("tier")
    if not tier:
        return "未定级"
    name = tier.title() if short else TIER_CN.get(tier, tier)
    div = "" if tier in APEX else ROMAN.get(rank.get("division"), str(rank.get("division") or ""))
    lp = rank.get("lp")
    text = f"{name} {div}".strip()
    if lp is not None:
        text += f" {lp}LP"
    return text


def tier_color(rank: Dict[str, Any]) -> str:
    return TIER_COLORS.get((rank or {}).get("tier") or "", COLORS["text_dim"])


def kda_color(kda: float) -> str:
    if kda >= 5:
        return COLORS["gold"]
    if kda >= 3:
        return COLORS["accent"]
    if kda >= 2:
        return COLORS["text"]
    return COLORS["text_dim"]


ImageSetter = Callable[[ctk.CTkLabel, str, Any, int], None]


class EntryVar:
    """CTkEntry 绑定 textvariable 后 placeholder 会失效，这里用 get/set 直接操作控件"""

    def __init__(self, entry: ctk.CTkEntry):
        self.entry = entry

    def get(self) -> str:
        return self.entry.get()

    def set(self, value: str) -> None:
        self.entry.delete(0, "end")
        if value:
            self.entry.insert(0, value)


class Toast(ctk.CTkFrame):
    """右上角非阻塞提示"""

    def __init__(self, master, text: str, kind: str = "info", ms: int = 3500):
        color = {"info": COLORS["accent"], "error": COLORS["lose"], "ok": COLORS["win"]}.get(kind, COLORS["accent"])
        super().__init__(master, fg_color=COLORS["bg_card2"], corner_radius=10, border_width=1, border_color=color)
        ctk.CTkLabel(self, text=text, font=font(12), text_color=COLORS["text"], wraplength=360,
                     justify="left").pack(padx=14, pady=10)
        self.place(relx=0.99, rely=0.015, anchor="ne")
        self.lift()
        self.after(ms, self.destroy)


class Suggestions(ctk.CTkFrame):
    """搜索框下拉的模糊匹配候选"""

    def __init__(self, master, on_pick: Callable[[Dict[str, Any]], None]):
        super().__init__(master, fg_color=COLORS["bg_card2"], corner_radius=8, border_width=1,
                         border_color=COLORS["border"])
        self.on_pick = on_pick
        self.items: List[Dict[str, Any]] = []
        self.buttons: List[ctk.CTkButton] = []
        self.index = -1

    def show(self, items: List[Dict[str, Any]], anchor: ctk.CTkBaseClass) -> None:
        for b in self.buttons:
            b.destroy()
        self.buttons.clear()
        self.items = items
        self.index = -1
        if not items:
            self.place_forget()
            return
        icons = {"favorite": "★", "friend": "👥", "lcu": "🖥", "seen": "·", "history": "🕘"}
        for i, p in enumerate(items):
            src = "favorite" if p.get("favorite") else p.get("source", "history")
            b = ctk.CTkButton(self, text=f"{icons.get(src, '·')}  {p['riot_id']}   [{p['platform']}]",
                              anchor="w", height=28, font=font(12), fg_color="transparent",
                              hover_color=COLORS["bg_hover"], text_color=COLORS["text"],
                              command=lambda p=p: self.on_pick(p))
            b.pack(fill="x", padx=4, pady=1)
            self.buttons.append(b)
        x = anchor.winfo_x()
        y = anchor.winfo_y() + anchor.winfo_height() + 2
        # winfo_* 是真实像素，绕过 CTk 的 DPI 缩放直接用 tkinter 的 place
        tkinter.Place.place_configure(self, x=x, y=y, width=anchor.winfo_width())
        self.lift()

    def hide(self) -> None:
        self.place_forget()
        self.index = -1

    @property
    def visible(self) -> bool:
        return bool(self.winfo_ismapped())

    def move(self, delta: int) -> None:
        if not self.buttons:
            return
        self.index = (self.index + delta) % len(self.buttons)
        for i, b in enumerate(self.buttons):
            b.configure(fg_color=COLORS["bg_hover"] if i == self.index else "transparent")

    def current(self) -> Optional[Dict[str, Any]]:
        if 0 <= self.index < len(self.items):
            return self.items[self.index]
        return None


class MatchCard(ctk.CTkFrame):
    ICON = 46

    def __init__(self, master, match: Match, set_image: ImageSetter, on_click: Callable[[Match], None]):
        me = match.me
        if match.remake:
            bar, bg, label = COLORS["text_muted"], COLORS["bg_card"], "重开"
        elif me.win:
            bar, bg, label = COLORS["win"], COLORS["win_bg"], "胜利"
        else:
            bar, bg, label = COLORS["lose"], COLORS["lose_bg"], "失败"
        super().__init__(master, fg_color=bg, corner_radius=10)
        self.match = match
        self.bg = bg
        self.grid_columnconfigure(3, weight=1)

        ctk.CTkFrame(self, width=5, height=10, fg_color=bar, corner_radius=3).grid(row=0, column=0, rowspan=2, sticky="ns",
                                                                         padx=(6, 8), pady=8)
        info = ctk.CTkFrame(self, fg_color="transparent", width=96, height=10)
        info.grid(row=0, column=1, rowspan=2, sticky="w", padx=(0, 6))
        ctk.CTkLabel(info, text=match.queue_name or "-", font=font(12, True), text_color=bar, anchor="w").pack(anchor="w")
        ctk.CTkLabel(info, text=match.date_text, font=font(11), text_color=COLORS["text_dim"], anchor="w").pack(anchor="w")
        ctk.CTkLabel(info, text=f"{label} · {format_duration(match.duration)}", font=font(11),
                     text_color=COLORS["text_dim"], anchor="w").pack(anchor="w")

        icon = ctk.CTkLabel(self, text="", width=self.ICON, height=self.ICON, fg_color=COLORS["bg_dark"], corner_radius=8)
        icon.grid(row=0, column=2, rowspan=2, padx=6, pady=8)
        set_image(icon, "champion", me.champ_key or me.champ_id, self.ICON)

        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.grid(row=0, column=3, sticky="w", padx=8, pady=(8, 0))
        ctk.CTkLabel(mid, text=me.champ_name or "?", font=font(14, True), text_color=COLORS["text"]).pack(side="left")
        ctk.CTkLabel(mid, text=f"  {me.kda_text}", font=font(14, True), text_color=COLORS["text"]).pack(side="left")
        ctk.CTkLabel(mid, text=f"  {me.kda:.2f} KDA", font=font(12, True), text_color=kda_color(me.kda)).pack(side="left")
        if me.op_score is not None and me.op_score:
            ctk.CTkLabel(mid, text=f"  OP {me.op_score:.1f}", font=font(12, True),
                         text_color=COLORS["opgg"]).pack(side="left")
            if me.op_rank in (1,):
                ctk.CTkLabel(mid, text=" MVP", font=font(11, True), text_color=COLORS["gold"]).pack(side="left")

        sub = ctk.CTkFrame(self, fg_color="transparent")
        sub.grid(row=1, column=3, sticky="w", padx=8, pady=(0, 8))
        mins = max(1, match.duration / 60)
        pos = POSITION_CN.get(me.position.upper(), "") if me.position else ""
        parts = [pos, f"补刀 {me.cs} ({me.cs / mins:.1f})"]
        if match.full:
            parts.append(f"参团 {match.kill_participation(me)}%")
        if me.damage:
            parts.append(f"伤害 {me.damage:,}")
        if match.avg_tier:
            parts.append(match.avg_tier.title())
        ctk.CTkLabel(sub, text="  ·  ".join(p for p in parts if p), font=font(11),
                     text_color=COLORS["text_dim"]).pack(side="left")

        items = ctk.CTkFrame(self, fg_color="transparent")
        items.grid(row=0, column=4, rowspan=2, padx=10)
        for it in (me.items or [])[:7]:
            lb = ctk.CTkLabel(items, text="", width=24, height=24, fg_color=COLORS["bg_dark"], corner_radius=4)
            lb.pack(side="left", padx=1)
            if it:
                set_image(lb, "item", it, 24)

        self._bind_all(self, lambda e: on_click(self.match))
        self._bind_hover(self)

    def _bind_all(self, w, fn):
        w.bind("<Button-1>", fn)
        for c in w.winfo_children():
            self._bind_all(c, fn)

    def _bind_hover(self, w):
        w.bind("<Enter>", lambda e: self.configure(fg_color=COLORS["bg_hover"]), add="+")
        w.bind("<Leave>", lambda e: self.configure(fg_color=self.bg), add="+")


def participant_row(master, m: Match, p: Participant, set_image: ImageSetter, max_dmg: int,
                    on_player: Callable[[str], None], highlight: bool) -> ctk.CTkFrame:
    row = ctk.CTkFrame(master, fg_color=COLORS["bg_hover"] if highlight else "transparent", corner_radius=6)
    # 固定列宽，保证 10 行对齐（图片是否已加载都不影响布局）
    for col, minsize in enumerate((40, 40, 190, 72, 40, 40, 120, 64, 52, 0)):
        row.grid_columnconfigure(col, minsize=minsize)
    icon = ctk.CTkLabel(row, text="", width=30, height=30, fg_color=COLORS["bg_dark"], corner_radius=6)
    icon.grid(row=0, column=0, padx=(6, 4), pady=3)
    set_image(icon, "champion", p.champ_key or p.champ_id, 30)
    spells = ctk.CTkFrame(row, fg_color="transparent")
    spells.grid(row=0, column=1, sticky="w")
    for sp in p.spells[:2]:
        s = ctk.CTkLabel(spells, text="", width=16, height=16, fg_color=COLORS["bg_dark"])
        s.pack(side="left", padx=1)
        if sp:
            set_image(s, "spell", sp, 16)
    name = p.riot_id or "(隐藏)"
    nb = ctk.CTkButton(row, text=name, width=180, anchor="w", font=font(12, highlight), height=24,
                       fg_color="transparent", hover_color=COLORS["bg_card2"],
                       text_color=COLORS["gold"] if highlight else COLORS["text"],
                       command=(lambda: on_player(p.riot_id)) if p.tag_line else None)
    nb.grid(row=0, column=2, sticky="w", padx=4)
    ctk.CTkLabel(row, text=p.kda_text, font=font(12, True)).grid(row=0, column=3)
    ctk.CTkLabel(row, text=f"{p.kda:.1f}", font=font(11), text_color=kda_color(p.kda)).grid(row=0, column=4)
    if p.op_score:
        ctk.CTkLabel(row, text=f"{p.op_score:.1f}", font=font(11, True),
                     text_color=COLORS["gold"] if p.op_rank == 1 else COLORS["opgg"]).grid(row=0, column=5)
    dmg = ctk.CTkFrame(row, fg_color="transparent")
    dmg.grid(row=0, column=6, sticky="w", padx=6)
    ctk.CTkLabel(dmg, text=f"{p.damage:,}", font=font(10), text_color=COLORS["text_dim"], height=14).pack(anchor="w")
    bar = ctk.CTkProgressBar(dmg, width=100, height=6, progress_color=COLORS["lose"] if p.team == 200 else COLORS["accent"],
                             fg_color=COLORS["bg_dark"])
    bar.set(p.damage / max_dmg if max_dmg else 0)
    bar.pack(anchor="w")
    ctk.CTkLabel(row, text=f"{p.cs} CS", font=font(11), text_color=COLORS["text_dim"]).grid(row=0, column=7)
    ctk.CTkLabel(row, text=f"{p.gold / 1000:.1f}k", font=font(11), text_color=COLORS["gold"]).grid(row=0, column=8)
    items = ctk.CTkFrame(row, fg_color="transparent")
    items.grid(row=0, column=9, sticky="w", padx=6)
    for it in (p.items or [])[:7]:
        lb = ctk.CTkLabel(items, text="", width=22, height=22, fg_color=COLORS["bg_dark"], corner_radius=3)
        lb.pack(side="left", padx=1)
        if it:
            set_image(lb, "item", it, 22)
    return row


class LivePlayerRow(ctk.CTkFrame):
    def __init__(self, master, p: LivePlayer, set_image: ImageSetter, champ_name: Callable[[Any], str],
                 on_player: Callable[[str], None], highlight: bool):
        super().__init__(master, fg_color=COLORS["bg_hover"] if highlight else COLORS["bg_card2"], corner_radius=8)
        self.player = p
        self.champ_name = champ_name
        icon = ctk.CTkLabel(self, text="", width=40, height=40, fg_color=COLORS["bg_dark"], corner_radius=8)
        icon.grid(row=0, column=0, rowspan=2, padx=8, pady=6)
        if p.champ_key:
            set_image(icon, "champion", p.champ_key, 40)
        spells = ctk.CTkFrame(self, fg_color="transparent")
        spells.grid(row=0, column=1, rowspan=2, padx=(0, 6))
        for sp in p.spells[:2]:
            s = ctk.CTkLabel(spells, text="", width=18, height=18, fg_color=COLORS["bg_dark"])
            s.pack(pady=1)
            if sp:
                set_image(s, "spell", sp, 18)
        title = p.riot_id or ("电脑" if p.bot else "(隐藏名字)")
        pos = POSITION_CN.get(p.position, "")
        ctk.CTkButton(self, text=title, anchor="w", height=22, font=font(13, True),
                      fg_color="transparent", hover_color=COLORS["bg_card"],
                      text_color=COLORS["gold"] if highlight else COLORS["text"],
                      command=(lambda: on_player(p.riot_id)) if p.tag_line else None
                      ).grid(row=0, column=2, sticky="w")
        self.sub = ctk.CTkLabel(self, text=f"{champ_name(p.champ_key) if p.champ_key else '未选择'}  {pos}",
                                font=font(11), text_color=COLORS["text_dim"], anchor="w")
        self.sub.grid(row=1, column=2, sticky="w", padx=6)
        self.rank = ctk.CTkLabel(self, text="查询中…", font=font(12, True), text_color=COLORS["text_muted"], width=150,
                                 anchor="e")
        self.rank.grid(row=0, column=3, sticky="e", padx=10)
        self.extra = ctk.CTkLabel(self, text="", font=font(11), text_color=COLORS["text_dim"], anchor="e")
        self.extra.grid(row=1, column=3, sticky="e", padx=10)
        self.grid_columnconfigure(2, weight=1)
        if p.bot:
            self.rank.configure(text="")

    def update_player(self, p: LivePlayer) -> None:
        r = p.rank or {}
        self.rank.configure(text=rank_text(r), text_color=tier_color(r))
        bits = []
        if r.get("win") is not None and r.get("tier"):
            bits.append(f"{r['win']}胜{r['lose']}负 {r['winrate']}%")
        tops = [c.get("champion_name") for c in (p.top_champs or []) if c.get("champion_name")]
        if tops:
            bits.append("常用: " + "/".join(tops[:3]))
        if p.note:
            bits.append(p.note)
        self.extra.configure(text="  ".join(bits), text_color=COLORS["purple"] if p.note else COLORS["text_dim"])
