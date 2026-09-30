#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Downloader Pro - 暗色霓虹风格的高级版下载器
功能: 批量链接 / 合集(播放列表、频道)解析与勾选下载 / 多任务并发
      字幕下载(人工+自动、转 SRT/VTT/ASS、内嵌、仅字幕) / 画质预设 / 仅音频
      嵌入封面 / 代理 / 浏览器 Cookies / 失败重试 / 实时彩色日志
依赖: yt-dlp (必需)；ffmpeg (合并音视频、转音频、转换/内嵌字幕、嵌入封面时需要)
"""

import os
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from queue import Queue, Empty
from tkinter import ttk, filedialog, messagebox

try:
    import customtkinter as ctk
except ImportError:
    print("缺少 customtkinter，请先执行: pip install customtkinter")
    raise

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

# ---------------- 主题配色 ----------------
C = {
    "bg": "#0b0d18",
    "panel": "#12152a",
    "card": "#161a30",
    "input": "#0f1224",
    "hover": "#1e2340",
    "border": "#272d52",
    "fg": "#e8ebff",
    "muted": "#9aa0c8",
    "dim": "#5a6090",
    "log": "#0a0c16",
    "accent": "#22d3ee",
    "accent2": "#8b5cf6",
    "ok": "#10d990",
    "warn": "#f5a524",
    "err": "#f43f5e",
    "disabled": "#23284a",
}
FONT = "Microsoft YaHei UI"
MONO = "Consolas"

# 画质预设: 名称 -> (yt-dlp format 选择器, 音频转码格式/None)
QUALITY_PRESETS = {
    "最佳画质 (自动)": ("bestvideo*+bestaudio/best", None),
    "2160p 4K": ("bestvideo*[height<=2160]+bestaudio/best[height<=2160]", None),
    "1440p 2K": ("bestvideo*[height<=1440]+bestaudio/best[height<=1440]", None),
    "1080p": ("bestvideo*[height<=1080]+bestaudio/best[height<=1080]", None),
    "720p": ("bestvideo*[height<=720]+bestaudio/best[height<=720]", None),
    "480p": ("bestvideo*[height<=480]+bestaudio/best[height<=480]", None),
    "仅音频 MP3": ("bestaudio/best", "mp3"),
    "仅音频 M4A": ("bestaudio[ext=m4a]/bestaudio/best", "m4a"),
    "仅音频 FLAC": ("bestaudio/best", "flac"),
}
# 注意: 正则如 en.* 会匹配大量机器翻译字幕 (en-de 等)，容易触发 429 限流
SUB_LANG_PRESETS = ["zh-Hans,zh-Hant,en", "zh-Hans", "en", "ja,en", "zh.*", "en.*", "all"]
STATUS_COLORS = {
    "等待": "muted", "下载中": "accent", "处理中": "accent2",
    "完成": "ok", "失败": "err", "已取消": "warn",
}


class CancelledByUser(Exception):
    pass


def fmt_size(n):
    if not n:
        return "-"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def fmt_time(sec):
    if sec is None:
        return "-"
    try:
        sec = int(sec)
    except (TypeError, ValueError):
        return "-"
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def safe_name(name):
    name = re.sub(r'[\\/:*?"<>|\r\n]+', "_", str(name or "")).strip(" .")
    return name[:120] or "untitled"


def hex_mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * t) for x, y in zip(a, b))


class _Logger:
    """把 yt-dlp 输出转发到界面日志（过滤进度刷屏）"""

    def __init__(self, push):
        self.push = push

    def debug(self, msg):
        if msg and not msg.startswith("[download]") and not msg.startswith("[debug]"):
            self.push(msg)

    def info(self, msg):
        self.debug(msg)

    def warning(self, msg):
        self.push(f"⚠ {msg}", "warn")

    def error(self, msg):
        self.push(f"✖ {msg}", "err")


class ProDownloader:
    def __init__(self, root):
        self.root = root
        self.tasks = {}              # iid -> task dict
        self.ui_queue = Queue()      # 工作线程 -> 主线程 的消息队列
        self.cancel_event = threading.Event()
        self.running = False
        self.executor = None
        self.pending = 0
        self.done_count = 0
        self.fail_count = 0
        self.total_count = 0
        self.task_progress = {}
        self._glow_phase = 0
        self._build_theme()
        self._build_ui()
        self.root.after(80, self._drain_ui_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        if yt_dlp is None:
            self.log("未检测到 yt-dlp，请先执行: pip install -U yt-dlp", "err")
        else:
            self.log(f"yt-dlp 版本: {yt_dlp.version.__version__}", "accent")

    # ================= 主题 =================
    def _build_theme(self):
        r = self.root
        r.title("YouTube Downloader Pro")
        r.geometry("1400x940")
        r.minsize(1200, 800)
        r.configure(fg_color=C["bg"])
        self.f_title = ctk.CTkFont(family=FONT, size=15, weight="bold")
        self.f_body = ctk.CTkFont(family=FONT, size=13)
        self.f_small = ctk.CTkFont(family=FONT, size=12)
        self.f_btn = ctk.CTkFont(family=FONT, size=13, weight="bold")
        self.f_big = ctk.CTkFont(family=FONT, size=28, weight="bold")
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Pro.Treeview", background=C["card"], fieldbackground=C["card"], foreground=C["fg"],
                    rowheight=34, borderwidth=0, relief="flat", font=(FONT, 10))
        s.configure("Pro.Treeview.Heading", background=C["panel"], foreground=C["muted"],
                    font=(FONT, 10, "bold"), relief="flat", borderwidth=0, padding=(6, 8))
        s.map("Pro.Treeview", background=[("selected", "#2d2660")], foreground=[("selected", "#ffffff")])
        s.map("Pro.Treeview.Heading", background=[("active", C["hover"])])
        s.layout("Pro.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])  # 去掉默认边框

    # ================= 通用控件 =================
    def _btn(self, parent, text, cmd, kind="ghost", **kw):
        styles = {
            "primary": dict(fg_color=C["accent"], hover_color="#5ee6ff", text_color="#06121f"),
            "violet": dict(fg_color=C["accent2"], hover_color="#a78bfa", text_color="#ffffff"),
            "ok": dict(fg_color=C["ok"], hover_color="#4ff0b0", text_color="#04170f"),
            "danger": dict(fg_color=C["err"], hover_color="#fb7185", text_color="#ffffff"),
            "ghost": dict(fg_color=C["hover"], hover_color=C["border"], text_color=C["fg"],
                          border_width=1, border_color=C["border"]),
        }
        opts = dict(corner_radius=10, height=34, font=self.f_btn, text_color_disabled=C["dim"])
        opts.update(styles[kind])
        opts.update(kw)
        b = ctk.CTkButton(parent, text=text, command=cmd, **opts)
        b._base = opts["fg_color"]
        return b

    def _set_btn(self, b, enabled):
        b.configure(state="normal" if enabled else "disabled", fg_color=b._base if enabled else C["disabled"])

    def _card(self, parent, title, subtitle=None):
        """圆角卡片：左侧霓虹竖条 + 标题，返回 (卡片, 内容区)"""
        card = ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=16, border_width=1, border_color=C["border"])
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill=tk.X, padx=16, pady=(14, 8))
        ctk.CTkFrame(head, width=4, height=18, corner_radius=2, fg_color=C["accent"]).pack(side=tk.LEFT, padx=(0, 10))
        ctk.CTkLabel(head, text=title, font=self.f_title, text_color=C["fg"]).pack(side=tk.LEFT)
        if subtitle:
            ctk.CTkLabel(head, text=subtitle, font=self.f_small, text_color=C["dim"]).pack(side=tk.LEFT, padx=(10, 0))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 14))
        return card, body

    def _label(self, parent, text, muted=False, **kw):
        return ctk.CTkLabel(parent, text=text, font=self.f_small if muted else self.f_body,
                            text_color=C["dim"] if muted else C["muted"], **kw)

    def _switch(self, parent, text, var):
        return ctk.CTkSwitch(parent, text=text, variable=var, onvalue=True, offvalue=False, font=self.f_body,
                             text_color=C["fg"], progress_color=C["accent"], button_color="#ffffff",
                             button_hover_color="#dfe6ff", fg_color=C["border"], switch_width=38, switch_height=20)

    def _option(self, parent, var, values, width=200):
        return ctk.CTkOptionMenu(parent, variable=var, values=values, width=width, height=34, corner_radius=10,
                                 font=self.f_body, dropdown_font=self.f_body, fg_color=C["input"],
                                 button_color=C["border"], button_hover_color=C["accent2"], text_color=C["fg"],
                                 dropdown_fg_color=C["panel"], dropdown_hover_color=C["accent2"],
                                 dropdown_text_color=C["fg"])

    def _entry(self, parent, var, **kw):
        return ctk.CTkEntry(parent, textvariable=var, height=34, corner_radius=10, font=self.f_body,
                            fg_color=C["input"], border_color=C["border"], text_color=C["fg"], **kw)

    def _segment(self, parent, var, values):
        return ctk.CTkSegmentedButton(parent, variable=var, values=values, height=32, corner_radius=10,
                                      font=self.f_small, fg_color=C["input"], unselected_color=C["input"],
                                      unselected_hover_color=C["hover"], selected_color=C["accent2"],
                                      selected_hover_color="#a78bfa", text_color=C["fg"])

    # ================= 顶部标题栏 =================
    def _build_header(self):
        self._header = tk.Canvas(self.root, height=84, highlightthickness=0, bg=C["bg"], bd=0)
        self._header.pack(fill=tk.X)
        self._header.bind("<Configure>", lambda e: self._draw_header())
        self._animate_header()

    def _draw_header(self):
        cv = self._header
        cv.delete("all")
        w = max(cv.winfo_width(), 1)
        steps = 80
        for i in range(steps):
            t = i / (steps - 1)
            x0, x1 = w * i / steps, w * (i + 1) / steps + 1
            cv.create_rectangle(x0, 0, x1, 81, fill=hex_mix("#161033", "#07162a", t), outline="")
            cv.create_rectangle(x0, 81, x1, 84, fill=hex_mix(C["accent2"], C["accent"], t), outline="")
        # YouTube 风格圆角 Logo
        self._round_rect(cv, 26, 22, 82, 62, 12, fill="#ff2e4d")
        cv.create_polygon(47, 32, 47, 52, 63, 42, fill="#ffffff", outline="")
        tid = cv.create_text(98, 34, anchor="w", text="YouTube Downloader", fill=C["fg"], font=(FONT, 19, "bold"))
        x2 = cv.bbox(tid)[2]
        self._round_rect(cv, x2 + 10, 22, x2 + 64, 46, 10, fill="", outline=C["accent"], width=2, tags="pro_box")
        cv.create_text(x2 + 37, 34, text="PRO", fill=C["accent"], font=(FONT, 11, "bold"), tags="pro")
        cv.create_text(99, 60, anchor="w", text="批量解析 · 合集下载 · 多语字幕 · 多任务并发 · 封面嵌入",
                       fill=C["muted"], font=(FONT, 10))
        self._round_rect(cv, w - 190, 26, w - 24, 58, 16, fill="#1b1f3a", outline=C["border"])
        ver = yt_dlp.version.__version__ if yt_dlp else "未安装"
        cv.create_oval(w - 176, 38, w - 168, 46, fill=C["ok"] if yt_dlp else C["err"], outline="")
        cv.create_text(w - 160, 42, anchor="w", text=f"yt-dlp {ver}", fill=C["fg"], font=(FONT, 10))

    @staticmethod
    def _round_rect(cv, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return cv.create_polygon(pts, smooth=True, **kw)

    def _animate_header(self):
        """PRO 徽章在两种霓虹色之间呼吸"""
        self._glow_phase = (self._glow_phase + 1) % 50
        col = hex_mix(C["accent"], C["accent2"], abs(25 - self._glow_phase) / 25)
        self._header.itemconfig("pro", fill=col)
        self._header.itemconfig("pro_box", outline=col)
        self.root.after(60, self._animate_header)

    # ================= 布局 =================
    def _build_ui(self):
        self._build_header()
        body = ctk.CTkFrame(self.root, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True, padx=18, pady=(14, 16))
        left = ctk.CTkScrollableFrame(body, width=400, fg_color="transparent",
                                      scrollbar_button_color=C["border"], scrollbar_button_hover_color=C["accent2"])
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        right = ctk.CTkFrame(body, fg_color="transparent")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_input_card(left)
        self._build_option_card(left)
        self._build_subtitle_card(left)
        self._build_network_card(left)
        self._build_stats(right)
        self._build_queue_card(right)
        self._build_bottom(right)

    def _build_input_card(self, parent):
        card, c = self._card(parent, "链接输入", "每行一个 · 视频 / 合集 / 频道")
        card.pack(fill=tk.X, pady=(0, 12))
        self.url_text = ctk.CTkTextbox(c, height=110, corner_radius=10, font=(MONO, 12), fg_color=C["input"],
                                       border_width=1, border_color=C["border"], text_color=C["fg"], wrap="none",
                                       scrollbar_button_color=C["border"])
        self.url_text.pack(fill=tk.X)
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill=tk.X, pady=(10, 0))
        self.parse_btn = self._btn(row, "⚡ 解析链接", self._on_parse, "primary", width=120)
        self.parse_btn.pack(side=tk.LEFT)
        self._btn(row, "粘贴", self._on_paste, width=64).pack(side=tk.LEFT, padx=8)
        self._btn(row, "清空", lambda: self.url_text.delete("1.0", tk.END), width=64).pack(side=tk.LEFT)
        self.flat_var = tk.BooleanVar(value=True)
        self._switch(row, "快速", self.flat_var).pack(side=tk.RIGHT)

    def _build_option_card(self, parent):
        card, c = self._card(parent, "下载选项")
        card.pack(fill=tk.X, pady=(0, 12))
        c.columnconfigure(1, weight=1)
        g = dict(sticky="w", pady=5)
        self._label(c, "画质").grid(row=0, column=0, **g)
        self.quality_var = tk.StringVar(value=list(QUALITY_PRESETS)[0])
        self._option(c, self.quality_var, list(QUALITY_PRESETS)).grid(row=0, column=1, sticky="ew", pady=5, padx=(12, 0))
        self._label(c, "容器").grid(row=1, column=0, **g)
        self.container_var = tk.StringVar(value="mp4")
        self._segment(c, self.container_var, ["mp4", "mkv", "webm"]).grid(row=1, column=1, sticky="ew", pady=5, padx=(12, 0))
        self._label(c, "保存到").grid(row=2, column=0, **g)
        prow = ctk.CTkFrame(c, fg_color="transparent")
        prow.grid(row=2, column=1, sticky="ew", pady=5, padx=(12, 0))
        self.path_var = tk.StringVar(value=self._default_dir())
        self._entry(prow, self.path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._btn(prow, "…", self._on_browse, width=40).pack(side=tk.LEFT, padx=(6, 0))
        self._label(c, "并发数").grid(row=3, column=0, **g)
        srow = ctk.CTkFrame(c, fg_color="transparent")
        srow.grid(row=3, column=1, sticky="ew", pady=5, padx=(12, 0))
        self.workers_var = tk.IntVar(value=3)
        self.workers_lbl = ctk.CTkLabel(srow, text="3", width=28, font=self.f_btn, text_color=C["accent"])
        slider = ctk.CTkSlider(srow, from_=1, to=8, number_of_steps=7, button_color=C["accent"],
                               progress_color=C["accent2"], button_hover_color="#5ee6ff", fg_color=C["border"],
                               command=lambda v: (self.workers_var.set(int(round(v))),
                                                  self.workers_lbl.configure(text=str(int(round(v))))))
        slider.set(3)
        slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.workers_lbl.pack(side=tk.LEFT, padx=(8, 0))
        sw = ctk.CTkFrame(c, fg_color="transparent")
        sw.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.folder_var = tk.BooleanVar(value=True)
        self.index_var = tk.BooleanVar(value=True)
        self.thumb_var = tk.BooleanVar(value=False)
        self._switch(sw, "合集子文件夹", self.folder_var).grid(row=0, column=0, sticky="w", pady=3)
        self._switch(sw, "序号前缀", self.index_var).grid(row=0, column=1, sticky="w", pady=3, padx=(16, 0))
        self._switch(sw, "嵌入封面", self.thumb_var).grid(row=1, column=0, sticky="w", pady=3)

    def _build_subtitle_card(self, parent):
        card, c = self._card(parent, "字幕")
        card.pack(fill=tk.X, pady=(0, 12))
        c.columnconfigure(1, weight=1)
        self.sub_var = tk.BooleanVar(value=False)
        self.auto_sub_var = tk.BooleanVar(value=True)
        self.embed_sub_var = tk.BooleanVar(value=False)
        self.only_sub_var = tk.BooleanVar(value=False)
        sw = ctk.CTkFrame(c, fg_color="transparent")
        sw.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        self._switch(sw, "下载字幕", self.sub_var).grid(row=0, column=0, sticky="w", pady=3)
        self._switch(sw, "含自动字幕", self.auto_sub_var).grid(row=0, column=1, sticky="w", pady=3, padx=(16, 0))
        self._switch(sw, "内嵌到视频", self.embed_sub_var).grid(row=1, column=0, sticky="w", pady=3)
        self._switch(sw, "仅下载字幕", self.only_sub_var).grid(row=1, column=1, sticky="w", pady=3, padx=(16, 0))
        self._label(c, "语言").grid(row=1, column=0, sticky="w", pady=5)
        self.sub_lang_var = tk.StringVar(value=SUB_LANG_PRESETS[0])
        ctk.CTkComboBox(c, variable=self.sub_lang_var, values=SUB_LANG_PRESETS, height=34, corner_radius=10,
                        font=self.f_body, dropdown_font=self.f_body, fg_color=C["input"], border_color=C["border"],
                        button_color=C["border"], button_hover_color=C["accent2"], text_color=C["fg"],
                        dropdown_fg_color=C["panel"], dropdown_hover_color=C["accent2"],
                        dropdown_text_color=C["fg"]).grid(row=1, column=1, sticky="ew", pady=5, padx=(12, 0))
        self._label(c, "格式").grid(row=2, column=0, sticky="w", pady=5)
        self.sub_fmt_var = tk.StringVar(value="srt")
        self._segment(c, self.sub_fmt_var, ["srt", "vtt", "ass", "原始"]).grid(
            row=2, column=1, sticky="ew", pady=5, padx=(12, 0))
        self._label(c, "逗号分隔；zh.* / all 会含大量翻译字幕，易被限流", muted=True).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

    def _build_network_card(self, parent):
        card, c = self._card(parent, "网络")
        card.pack(fill=tk.X)
        c.columnconfigure(1, weight=1)
        self._label(c, "代理").grid(row=0, column=0, sticky="w", pady=5)
        self.proxy_var = tk.StringVar(value="http://127.0.0.1:7890")
        self._entry(c, self.proxy_var, placeholder_text="留空 = 直连").grid(
            row=0, column=1, sticky="ew", pady=5, padx=(12, 0))
        self._label(c, "Cookies").grid(row=1, column=0, sticky="w", pady=5)
        self.cookie_var = tk.StringVar(value="不使用")
        self._option(c, self.cookie_var, ["不使用", "chrome", "edge", "firefox", "brave"]).grid(
            row=1, column=1, sticky="ew", pady=5, padx=(12, 0))
        self._label(c, "会员 / 年龄限制视频可读取浏览器 Cookies", muted=True).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))

    def _build_stats(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill=tk.X, pady=(0, 12))
        self.stat_labels = {}
        items = (("total", "队列总数", C["accent"]), ("checked", "已勾选", C["accent2"]),
                 ("done", "已完成", C["ok"]), ("fail", "失败", C["err"]))
        for i, (key, name, color) in enumerate(items):
            row.columnconfigure(i, weight=1, uniform="stat")
            card = ctk.CTkFrame(row, fg_color=C["card"], corner_radius=16, border_width=1, border_color=C["border"])
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 10, 0))
            ctk.CTkFrame(card, height=3, corner_radius=2, fg_color=color).pack(fill=tk.X, padx=16, pady=(10, 0))
            num = ctk.CTkLabel(card, text="0", font=self.f_big, text_color=color)
            line = ctk.CTkFrame(card, fg_color="transparent")
            line.pack(fill=tk.X, padx=18, pady=(2, 8))
            num = ctk.CTkLabel(line, text="0", font=self.f_big, text_color=color)
            num.pack(side=tk.LEFT)
            ctk.CTkLabel(line, text=name, font=self.f_small, text_color=C["muted"]).pack(side=tk.RIGHT, anchor="s")
            self.stat_labels[key] = num

    def _build_queue_card(self, parent):
        card, c = self._card(parent, "下载队列", "单击 ☑ 列切换勾选 · 双击行在浏览器打开")
        card.pack(fill=tk.BOTH, expand=True)
        bar = ctk.CTkFrame(c, fg_color="transparent")
        bar.pack(fill=tk.X, pady=(0, 10))
        actions = (("全选", lambda: self._check_all(True)), ("全不选", lambda: self._check_all(False)),
                   ("反选", self._invert_check), ("移除选中", self._remove_selected),
                   ("清空", self._clear_tasks), ("↻ 重试失败", self._retry_failed))
        for text, cmd in actions:
            self._btn(bar, text, cmd, height=30, width=70, font=self.f_small).pack(side=tk.LEFT, padx=(0, 6))
        self._btn(bar, "打开目录", self._open_dir, "violet", height=30, width=90).pack(side=tk.RIGHT)
        self.count_var = tk.StringVar(value="")
        wrap = ctk.CTkFrame(c, fg_color=C["card"], corner_radius=12, border_width=1, border_color=C["border"])
        wrap.pack(fill=tk.BOTH, expand=True)
        cols = ("chk", "idx", "title", "group", "dur", "status", "prog", "speed", "size")
        heads = ("☑", "#", "标题", "合集", "时长", "状态", "进度", "速度 · ETA", "大小")
        widths = (36, 40, 220, 110, 56, 64, 150, 120, 70)
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="extended", style="Pro.Treeview")
        for col, head, w in zip(cols, heads, widths):
            self.tree.heading(col, text=head, anchor="w" if col in ("title", "group") else "center")
            self.tree.column(col, width=w, minwidth=30, stretch=col in ("title", "group"),
                             anchor="w" if col in ("title", "group", "prog") else "center")
        ys = ctk.CTkScrollbar(wrap, command=self.tree.yview, button_color=C["border"],
                              button_hover_color=C["accent2"], fg_color="transparent")
        self.tree.configure(yscrollcommand=ys.set)
        ys.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4), pady=6)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0), pady=6)
        for st, key in STATUS_COLORS.items():
            self.tree.tag_configure(st, foreground=C[key])
        self.tree.tag_configure("unchecked", foreground=C["dim"])
        self.tree.tag_configure("odd", background="#131730")
        self.tree.tag_configure("even", background=C["card"])
        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Double-1>", self._on_tree_double)

    def _build_bottom(self, parent):
        ctl = ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=16, border_width=1, border_color=C["border"])
        ctl.pack(fill=tk.X, pady=(12, 0))
        inner = ctk.CTkFrame(ctl, fg_color="transparent")
        inner.pack(fill=tk.X, padx=16, pady=14)
        self.start_btn = self._btn(inner, "▶  开始下载", self._on_start, "ok", height=46, width=150,
                                   corner_radius=12, font=ctk.CTkFont(family=FONT, size=15, weight="bold"))
        self.start_btn.pack(side=tk.LEFT)
        self.stop_btn = self._btn(inner, "■  停止", self._on_stop, "danger", height=46, width=110,
                                  corner_radius=12, font=ctk.CTkFont(family=FONT, size=15, weight="bold"))
        self.stop_btn.pack(side=tk.LEFT, padx=(10, 0))
        self._set_btn(self.stop_btn, False)
        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(20, 0))
        top = ctk.CTkFrame(info, fg_color="transparent")
        top.pack(fill=tk.X)
        ctk.CTkLabel(top, text="总进度", font=self.f_small, text_color=C["muted"]).pack(side=tk.LEFT)
        self.pct_lbl = ctk.CTkLabel(top, text="0.0%", font=ctk.CTkFont(family=FONT, size=16, weight="bold"),
                                    text_color=C["accent"])
        self.pct_lbl.pack(side=tk.RIGHT)
        self.progress = ctk.CTkProgressBar(info, height=12, corner_radius=6, fg_color=C["input"],
                                           progress_color=C["accent"])
        self.progress.set(0)
        self.progress.pack(fill=tk.X, pady=(4, 6))
        self.status_var = tk.StringVar(value="就绪 · 粘贴链接后点击「解析链接」")
        ctk.CTkLabel(info, textvariable=self.status_var, font=self.f_small, text_color=C["muted"],
                     anchor="w").pack(fill=tk.X)
        self.log_text = ctk.CTkTextbox(parent, height=130, corner_radius=14, font=(MONO, 11), fg_color=C["log"],
                                       border_width=1, border_color=C["border"], text_color=C["muted"],
                                       wrap="word", scrollbar_button_color=C["border"],
                                       scrollbar_button_hover_color=C["accent2"])
        self.log_text.pack(fill=tk.X, pady=(12, 0))
        for key in ("ok", "err", "warn", "accent", "accent2"):
            self.log_text.tag_config(key, foreground=C[key])
        self.log_text.tag_config("time", foreground=C["dim"])
        self.log_text.configure(state="disabled")

    def _set_overall(self, pct):
        self.progress.set(max(0.0, min(1.0, pct / 100.0)))
        self.pct_lbl.configure(text=f"{pct:.1f}%")
        self.progress.configure(progress_color=C["ok"] if pct >= 99.95 else C["accent"])

    # ================= 线程安全的 UI 更新 =================
    def log(self, msg, level=None):
        self.ui_queue.put(("log", str(msg), level))

    def _ui(self, fn, *args, **kwargs):
        self.ui_queue.put(("call", fn, args, kwargs))

    def _drain_ui_queue(self):
        self.root.after(80, self._drain_ui_queue)
        logs = []
        for _ in range(800):
            try:
                item = self.ui_queue.get_nowait()
            except Empty:
                break
            if item[0] == "log":
                logs.append(item[1:])
                continue
            try:
                item[1](*item[2], **item[3])
            except Exception as exc:  # 单个 UI 回调出错不影响消息循环
                logs.append((f"UI 更新异常: {exc}", "err"))
        if logs:
            self._write_logs(logs)

    def _write_logs(self, logs):
        t = self.log_text
        t.configure(state="normal")
        now = datetime.now().strftime("%H:%M:%S")
        for msg, level in logs:
            t.insert(tk.END, f"[{now}] ", "time")
            t.insert(tk.END, msg + "\n", level or ())
        lines = int(t.index("end-1c").split(".")[0])
        if lines > 3000:
            t.delete("1.0", f"{lines - 2000}.0")
        t.see(tk.END)
        t.configure(state="disabled")

    # ================= 小工具 =================
    @staticmethod
    def _default_dir():
        """Windows 下默认使用最后一个可用盘符 (如 F:\\YouTube)，其他系统用 ~/Downloads/YouTube"""
        if os.name == "nt":
            drives = [f"{d}:\\" for d in "CDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.isdir(f"{d}:\\")]
            if drives:
                return os.path.join(drives[-1], "YouTube")
        return os.path.join(os.path.expanduser("~"), "Downloads", "YouTube")

    def _on_browse(self):
        p = filedialog.askdirectory(initialdir=self.path_var.get() or os.path.expanduser("~"))
        if p:
            self.path_var.set(p)

    def _on_paste(self):
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            return
        cur = self.url_text.get("1.0", "end-1c")
        if cur and not cur.endswith("\n"):
            self.url_text.insert(tk.END, "\n")
        self.url_text.insert(tk.END, text.strip() + "\n")

    def _open_dir(self):
        p = self.path_var.get().strip()
        try:
            os.makedirs(p, exist_ok=True)
            if os.name == "nt":
                os.startfile(p)
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", p])
        except OSError as exc:
            messagebox.showerror("错误", f"无法打开目录：{exc}")

    def _base_opts(self):
        opts = {"quiet": True, "no_warnings": False, "noprogress": True, "no_color": True,
                "socket_timeout": 20, "retries": 5, "fragment_retries": 5, "logger": _Logger(self.log)}
        # 新版 yt-dlp 解析 YouTube 需要 JS 运行时，自动启用本机已安装的 deno/node/bun
        runtimes = {name: {} for name in ("deno", "node", "bun") if shutil.which(name)}
        if runtimes:
            opts["js_runtimes"] = runtimes
        proxy = self.proxy_var.get().strip()
        if proxy:
            opts["proxy"] = proxy
        browser = self.cookie_var.get()
        if browser and browser != "不使用":
            opts["cookiesfrombrowser"] = (browser,)
        return opts

    # ================= 解析链接 =================
    def _on_parse(self):
        if yt_dlp is None:
            messagebox.showerror("缺少依赖", "请先安装 yt-dlp：pip install -U yt-dlp")
            return
        lines = self.url_text.get("1.0", tk.END).splitlines()
        urls = [u.strip() for u in lines if u.strip().startswith("http")]
        if not urls:
            messagebox.showwarning("提示", "请输入至少一个有效链接（以 http 开头）")
            return
        opts = self._base_opts()
        opts["extract_flat"] = "in_playlist" if self.flat_var.get() else False
        opts["skip_download"] = True
        self._set_btn(self.parse_btn, False)
        self.status_var.set(f"正在解析 {len(urls)} 个链接...")
        threading.Thread(target=self._parse_worker, args=(urls, opts), daemon=True).start()

    def _parse_worker(self, urls, opts):
        added = 0
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                for url in urls:
                    self.log(f"解析: {url}", "accent")
                    try:
                        info = ydl.extract_info(url, download=False)
                        items = list(self._flatten(ydl, info))
                    except Exception as exc:
                        self.log(f"解析失败: {url} -> {exc}", "err")
                        continue
                    self.log(f"✔ {info.get('title') or url}：{len(items)} 个视频", "ok")
                    self._ui(self._add_tasks, items)
                    added += len(items)
        except Exception as exc:
            self.log(f"解析异常: {exc}", "err")
        finally:
            self._ui(self._parse_done, added)

    def _flatten(self, ydl, info, group=None, depth=0):
        """把视频 / 合集 / 频道(多标签页) 展开成扁平的视频列表"""
        if info.get("_type") in ("playlist", "multi_video") or info.get("entries") is not None:
            name = info.get("title") or info.get("id") or "合集"
            group = f"{group}/{name}" if group else name
            for i, entry in enumerate(info.get("entries") or [], 1):
                if not entry:
                    continue
                is_tab = entry.get("ie_key") == "YoutubeTab" or entry.get("entries") is not None
                if is_tab and depth < 2:
                    if entry.get("entries") is None:  # 扁平模式下频道标签页需要再展开一次
                        try:
                            entry = ydl.extract_info(entry["url"], download=False)
                        except Exception as exc:
                            self.log(f"展开子合集失败: {entry.get('url')} -> {exc}", "warn")
                            continue
                    yield from self._flatten(ydl, entry, group, depth + 1)
                    continue
                yield self._make_item(entry, group, i)
        else:
            yield self._make_item(info, group, None)

    @staticmethod
    def _make_item(e, group, index):
        url = e.get("webpage_url") or e.get("url") or ""
        if (not url or not url.startswith("http")) and e.get("id"):
            url = f"https://www.youtube.com/watch?v={e['id']}"
        return {"url": url, "title": e.get("title") or e.get("id") or url, "group": group or "",
                "index": index, "duration": e.get("duration")}

    # ================= 队列管理 =================
    def _add_tasks(self, items):
        existing = {t["url"] for t in self.tasks.values()}
        for it in items:
            if not it["url"] or it["url"] in existing:
                continue
            existing.add(it["url"])
            values = ("☑", it["index"] or "-", it["title"], it["group"] or "-", fmt_time(it["duration"]),
                      "等待", self._bar(0), "-", "-")
            stripe = "odd" if len(self.tree.get_children()) % 2 else "even"
            iid = self.tree.insert("", tk.END, values=values, tags=("等待", stripe))
            it.update(iid=iid, checked=True, status="等待")
            self.tasks[iid] = it
        self._update_count()

    def _parse_done(self, added):
        self._set_btn(self.parse_btn, not self.running)
        self.status_var.set(f"解析完成，新增 {added} 项 · 勾选后点击「开始下载」")

    @staticmethod
    def _bar(p, width=12):
        p = max(0.0, min(100.0, p or 0.0))
        n = int(round(p / 100 * width))
        return "▰" * n + "▱" * (width - n) + f"  {p:.0f}%"

    def _update_count(self):
        checked = sum(1 for t in self.tasks.values() if t["checked"])
        done = sum(1 for t in self.tasks.values() if t["status"] == "完成")
        fail = sum(1 for t in self.tasks.values() if t["status"] == "失败")
        for key, val in (("total", len(self.tasks)), ("checked", checked), ("done", done), ("fail", fail)):
            self.stat_labels[key].configure(text=str(val))

    def _set_row(self, iid, **kw):
        t = self.tasks.get(iid)
        if not t or not self.tree.exists(iid):
            return
        col_index = {"title": 2, "status": 5, "prog": 6, "speed": 7, "size": 8}
        vals = list(self.tree.item(iid, "values"))
        for k, v in kw.items():
            if k in col_index:
                vals[col_index[k]] = v
        if "status" in kw:
            t["status"] = kw["status"]
        if "title" in kw:
            t["title"] = kw["title"]
        vals[0] = "☑" if t["checked"] else "☐"
        tag = t["status"] if t["checked"] else "unchecked"
        stripe = "odd" if self.tree.index(iid) % 2 else "even"
        self.tree.item(iid, values=vals, tags=(tag, stripe))

    def _on_tree_click(self, event):
        if self.running or self.tree.identify_region(event.x, event.y) != "cell":
            return None
        if self.tree.identify_column(event.x) != "#1":
            return None
        iid = self.tree.identify_row(event.y)
        if iid in self.tasks:
            self.tasks[iid]["checked"] = not self.tasks[iid]["checked"]
            self._set_row(iid)
            self._update_count()
            return "break"
        return None

    def _on_tree_double(self, event):
        iid = self.tree.identify_row(event.y)
        if iid in self.tasks and self.tree.identify_column(event.x) != "#1":
            webbrowser.open(self.tasks[iid]["url"])

    def _check_all(self, value):
        if self.running:
            return
        for iid, t in self.tasks.items():
            t["checked"] = value
            self._set_row(iid)
        self._update_count()

    def _invert_check(self):
        if self.running:
            return
        for iid, t in self.tasks.items():
            t["checked"] = not t["checked"]
            self._set_row(iid)
        self._update_count()

    def _remove_selected(self):
        if self.running:
            messagebox.showinfo("提示", "下载进行中，无法移除")
            return
        for iid in self.tree.selection():
            self.tree.delete(iid)
            self.tasks.pop(iid, None)
        for iid in self.tasks:  # 重新计算斑马纹
            self._set_row(iid)
        self._update_count()

    def _clear_tasks(self):
        if self.running:
            messagebox.showinfo("提示", "下载进行中，无法清空")
            return
        self.tree.delete(*self.tree.get_children())
        self.tasks.clear()
        self._update_count()

    def _retry_failed(self):
        if self.running:
            return
        n = 0
        for iid, t in self.tasks.items():
            if t["status"] in ("失败", "已取消"):
                t["checked"] = True
                self._set_row(iid, status="等待", prog=self._bar(0), speed="-")
                n += 1
            else:
                t["checked"] = False
                self._set_row(iid)
        self._update_count()
        if n:
            self.log(f"已重新勾选 {n} 个失败/取消的任务，点击「开始下载」重试", "warn")
            self._on_start()
        else:
            self.status_var.set("没有失败或取消的任务")

    # ================= 下载 =================
    def _collect_config(self, path):
        selector, audio = QUALITY_PRESETS[self.quality_var.get()]
        langs = [s.strip() for s in self.sub_lang_var.get().split(",") if s.strip()] or ["all"]
        return {
            "path": path, "selector": selector, "audio": audio, "container": self.container_var.get(),
            "folder": self.folder_var.get(), "prefix": self.index_var.get(), "thumb": self.thumb_var.get(),
            "sub": self.sub_var.get(), "auto_sub": self.auto_sub_var.get(),
            "embed_sub": self.embed_sub_var.get(), "only_sub": self.only_sub_var.get(),
            "sub_langs": langs, "sub_fmt": self.sub_fmt_var.get(), "base": self._base_opts(),
        }

    def _on_start(self):
        if yt_dlp is None:
            messagebox.showerror("缺少依赖", "请先安装 yt-dlp：pip install -U yt-dlp")
            return
        if self.running:
            return
        todo = [t for t in self.tasks.values() if t["checked"] and t["status"] != "完成"]
        if not todo:
            messagebox.showwarning("提示", "队列中没有勾选的待下载项")
            return
        path = self.path_var.get().strip()
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("错误", f"保存路径不可用：{exc}")
            return
        cfg = self._collect_config(path)
        workers = max(1, min(8, int(self.workers_var.get() or 1)))
        self.cancel_event.clear()
        self.running = True
        self.done_count, self.fail_count, self.total_count = 0, 0, len(todo)
        self.pending = len(todo)
        self.task_progress = {t["iid"]: 0.0 for t in todo}
        for t in todo:
            self._set_row(t["iid"], status="等待", prog=self._bar(0), speed="-")
        self._set_btn(self.start_btn, False)
        self._set_btn(self.stop_btn, True)
        self._set_btn(self.parse_btn, False)
        self._set_overall(0)
        self.log(f"开始下载 {len(todo)} 项 | 画质: {self.quality_var.get()} | 并发: {workers} | "
                 f"字幕: {'仅字幕' if cfg['only_sub'] else ('开' if cfg['sub'] else '关')}", "accent")
        self.executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="ytpro")
        for t in todo:
            snapshot = {k: t[k] for k in ("iid", "url", "title", "group", "index")}
            fut = self.executor.submit(self._download_one, snapshot, cfg)
            fut.add_done_callback(lambda f, iid=t["iid"]: self._ui(self._on_task_done, iid, f))
        self.executor.shutdown(wait=False)
        self._refresh_overall()

    def _build_opts(self, task, cfg):
        opts = dict(cfg["base"])
        out_dir = cfg["path"]
        if cfg["folder"] and task["group"]:
            out_dir = os.path.join(out_dir, *[safe_name(p) for p in task["group"].split("/")])
        name = "%(title).150B [%(id)s].%(ext)s"
        if cfg["prefix"] and task["index"]:
            name = f"{int(task['index']):03d} - " + name
        opts.update({
            "outtmpl": os.path.join(out_dir, name),
            "format": cfg["selector"],
            "noplaylist": True,
            "windowsfilenames": True,
            "continuedl": True,
            "concurrent_fragment_downloads": 4,
            "progress_hooks": [self._make_hook(task["iid"])],
            "postprocessor_hooks": [self._make_pp_hook(task["iid"])],
        })
        pps = []
        if cfg["audio"]:
            pps.append({"key": "FFmpegExtractAudio", "preferredcodec": cfg["audio"], "preferredquality": "192"})
        else:
            opts["merge_output_format"] = cfg["container"]
        if cfg["sub"] or cfg["only_sub"]:
            opts["writesubtitles"] = True
            opts["writeautomaticsub"] = cfg["auto_sub"]
            opts["subtitleslangs"] = cfg["sub_langs"]
            opts["sleep_interval_subtitles"] = 2  # 降低字幕接口 429 限流概率
            if cfg["sub_fmt"] != "原始":
                opts["subtitlesformat"] = f"{cfg['sub_fmt']}/best"
                pps.append({"key": "FFmpegSubtitlesConvertor", "format": cfg["sub_fmt"], "when": "before_dl"})
            if cfg["embed_sub"] and not cfg["audio"] and not cfg["only_sub"]:
                pps.append({"key": "FFmpegEmbedSubtitle", "already_have_subtitle": True})
        if cfg["only_sub"]:
            opts["skip_download"] = True
        elif cfg["thumb"]:
            opts["writethumbnail"] = True
            pps.append({"key": "FFmpegThumbnailsConvertor", "format": "jpg", "when": "before_dl"})
            pps.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})
        opts["postprocessors"] = pps
        return opts

    def _make_hook(self, iid):
        state = {"t": 0.0, "part": 0}

        def hook(d):
            if self.cancel_event.is_set():
                raise CancelledByUser("用户取消")
            st = d.get("status")
            if st == "downloading":
                now = time.time()
                if now - state["t"] < 0.25:
                    return
                state["t"] = now
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                done = d.get("downloaded_bytes") or 0
                p = done * 100.0 / total if total else 0.0
                title = (d.get("info_dict") or {}).get("title")
                spd = f"{fmt_size(d.get('speed'))}/s · {fmt_time(d.get('eta'))}"
                part = f" (分段{state['part'] + 1})" if state["part"] else ""
                self._ui(self._on_progress, iid, p, spd, fmt_size(total) + part, title)
            elif st == "finished":
                state["part"] += 1
                self._ui(self._set_row, iid, status="处理中", prog=self._bar(100), speed="合并/处理中")
        return hook

    def _make_pp_hook(self, iid):
        def hook(d):
            if d.get("status") == "started":
                self._ui(self._set_row, iid, status="处理中", speed=str(d.get("postprocessor") or "处理中"))
        return hook

    def _on_progress(self, iid, p, spd, size, title):
        if not self.running:
            return
        self.task_progress[iid] = p
        kw = {"status": "下载中", "prog": self._bar(p), "speed": spd, "size": size}
        t = self.tasks.get(iid)
        if title and t and t["title"] != title:
            kw["title"] = title
        self._set_row(iid, **kw)
        self._refresh_overall()

    def _refresh_overall(self):
        if not self.total_count:
            return
        pct = sum(self.task_progress.values()) / self.total_count
        self._set_overall(pct)
        self.status_var.set(f"总进度 {pct:.1f}%  ·  成功 {self.done_count}  ·  失败 {self.fail_count}"
                            f"  ·  剩余 {self.pending}  ·  共 {self.total_count}")

    def _download_one(self, task, cfg):
        """工作线程：下载单个视频，返回 (结果, 错误信息)"""
        if self.cancel_event.is_set():
            return "cancel", None
        self._ui(self._set_row, task["iid"], status="下载中", prog=self._bar(0), speed="连接中...")
        try:
            return self._run_ydl(task, cfg)
        except CancelledByUser:
            return "cancel", None
        except Exception as exc:
            if self.cancel_event.is_set() or "用户取消" in str(exc):
                return "cancel", None
            # 字幕失败(如 429 限流)不应拖垮整个视频：去掉字幕重试一次
            if "subtitle" in str(exc).lower() and cfg["sub"] and not cfg["only_sub"]:
                self.log(f"⚠ 字幕下载失败，改为无字幕重试: {task['title']}", "warn")
                try:
                    return self._run_ydl(task, dict(cfg, sub=False))
                except Exception as exc2:
                    if self.cancel_event.is_set():
                        return "cancel", None
                    return "fail", str(exc2)
            return "fail", str(exc)

    def _run_ydl(self, task, cfg):
        with yt_dlp.YoutubeDL(self._build_opts(task, cfg)) as ydl:
            code = ydl.download([task["url"]])
        if self.cancel_event.is_set():
            return "cancel", None
        return ("ok", None) if code == 0 else ("fail", f"yt-dlp 返回码 {code}")

    def _on_task_done(self, iid, future):
        try:
            result, err = future.result()
        except Exception as exc:
            result, err = "fail", str(exc)
        title = self.tasks.get(iid, {}).get("title", iid)
        if result == "ok":
            self.done_count += 1
            self.task_progress[iid] = 100.0
            self._set_row(iid, status="完成", prog=self._bar(100), speed="✔")
            self.log(f"✔ 完成: {title}", "ok")
        elif result == "cancel":
            self._set_row(iid, status="已取消", speed="-")
        else:
            self.fail_count += 1
            self.task_progress[iid] = 100.0  # 失败也计入已处理，保证总进度能走到终点
            self._set_row(iid, status="失败", speed="✖")
            self.log(f"✖ 失败: {title} -> {err}", "err")
        self.pending -= 1
        self._refresh_overall()
        self._update_count()
        if self.pending <= 0:
            self._finish_all()

    def _finish_all(self):
        self.running = False
        self.executor = None
        self._set_btn(self.start_btn, True)
        self._set_btn(self.stop_btn, False)
        self._set_btn(self.parse_btn, True)
        cancelled = self.cancel_event.is_set()
        msg = (f"{'已停止' if cancelled else '全部结束'}：成功 {self.done_count}，"
               f"失败 {self.fail_count}，共 {self.total_count}")
        self.status_var.set(msg)
        self.log(msg, "warn" if (cancelled or self.fail_count) else "ok")
        if not cancelled:
            self.root.bell()
            messagebox.showinfo("下载结束", msg)

    def _on_stop(self):
        if not self.running:
            return
        self.cancel_event.set()
        self._set_btn(self.stop_btn, False)
        self.status_var.set("正在停止，等待当前任务中断...")
        self.log("收到停止请求，正在中断任务...", "warn")

    def _on_close(self):
        if self.running and not messagebox.askyesno("确认退出", "仍有任务在下载，确定退出吗？"):
            return
        self.cancel_event.set()
        self.root.destroy()


def main():
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    # 窗口图标：打包后从 PyInstaller 临时目录读取；customtkinter 会在 200ms 后覆盖图标，所以延迟设置
    icon = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "youtube_pro.ico")
    if os.name == "nt" and os.path.exists(icon):
        root.after(300, lambda: root.iconbitmap(icon))
    ProDownloader(root)
    root.mainloop()


if __name__ == "__main__":
    main()
