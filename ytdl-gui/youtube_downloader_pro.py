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


# ---------------- 视频源格式分析工具 ----------------
LANG_NAMES = {
    "zh": "中文", "zh-hans": "简体中文", "zh-hant": "繁体中文", "zh-cn": "简体中文", "zh-tw": "繁体中文",
    "en": "英语", "ja": "日语", "ko": "韩语", "fr": "法语", "de": "德语", "es": "西班牙语", "it": "意大利语",
    "pt": "葡萄牙语", "ru": "俄语", "ar": "阿拉伯语", "hi": "印地语", "th": "泰语", "vi": "越南语",
    "id": "印尼语", "tr": "土耳其语", "pl": "波兰语", "nl": "荷兰语", "uk": "乌克兰语", "bn": "孟加拉语",
    "ta": "泰米尔语", "te": "泰卢固语", "mr": "马拉地语", "ml": "马拉雅拉姆语", "pa": "旁遮普语", "ms": "马来语",
    "cs": "捷克语", "sv": "瑞典语", "fi": "芬兰语", "da": "丹麦语", "no": "挪威语", "he": "希伯来语",
    "el": "希腊语", "hu": "匈牙利语", "ro": "罗马尼亚语", "fil": "菲律宾语", "und": "未知",
}
# ffmpeg / mp4 容器要求 ISO 639-2 三字母语言码
ISO3 = {
    "zh": "chi", "en": "eng", "ja": "jpn", "ko": "kor", "fr": "fre", "de": "ger", "es": "spa", "it": "ita",
    "pt": "por", "ru": "rus", "ar": "ara", "hi": "hin", "th": "tha", "vi": "vie", "id": "ind", "tr": "tur",
    "pl": "pol", "nl": "dut", "uk": "ukr", "bn": "ben", "ta": "tam", "te": "tel", "mr": "mar", "ml": "mal",
    "pa": "pan", "ms": "may", "cs": "cze", "sv": "swe", "fi": "fin", "da": "dan", "no": "nor", "he": "heb",
    "el": "gre", "hu": "hun", "ro": "rum", "fil": "fil",
}
# 视频编码: 显示名 -> yt-dlp vcodec 正则（用于把单个视频的选择套用到整个合集）
VCODEC_FAMILY = {"H.264": "^avc1", "VP9": "^vp0?9", "AV1": "^av01", "H.265": "^(hev1|hvc1)"}


def lang_name(code):
    c = str(code or "und").lower()
    return LANG_NAMES.get(c) or LANG_NAMES.get(c.split("-")[0]) or code or "未知"


def iso3(code):
    c = str(code or "und").lower().split("-")[0]
    return ISO3.get(c, c if len(c) == 3 else "und")


def vcodec_family(vcodec):
    v = str(vcodec or "").lower()
    for name, pattern in VCODEC_FAMILY.items():
        if re.match(pattern, v):
            return name
    return v.split(".")[0].upper() or "?"


def acodec_family(acodec):
    a = str(acodec or "").lower()
    if a.startswith("mp4a"):
        return "AAC"
    return a.split(".")[0].upper() or "?"


def est_size(f, duration):
    """返回 (字节数, 是否精确)。m3u8 等无 filesize 的格式按 码率 × 时长 估算"""
    if f.get("filesize"):
        return f["filesize"], True
    if f.get("filesize_approx"):
        return f["filesize_approx"], False
    rate = f.get("tbr") or f.get("vbr") or f.get("abr")
    if rate and duration:
        return rate * 125 * duration, False
    return None, False


def build_rule_selector(height, vfam, langs, afam, audio_only):
    """把在某个视频上的选择转成通用规则，套用到合集中其他视频（缺失的语言/编码自动降级）"""
    af = {"AAC": "[acodec^=mp4a]", "OPUS": "[acodec=opus]"}.get(afam, "")

    def aud(lang):
        if not lang or lang == "und":
            return f"(ba{af}/ba)"
        base = lang.split("-")[0]
        return f"(ba[language={lang}]{af}/ba[language={lang}]/ba[language^={base}])"

    if audio_only:
        return f"{aud(langs[0])}/ba/b" if langs else "ba/b"
    hf = f"[height<={height}]" if height else ""
    vf = f"[vcodec~='{VCODEC_FAMILY[vfam]}']" if vfam in VCODEC_FAMILY else ""
    video = f"(bv*{hf}{vf}/bv*{hf})"
    main = video + "+" + ("+".join(aud(lang) for lang in langs) if langs else "ba")
    return f"{main}/{video}+ba/b{hf}/b"


def guess_sub_lang(path):
    """从 xxx.zh-Hans.srt 这类文件名推测语言码"""
    parts = os.path.basename(path).rsplit(".", 2)
    if len(parts) == 3 and re.fullmatch(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*", parts[1]):
        return parts[1]
    return "und"


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
        self._parse_new = []
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
        card, c = self._card(parent, "下载选项", "未单独设置格式的视频使用")
        card.pack(fill=tk.X, pady=(0, 12))
        c.columnconfigure(1, weight=1)
        g = dict(sticky="w", pady=5)
        self._label(c, "默认画质").grid(row=0, column=0, **g)
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
        self._label(c, "默认语言").grid(row=1, column=0, sticky="w", pady=5)
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
        self._label(c, "批量默认规则；双击队列中的视频可按实际存在的\n字幕 / 音轨勾选，并添加本地字幕文件",
                    muted=True, justify="left").grid(
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
        card, c = self._card(parent, "下载队列", "单击 ☑ 切换勾选 · 双击行按视频源选择 画质/音轨/字幕 · 右键更多")
        card.pack(fill=tk.BOTH, expand=True)
        bar = ctk.CTkFrame(c, fg_color="transparent")
        bar.pack(fill=tk.X, pady=(0, 10))
        actions = (("全选", lambda: self._check_all(True)), ("全不选", lambda: self._check_all(False)),
                   ("反选", self._invert_check), ("移除选中", self._remove_selected),
                   ("清空", self._clear_tasks), ("↻ 重试失败", self._retry_failed))
        for text, cmd in actions:
            self._btn(bar, text, cmd, height=30, width=70, font=self.f_small).pack(side=tk.LEFT, padx=(0, 6))
        self._btn(bar, "打开目录", self._open_dir, "violet", height=30, width=90).pack(side=tk.RIGHT)
        self._btn(bar, "⚙ 格式 / 音轨 / 字幕", self._open_format_dialog, "primary", height=30,
                  width=150).pack(side=tk.RIGHT, padx=(0, 8))
        wrap = ctk.CTkFrame(c, fg_color=C["card"], corner_radius=12, border_width=1, border_color=C["border"])
        wrap.pack(fill=tk.BOTH, expand=True)
        cols = ("chk", "idx", "title", "group", "dur", "fmt", "status", "prog", "speed", "size")
        heads = ("☑", "#", "标题", "合集", "时长", "格式", "状态", "进度", "速度 · ETA", "大小")
        widths = (36, 40, 200, 100, 56, 150, 64, 140, 120, 80)
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
        self.tree.bind("<Button-3>", self._on_tree_menu)

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
        self._parse_new = []
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
                    if info.get("formats") and len(items) == 1:
                        items[0]["info"] = info  # 非快速模式下已拿到完整格式，直接缓存
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
                      "默认规则", "等待", self._bar(0), "-", "-")
            stripe = "odd" if len(self.tree.get_children()) % 2 else "even"
            iid = self.tree.insert("", tk.END, values=values, tags=("等待", stripe))
            it.update(iid=iid, checked=True, status="等待")
            self.tasks[iid] = it
            self._parse_new.append(iid)
        self._update_count()

    def _parse_done(self, added):
        self._set_btn(self.parse_btn, not self.running)
        self.status_var.set(f"解析完成，新增 {added} 项 · 双击视频可按视频源选择 画质/音轨/字幕")
        # 只解析出一个视频时，直接弹出格式选择（画质、音轨、字幕全部来自视频源）
        if len(self._parse_new) == 1 and not self.running:
            self._open_format_dialog(self._parse_new[0])

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
        col_index = {"title": 2, "fmt": 5, "status": 6, "prog": 7, "speed": 8, "size": 9}
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
            self._open_format_dialog(iid)

    def _on_tree_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid not in self.tasks:
            return
        if iid not in self.tree.selection():
            self.tree.selection_set(iid)
        menu = tk.Menu(self.root, tearoff=0, bg=C["panel"], fg=C["fg"], activebackground=C["accent2"],
                       activeforeground="#ffffff", bd=0, font=(FONT, 10))
        menu.add_command(label="⚙  选择画质 / 音轨 / 字幕", command=lambda: self._open_format_dialog(iid))
        menu.add_command(label="↺  恢复默认规则", command=self._reset_custom_selected)
        menu.add_separator()
        menu.add_command(label="🌐  在浏览器打开", command=lambda: webbrowser.open(self.tasks[iid]["url"]))
        menu.add_command(label="📋  复制链接", command=lambda: (self.root.clipboard_clear(),
                                                             self.root.clipboard_append(self.tasks[iid]["url"])))
        menu.tk_popup(event.x_root, event.y_root)

    # ================= 视频源分析 / 单视频自定义 =================
    def _analyze(self, iid, on_done):
        """后台读取单个视频的完整信息(全部格式/音轨/字幕)，结果缓存在 task['info']"""
        task = self.tasks.get(iid)
        if not task:
            return
        if task.get("info"):
            on_done(task["info"], None)
            return
        opts = self._base_opts()
        opts.update(skip_download=True, noplaylist=True)
        url = task["url"]

        def done(info, err):
            if info and iid in self.tasks:
                self.tasks[iid]["info"] = info
                self.tasks[iid]["duration"] = info.get("duration")
                if self.tree.exists(iid):
                    vals = list(self.tree.item(iid, "values"))
                    vals[4] = fmt_time(info.get("duration"))
                    self.tree.item(iid, values=vals)
                self._set_row(iid, title=info.get("title") or self.tasks[iid]["title"])
            on_done(info, err)

        def work():
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                self._ui(done, info, None)
            except Exception as exc:
                self._ui(done, None, exc)

        self.log(f"读取视频源格式: {url}", "accent")
        threading.Thread(target=work, daemon=True).start()

    def _open_format_dialog(self, iid=None):
        if yt_dlp is None:
            messagebox.showerror("缺少依赖", "请先安装 yt-dlp：pip install -U yt-dlp")
            return
        if self.running:
            messagebox.showinfo("提示", "下载进行中，结束后再修改格式")
            return
        if iid is None:
            sel = [i for i in self.tree.selection() if i in self.tasks]
            iid = sel[0] if sel else None
        if not iid:
            messagebox.showinfo("提示", "请先在下载队列中选中一个视频")
            return
        FormatDialog(self, iid)

    def _apply_custom(self, iid, custom, to_checked=False):
        targets = [iid] + ([i for i, t in self.tasks.items() if t["checked"] and i != iid] if to_checked else [])
        for i in targets:
            cu = custom if i == iid else custom["rule"]
            self.tasks[i]["custom"] = cu
            self._set_row(i, fmt=cu["label"], size=("≈" + fmt_size(cu["size"])) if cu.get("size") else "-")
        self.log(f"已应用格式设置到 {len(targets)} 个视频: {custom['label']}", "ok")

    def _reset_custom_selected(self):
        if self.running:
            return
        for iid in self.tree.selection():
            if iid in self.tasks:
                self.tasks[iid].pop("custom", None)
                self._set_row(iid, fmt="默认规则", size="-")

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
            snapshot["custom"] = t.get("custom")
            fut = self.executor.submit(self._download_one, snapshot, cfg)
            fut.add_done_callback(lambda f, iid=t["iid"]: self._ui(self._on_task_done, iid, f))
        self.executor.shutdown(wait=False)
        self._refresh_overall()

    @staticmethod
    def _resolve(task, cfg):
        """合并全局默认规则与单个视频的自定义选择（custom 由格式对话框生成）"""
        r = {"selector": cfg["selector"], "audio_conv": cfg["audio"], "container": cfg["container"],
             "multi_audio": False, "audio_only": bool(cfg["audio"]), "sub_on": cfg["sub"] or cfg["only_sub"],
             "auto": cfg["auto_sub"], "langs": cfg["sub_langs"], "embed": cfg["embed_sub"],
             "keep_subs": True, "local_subs": []}
        cu = task.get("custom")
        if cu:
            r.update(selector=cu["selector"], multi_audio=cu["multi_audio"], audio_only=cu["audio_only"],
                     audio_conv=cfg["audio"] if cu["audio_only"] else None,
                     container=cu.get("container") or cfg["container"],
                     sub_on=bool(cu["subs"]), auto=any(a for _, a in cu["subs"]),
                     langs=[re.escape(code) for code, _ in cu["subs"]],
                     embed=cu["embed"], keep_subs=cu["keep_subs"], local_subs=list(cu["local_subs"]))
        if cfg.get("no_sub"):
            r["sub_on"] = False
        return r

    def _build_opts(self, task, cfg, final_paths=None):
        opts = dict(cfg["base"])
        rs = self._resolve(task, cfg)
        out_dir = cfg["path"]
        if cfg["folder"] and task["group"]:
            out_dir = os.path.join(out_dir, *[safe_name(p) for p in task["group"].split("/")])
        name = "%(title).150B [%(id)s].%(ext)s"
        if cfg["prefix"] and task["index"]:
            name = f"{int(task['index']):03d} - " + name
        state = {"t": 0.0, "total": 0, "prev": 0}  # total 来自视频源(下载前探测)，prev 为已完成分段字节
        opts.update({
            "outtmpl": os.path.join(out_dir, name),
            "format": rs["selector"],
            "noplaylist": True,
            "windowsfilenames": True,
            "continuedl": True,
            "concurrent_fragment_downloads": 4,
            "progress_hooks": [self._make_hook(task["iid"], state)],
            "postprocessor_hooks": [self._make_pp_hook(task["iid"])],
            "post_hooks": [final_paths.append] if final_paths is not None else [],
            "_size_state": state,  # 仅供 _run_ydl 读取，yt-dlp 会忽略未知参数
        })
        if rs["multi_audio"]:
            opts["allow_multiple_audio_streams"] = True
        pps = []
        if rs["audio_conv"]:
            pps.append({"key": "FFmpegExtractAudio", "preferredcodec": rs["audio_conv"], "preferredquality": "192"})
        elif not rs["audio_only"]:
            opts["merge_output_format"] = rs["container"]
        if rs["sub_on"] and rs["langs"]:
            opts["writesubtitles"] = True
            opts["writeautomaticsub"] = rs["auto"]
            opts["subtitleslangs"] = rs["langs"]
            opts["sleep_interval_subtitles"] = 2  # 降低字幕接口 429 限流概率
            if cfg["sub_fmt"] != "原始":
                opts["subtitlesformat"] = f"{cfg['sub_fmt']}/best"
                pps.append({"key": "FFmpegSubtitlesConvertor", "format": cfg["sub_fmt"], "when": "before_dl"})
            if rs["embed"] and not rs["audio_only"] and not cfg["only_sub"]:
                pps.append({"key": "FFmpegEmbedSubtitle", "already_have_subtitle": rs["keep_subs"]})
        if cfg["only_sub"]:
            opts["skip_download"] = True
        elif cfg["thumb"]:
            opts["writethumbnail"] = True
            pps.append({"key": "FFmpegThumbnailsConvertor", "format": "jpg", "when": "before_dl"})
            pps.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})
        opts["postprocessors"] = pps
        return opts

    def _make_hook(self, iid, state):
        """视频+多条音轨会分多段下载：进度 = (已完成分段 + 当前分段) / 视频源总大小"""
        def hook(d):
            if self.cancel_event.is_set():
                raise CancelledByUser("用户取消")
            st = d.get("status")
            part_total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            if st == "downloading":
                now = time.time()
                if now - state["t"] < 0.25:
                    return
                state["t"] = now
                total = max(state["total"], state["prev"] + part_total)
                p = (state["prev"] + done) * 100.0 / total if total else 0.0
                title = (d.get("info_dict") or {}).get("title")
                spd = f"{fmt_size(d.get('speed'))}/s · {fmt_time(d.get('eta'))}"
                self._ui(self._on_progress, iid, min(p, 99.9), spd, fmt_size(total), title)
            elif st == "finished":
                state["prev"] += part_total or done
                if not state["total"] or state["prev"] >= state["total"] * 0.98:
                    self._ui(self._set_row, iid, status="处理中", prog=self._bar(100), speed="合并/处理中")
        return hook

    def _make_size_probe(self, iid, state):
        """before_dl 阶段读取 yt-dlp 最终选中的格式，按视频源计算真实总大小"""
        from yt_dlp.postprocessor.common import PostProcessor

        app = self

        class SizeProbe(PostProcessor):
            def run(self, info):
                fmts = info.get("requested_formats") or [info]
                total = sum(est_size(f, info.get("duration"))[0] or 0 for f in fmts)
                state["total"] = int(total)
                audios = sum(1 for f in fmts if f.get("acodec") not in (None, "none"))
                h = max((f.get("height") or 0) for f in fmts)
                desc = (f"{h}p · " if h else "") + f"{audios} 音轨"
                app.log(f"选定格式 {info.get('format_id')} ({desc})，源大小 ≈ {fmt_size(total)}", "accent2")
                app._ui(app._set_row, iid, size=fmt_size(total) if total else "-")
                return [], info
        return SizeProbe()

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
            if "subtitle" in str(exc).lower() and not cfg["only_sub"] and not cfg.get("no_sub"):
                self.log(f"⚠ 在线字幕下载失败，改为不下载在线字幕重试: {task['title']}", "warn")
                try:
                    return self._run_ydl(task, dict(cfg, no_sub=True))
                except Exception as exc2:
                    if self.cancel_event.is_set():
                        return "cancel", None
                    return "fail", str(exc2)
            return "fail", str(exc)

    def _run_ydl(self, task, cfg):
        final_paths = []
        opts = self._build_opts(task, cfg, final_paths)
        state = opts.pop("_size_state")
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.add_post_processor(self._make_size_probe(task["iid"], state), when="before_dl")
            code = ydl.download([task["url"]])
        if self.cancel_event.is_set():
            return "cancel", None
        if code != 0:
            return "fail", f"yt-dlp 返回码 {code}"
        rs = self._resolve(task, cfg)
        if rs["local_subs"] and not rs["audio_only"] and not cfg["only_sub"]:
            video = next((p for p in reversed(final_paths) if p and os.path.exists(p)), None)
            if not video:
                return "fail", "下载完成但找不到输出文件，无法内嵌自定义字幕"
            self._ui(self._set_row, task["iid"], status="处理中", speed="内嵌本地字幕")
            self._mux_local_subs(video, rs["local_subs"])
            self.log(f"已内嵌 {len(rs['local_subs'])} 个本地字幕: {os.path.basename(video)}", "ok")
        return "ok", None

    @staticmethod
    def _mux_local_subs(video, subs):
        """用 ffmpeg 把本地字幕文件无损封装进视频（视频/音轨/已有字幕全部 copy）"""
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("未找到 ffmpeg，无法内嵌自定义字幕")
        base, ext = os.path.splitext(video)
        ext = ext.lower()
        tmp = f"{base}.subtmp{ext}"
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", video]
        for path, _, _ in subs:
            try:  # 非 UTF-8 的中文字幕(GBK)需要告诉 ffmpeg 编码，否则乱码
                with open(path, "rb") as fh:
                    fh.read().decode("utf-8-sig")
            except UnicodeDecodeError:
                cmd += ["-sub_charenc", "CP936"]
            except OSError as exc:
                raise RuntimeError(f"无法读取字幕文件 {path}: {exc}")
            cmd += ["-i", path]
        cmd += ["-map", "0:v?", "-map", "0:a?"]
        cmd += [x for k in range(len(subs)) for x in ("-map", f"{k + 1}:0")]
        cmd += ["-map", "0:s?"]  # 保留 yt-dlp 已内嵌的在线字幕，排在本地字幕之后
        if ext == ".mkv":
            cmd += ["-map", "0:t?"]
        cmd += ["-c", "copy"]
        scodec = {".mp4": "mov_text", ".m4v": "mov_text", ".mov": "mov_text", ".webm": "webvtt"}.get(ext)
        for k, (path, lang, title) in enumerate(subs):
            # 文本字幕必须重新编码(不能 copy)，-sub_charenc 才会生效；srt/ass 重编码不丢样式
            codec = scodec or ("ass" if path.lower().endswith((".ass", ".ssa")) else "srt")
            cmd += [f"-c:s:{k}", codec, f"-metadata:s:s:{k}", f"language={iso3(lang)}",
                    f"-metadata:s:s:{k}", f"title={title or lang_name(lang)}"]
        # 多音轨时只让第 1 条音轨为默认；本地字幕第 1 条设为默认字幕
        cmd += ["-disposition:a", "0", "-disposition:a:0", "default",
                "-disposition:s", "0", "-disposition:s:0", "default", "-map_metadata", "0", tmp]
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                             creationflags=flags)
        if res.returncode != 0:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise RuntimeError(f"ffmpeg 内嵌字幕失败: {res.stderr.strip()[-400:]}")
        os.replace(tmp, video)

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



class FormatDialog:
    """按视频源真实数据选择：画质(含大小) / 音轨(可多选合并) / 在线字幕 / 本地字幕文件"""

    def __init__(self, app, iid):
        self.app, self.iid = app, iid
        self.task = app.tasks[iid]
        self.info = None
        self.audio_checked = []      # 按勾选顺序保存语言码，第一条为默认音轨
        self.sub_checked = set()     # {"m:zh-Hans", "a:en-orig", ...}
        self.local_subs = []         # [[path, lang, title], ...]
        w = self.win = ctk.CTkToplevel(app.root)
        w.title(f"选择格式 · 音轨 · 字幕 — {self.task['title'][:60]}")
        w.geometry("1280x840")
        w.minsize(1100, 720)
        w.configure(fg_color=C["bg"])
        w.transient(app.root)
        w.after(250, self._grab)
        self.loading = ctk.CTkLabel(w, text="⏳  正在读取视频源：画质 / 音轨 / 字幕 ...",
                                    font=app.f_title, text_color=C["accent"])
        self.loading.pack(expand=True)
        app._analyze(iid, self._on_info)

    def _grab(self):
        if self.win.winfo_exists():
            self.win.lift()
            self.win.focus_force()
            try:
                self.win.grab_set()
            except tk.TclError:
                pass

    def _on_info(self, info, err):
        if not self.win.winfo_exists():
            return
        if err or not info:
            self.loading.configure(text=f"✖ 读取失败：{err}", text_color=C["err"], wraplength=900)
            return
        if not info.get("formats"):
            self.loading.configure(text="✖ 该链接没有可用的格式（可能是合集/频道链接，请先解析出单个视频）",
                                   text_color=C["err"])
            return
        self.info = info
        self.loading.destroy()
        self._build()

    # ---------- 通用 ----------
    def _tree(self, parent, cols, heads, widths, select="browse", stretch=()):
        wrap = ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=10, border_width=1, border_color=C["border"])
        wrap.pack(fill=tk.BOTH, expand=True)
        tv = ttk.Treeview(wrap, columns=cols, show="headings", selectmode=select, style="Pro.Treeview", height=6)
        for col, head, width in zip(cols, heads, widths):
            anchor = "w" if col in stretch else "center"
            tv.heading(col, text=head, anchor=anchor)
            tv.column(col, width=width, minwidth=30, stretch=col in stretch, anchor=anchor)
        sb = ctk.CTkScrollbar(wrap, command=tv.yview, button_color=C["border"],
                              button_hover_color=C["accent2"], fg_color="transparent")
        tv.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4), pady=6)
        tv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0), pady=6)
        tv.tag_configure("on", foreground=C["accent"], background="#182a45")
        tv.tag_configure("off", foreground=C["fg"], background=C["card"])
        tv.tag_configure("muted", foreground=C["muted"], background=C["card"])
        return tv

    def _container(self):
        return self.app.container_var.get()

    def _build(self):
        app, info = self.app, self.info
        w = self.win
        self.duration = info.get("duration")
        fmts = info.get("formats") or []
        self.videos = sorted(
            [f for f in fmts if f.get("vcodec") not in (None, "none") and f.get("format_id")],
            key=lambda f: (f.get("height") or 0, f.get("fps") or 0,
                           str(f.get("protocol", "")).startswith("http"), f.get("tbr") or 0), reverse=True)
        self.audios = [f for f in fmts if f.get("vcodec") == "none" and f.get("acodec") not in (None, "none")]
        self.fmt_by_id = {f["format_id"]: f for f in fmts if f.get("format_id")}
        langs = {f.get("language") or "und" for f in self.audios}
        manual = {k: v for k, v in (info.get("subtitles") or {}).items() if k != "live_chat" and v}
        auto = {k: v for k, v in (info.get("automatic_captions") or {}).items() if v}
        self.manual_subs, self.auto_subs = manual, auto

        head = ctk.CTkFrame(w, fg_color=C["card"], corner_radius=14, border_width=1, border_color=C["border"])
        head.pack(fill=tk.X, padx=16, pady=(14, 10))
        ctk.CTkLabel(head, text=info.get("title") or self.task["title"], font=app.f_title, text_color=C["fg"],
                     anchor="w", wraplength=1180, justify="left").pack(fill=tk.X, padx=16, pady=(12, 2))
        meta = (f"{info.get('uploader') or info.get('channel') or '未知作者'}  ·  时长 {fmt_time(self.duration)}  ·  "
                f"{len(self.videos)} 个画面格式  ·  {len(langs)} 种音轨语言  ·  "
                f"{len(manual)} 条人工字幕 / {len(auto)} 条自动字幕")
        ctk.CTkLabel(head, text=meta, font=app.f_small, text_color=C["muted"], anchor="w").pack(
            fill=tk.X, padx=16, pady=(0, 12))

        # 底部操作栏（先 pack 到底部，保证窗口缩小时按钮始终可见）
        foot = ctk.CTkFrame(w, fg_color=C["card"], corner_radius=14, border_width=1, border_color=C["border"])
        foot.pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=(0, 14))
        info_col = ctk.CTkFrame(foot, fg_color="transparent")
        info_col.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=16, pady=10)
        self.size_lbl = ctk.CTkLabel(info_col, text="", font=ctk.CTkFont(family=FONT, size=15, weight="bold"),
                                     text_color=C["accent"], anchor="w")
        self.size_lbl.pack(fill=tk.X)
        self.hint_lbl = ctk.CTkLabel(info_col, text="", font=app.f_small, text_color=C["muted"], anchor="w",
                                     justify="left", wraplength=640)
        self.hint_lbl.pack(fill=tk.X)
        app._btn(foot, "✔ 应用到此视频", self._apply_one, "ok", height=40, width=140).pack(
            side=tk.RIGHT, padx=(0, 16), pady=10)
        app._btn(foot, "按此规则应用到所有勾选项", self._apply_all, "violet", height=40, width=200).pack(
            side=tk.RIGHT, padx=8, pady=10)
        app._btn(foot, "取消", self.win.destroy, height=40, width=80).pack(side=tk.RIGHT, pady=10)

        grid = ctk.CTkFrame(w, fg_color="transparent")
        grid.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 10))
        grid.columnconfigure(0, weight=11, uniform="c")
        grid.columnconfigure(1, weight=10, uniform="c")
        grid.rowconfigure(0, weight=1)
        grid.rowconfigure(1, weight=1)
        self._build_video(grid)
        self._build_audio(grid)
        self._build_subs(grid)
        self._build_local(grid)
        self._update_summary()

    # ---------- 画质 ----------
    def _build_video(self, grid):
        card, c = self.app._card(grid, "画质", "来自视频源 · 大小按源文件/码率计算")
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 6))
        cols = ("res", "fps", "codec", "ext", "hdr", "rate", "size", "note")
        heads = ("分辨率", "帧率", "编码", "封装", "动态范围", "码率", "大小", "备注")
        widths = (70, 46, 64, 52, 70, 70, 86, 170)
        self.vtree = self._tree(c, cols, heads, widths, stretch=("note",))
        self.vtree.insert("", tk.END, iid="__none__", tags=("muted",),
                          values=("🎵 仅音频", "", "", "", "", "", "", "不下载视频画面"))
        for f in self.videos:
            size, exact = est_size(f, self.duration)
            notes = []
            if f.get("acodec") not in (None, "none"):
                notes.append("自带音频")
            if "m3u8" in str(f.get("protocol")):
                notes.append("HLS")
            fn = f.get("format_note") or ""
            if fn and not re.fullmatch(r"\d+p\d*", fn):
                notes.append(fn)
            notes.append(f"id {f['format_id']}")
            res = f"{f['height']}p" if f.get("height") else (f.get("resolution") or "?")
            self.vtree.insert("", tk.END, iid=f["format_id"], tags=("off",), values=(
                res, int(f["fps"]) if f.get("fps") else "-", vcodec_family(f.get("vcodec")), f.get("ext") or "-",
                f.get("dynamic_range") or "SDR", f"{int(f['tbr'])}k" if f.get("tbr") else "-",
                ("" if exact else "≈") + fmt_size(size), " · ".join(notes)))
        self.vtree.bind("<<TreeviewSelect>>", lambda e: self._update_summary())
        self.vtree.selection_set(self._default_video())
        self.vtree.see(self.vtree.selection()[0])

    def _default_video(self):
        cu = self.task.get("custom") or {}
        if cu.get("mode") == "exact":
            vid = cu.get("video") or "__none__"
            if vid == "__none__" or vid in self.fmt_by_id:
                return vid
        preset = self.app.quality_var.get()
        if QUALITY_PRESETS[preset][1] or not self.videos:
            return "__none__"
        m = re.search(r"(\d{3,4})p", preset)
        cap = int(m.group(1)) if m else 99999
        # 同等画质优先 https 直链(比 HLS 更稳定)，再按码率
        ok = [f for f in self.videos if (f.get("height") or 0) <= cap] or self.videos
        top_h = ok[0].get("height") or 0
        same = [f for f in ok if (f.get("height") or 0) == top_h]
        best = max(same, key=lambda f: (str(f.get("protocol", "")).startswith("http"), f.get("fps") or 0,
                                        f.get("tbr") or 0))
        return best["format_id"]

    def _selected_video(self):
        sel = self.vtree.selection()
        vid = sel[0] if sel else "__none__"
        return None if vid == "__none__" else self.fmt_by_id.get(vid)

    # ---------- 音轨 ----------
    def _build_audio(self, grid):
        card, c = self.app._card(grid, "音轨", "点击勾选 · 可多选，多音轨合并进同一文件")
        card.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 6))
        bar = ctk.CTkFrame(c, fg_color="transparent")
        bar.pack(fill=tk.X, pady=(0, 6))
        self.app._label(bar, "音频编码").pack(side=tk.LEFT)
        cu = self.task.get("custom") or {}
        self.acodec_var = tk.StringVar(value=cu.get("acodec_pref", "自动"))
        seg = self.app._segment(bar, self.acodec_var, ["自动", "AAC", "Opus"])
        seg.configure(command=lambda v: (self._fill_audio(), self._update_summary()))
        seg.pack(side=tk.LEFT, padx=(10, 0))
        self.app._btn(bar, "仅原声", self._audio_only_orig, height=28, width=64,
                      font=self.app.f_small).pack(side=tk.RIGHT)
        self.app._btn(bar, "全部", self._audio_all, height=28, width=52,
                      font=self.app.f_small).pack(side=tk.RIGHT, padx=6)
        cols = ("chk", "name", "code", "tag", "codec", "rate", "size")
        heads = ("☑", "语言", "代码", "类型", "编码", "码率", "大小")
        widths = (34, 150, 70, 64, 56, 60, 80)
        self.atree = self._tree(c, cols, heads, widths, select="none", stretch=("name",))
        self.atree.bind("<Button-1>", self._on_audio_click)
        # 按语言分组
        self.audio_groups = {}
        for f in self.audios:
            self.audio_groups.setdefault(f.get("language") or "und", []).append(f)
        self.orig_langs = [lang for lang, fs in self.audio_groups.items()
                           if any((f.get("language_preference") or 0) >= 10 or "original" in str(f.get("format_note"))
                                  for f in fs)]
        if cu.get("mode") == "exact":
            self.audio_checked = [lang for lang in cu.get("audio_langs", []) if lang in self.audio_groups]
        if not self.audio_checked and self.audio_groups:
            self.audio_checked = self.orig_langs[:1] or [self._lang_order()[0]]
        self._fill_audio()

    def _lang_order(self):
        return sorted(self.audio_groups, key=lambda lang: (lang not in self.orig_langs, lang_name(lang)))

    def _acodec_pref(self):
        v = self.acodec_var.get()
        if v == "自动":
            return "AAC" if self._container() == "mp4" else "OPUS"
        return "OPUS" if v == "Opus" else "AAC"

    def _best_audio(self, lang):
        """某语言下选最佳格式：优先所选编码 → 非 DRC(动态范围压缩) → 码率最高"""
        pref = self._acodec_pref()
        return max(self.audio_groups[lang], key=lambda f: (
            acodec_family(f.get("acodec")) == pref,
            "drc" not in f"{f.get('format_id')} {f.get('format_note')}".lower(),
            f.get("abr") or f.get("tbr") or 0))

    def _fill_audio(self):
        top = self.atree.yview()[0]
        self.win.after_idle(lambda: self.atree.yview_moveto(top))
        self.atree.delete(*self.atree.get_children())
        multi = len(self.audio_groups) > 1
        for lang in self._lang_order():
            f = self._best_audio(lang)
            size, exact = est_size(f, self.duration)
            note = re.sub(r",\s*(ultralow|low|medium|high)$", "", str(f.get("format_note") or ""))
            name = lang_name(lang) if lang != "und" else (note or "默认音轨")
            tag = "★ 原声" if lang in self.orig_langs else ("配音" if multi else "")
            on = lang in self.audio_checked
            order = f" {self.audio_checked.index(lang) + 1}" if on and len(self.audio_checked) > 1 else ""
            self.atree.insert("", tk.END, iid=lang, tags=("on" if on else "off",), values=(
                ("☑" + order) if on else "☐", name, lang, tag, acodec_family(f.get("acodec")),
                f"{int(f.get('abr') or f.get('tbr') or 0)}k", ("" if exact else "≈") + fmt_size(size)))

    def _on_audio_click(self, event):
        lang = self.atree.identify_row(event.y)
        if not lang:
            return "break"
        if lang in self.audio_checked:
            self.audio_checked.remove(lang)
        else:
            self.audio_checked.append(lang)
        self._fill_audio()
        self._update_summary()
        return "break"

    def _audio_all(self):
        self.audio_checked = self._lang_order()
        self._fill_audio()
        self._update_summary()

    def _audio_only_orig(self):
        self.audio_checked = self.orig_langs[:1] or self._lang_order()[:1]
        self._fill_audio()
        self._update_summary()

    def _selected_audios(self):
        return [self._best_audio(lang) for lang in self.audio_checked if lang in self.audio_groups]

    # ---------- 在线字幕 ----------
    def _build_subs(self, grid):
        card, c = self.app._card(grid, "视频源字幕", "只列出该视频实际存在的字幕 · 点击勾选")
        card.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(6, 0))
        bar = ctk.CTkFrame(c, fg_color="transparent")
        bar.pack(fill=tk.X, pady=(0, 6))
        # 不绑定 textvariable，否则 CTkEntry 不显示占位提示
        self.sub_filter = ctk.CTkEntry(bar, height=34, corner_radius=10, font=self.app.f_body, width=220,
                                       fg_color=C["input"], border_color=C["border"], text_color=C["fg"],
                                       placeholder_text="🔍 搜索语言 / 代码，如 zh、英语")
        self.sub_filter.pack(side=tk.LEFT)
        self.sub_filter.bind("<KeyRelease>", lambda e: self._fill_subs())
        self.show_trans = tk.BooleanVar(value=False)
        sw = self.app._switch(bar, "显示自动翻译", self.show_trans)
        sw.configure(command=self._fill_subs)
        sw.pack(side=tk.LEFT, padx=12)
        self.app._btn(bar, "清空", lambda: (self.sub_checked.clear(), self._fill_subs(), self._update_summary()),
                      height=28, width=52, font=self.app.f_small).pack(side=tk.RIGHT)
        cols = ("chk", "kind", "code", "name", "exts")
        heads = ("☑", "类型", "代码", "语言", "可用格式")
        widths = (34, 90, 90, 190, 110)
        self.stree = self._tree(c, cols, heads, widths, select="none", stretch=("name",))
        self.stree.bind("<Button-1>", self._on_sub_click)
        opt = ctk.CTkFrame(c, fg_color="transparent")
        opt.pack(fill=tk.X, pady=(8, 0))
        cu = self.task.get("custom") or {}
        self.embed_var = tk.BooleanVar(value=cu.get("embed", self.app.embed_sub_var.get()))
        self.keep_var = tk.BooleanVar(value=cu.get("keep_subs", True))
        self.app._switch(opt, "内嵌到视频", self.embed_var).pack(side=tk.LEFT)
        self.app._switch(opt, "同时保留字幕文件", self.keep_var).pack(side=tk.LEFT, padx=16)
        self._init_sub_checked(cu)
        self._fill_subs()

    def _init_sub_checked(self, cu):
        if cu.get("mode") == "exact":
            for code, is_auto in cu.get("subs", []):
                key = f"{'a' if is_auto else 'm'}:{code}"
                if (self.auto_subs if is_auto else self.manual_subs).get(code):
                    self.sub_checked.add(key)
            return
        if not self.app.sub_var.get():
            return
        pats = [p.strip() for p in self.app.sub_lang_var.get().split(",") if p.strip()]

        def match(code):
            for p in pats:
                try:
                    if p == "all" or re.fullmatch(p, code):
                        return True
                except re.error:
                    if p == code:
                        return True
            return False
        for code in self.manual_subs:
            if match(code):
                self.sub_checked.add(f"m:{code}")
        if self.app.auto_sub_var.get():
            for code in self.auto_subs:
                if match(code) and code not in self.manual_subs:
                    self.sub_checked.add(f"a:{code}")

    def _fill_subs(self):
        self.stree.delete(*self.stree.get_children())
        kw = self.sub_filter.get().strip().lower() if hasattr(self, "sub_filter") else ""
        orig_bases = {c[:-5] for c in self.auto_subs if c.endswith("-orig")}
        rows = []
        for code, tracks in self.manual_subs.items():
            rows.append((0, f"m:{code}", "人工字幕", code, tracks))
        for code, tracks in self.auto_subs.items():
            is_orig = code.endswith("-orig") or code in orig_bases
            rows.append((1 if is_orig else 2, f"a:{code}", "自动·原声" if is_orig else "自动翻译", code, tracks))
        rows.sort(key=lambda r: (r[0], r[3].lower()))
        top = self.stree.yview()[0]
        shown = 0
        for rank, key, kind, code, tracks in rows:
            name = tracks[0].get("name") or lang_name(code.replace("-orig", ""))
            if kw and kw not in code.lower() and kw not in name.lower() and kw not in lang_name(code).lower():
                continue
            if rank == 2 and not (self.show_trans.get() or kw or key in self.sub_checked):
                continue
            on = key in self.sub_checked
            exts = [t.get("ext") for t in tracks if t.get("ext")]
            common = [e for e in ("srt", "vtt", "ass", "ttml") if e in exts]
            exts = " ".join(common or exts[:3])
            self.stree.insert("", tk.END, iid=key, tags=("on" if on else "off",),
                              values=("☑" if on else "☐", kind, code, f"{lang_name(code.replace('-orig', ''))} · {name}"
                                      if lang_name(code) != name else name, exts))
            shown += 1
        if not shown:
            tip = "该视频没有字幕" if not rows else "没有匹配的字幕（可打开「显示自动翻译」）"
            self.stree.insert("", tk.END, iid="__empty__", tags=("muted",), values=("", "", "", tip, ""))
        self.stree.yview_moveto(top)

    def _on_sub_click(self, event):
        key = self.stree.identify_row(event.y)
        if not key or key == "__empty__":
            return "break"
        self.sub_checked.symmetric_difference_update({key})
        self._fill_subs()
        self._update_summary()
        return "break"

    def _selected_subs(self):
        return [(k[2:], k.startswith("a:")) for k in sorted(self.sub_checked)]

    # ---------- 本地字幕 ----------
    def _build_local(self, grid):
        card, c = self.app._card(grid, "自定义字幕文件", "下载完成后用 ffmpeg 无损内嵌")
        card.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=(6, 0))
        bar = ctk.CTkFrame(c, fg_color="transparent")
        bar.pack(fill=tk.X, pady=(0, 6))
        self.app._btn(bar, "＋ 添加字幕文件", self._add_local, "primary", height=30, width=130).pack(side=tk.LEFT)
        self.app._btn(bar, "✎ 语言/标题", self._edit_local, height=30, width=96).pack(side=tk.LEFT, padx=6)
        self.app._btn(bar, "↑", lambda: self._move_local(-1), height=30, width=34).pack(side=tk.LEFT)
        self.app._btn(bar, "↓", lambda: self._move_local(1), height=30, width=34).pack(side=tk.LEFT, padx=6)
        self.app._btn(bar, "✕ 移除", self._remove_local, "danger", height=30, width=70).pack(side=tk.RIGHT)
        self.app._label(c, "支持 srt / ass / ssa / vtt；文件名如 xxx.zh-Hans.srt 自动识别语言，GBK 编码自动处理。"
                           "\n本地字幕排在最前并设为默认字幕轨；仅音频模式下不内嵌。", muted=True, justify="left").pack(
            side=tk.BOTTOM, anchor="w", pady=(6, 0))
        cols = ("file", "lang", "title")
        heads = ("文件", "语言", "轨道标题")
        widths = (240, 80, 130)
        self.ltree = self._tree(c, cols, heads, widths, select="browse", stretch=("file",))
        self.ltree.bind("<Double-1>", lambda e: self._edit_local())
        cu = self.task.get("custom") or {}
        self.local_subs = [list(x) for x in cu.get("local_subs", [])]
        self._fill_local()

    def _fill_local(self, select=None):
        self.ltree.delete(*self.ltree.get_children())
        for i, (path, lang, title) in enumerate(self.local_subs):
            self.ltree.insert("", tk.END, iid=str(i), tags=("off",),
                              values=(os.path.basename(path), lang, title or lang_name(lang)))
        if not self.local_subs:
            self.ltree.insert("", tk.END, iid="__empty__", tags=("muted",),
                              values=("（未添加，点击「＋ 添加字幕文件」）", "", ""))
        elif select is not None and 0 <= select < len(self.local_subs):
            self.ltree.selection_set(str(select))

    def _add_local(self):
        paths = filedialog.askopenfilenames(parent=self.win, title="选择字幕文件",
                                            filetypes=[("字幕文件", "*.srt *.ass *.ssa *.vtt"), ("所有文件", "*.*")])
        for p in paths:
            lang = guess_sub_lang(p)
            self.local_subs.append([p, lang, f"{lang_name(lang)} (自定义)"])
        self._fill_local()
        self._update_summary()

    def _local_index(self):
        sel = [s for s in self.ltree.selection() if s != "__empty__"]
        return int(sel[0]) if sel else None

    def _edit_local(self):
        i = self._local_index()
        if i is None:
            return
        path, lang, title = self.local_subs[i]
        dlg = ctk.CTkInputDialog(title="字幕语言 / 标题",
                                 text=f"{os.path.basename(path)}\n\n格式：语言码|轨道标题\n例如  zh-Hans|中文特效字幕  或  en")
        dlg.after(100, lambda: dlg._entry.insert(0, f"{lang}|{title}"))
        value = dlg.get_input()
        self._grab()
        if not value:
            return
        new_lang, _, new_title = value.partition("|")
        new_lang = new_lang.strip() or "und"
        self.local_subs[i] = [path, new_lang, new_title.strip() or lang_name(new_lang)]
        self._fill_local(i)

    def _move_local(self, step):
        i = self._local_index()
        j = None if i is None else i + step
        if j is None or not 0 <= j < len(self.local_subs):
            return
        self.local_subs[i], self.local_subs[j] = self.local_subs[j], self.local_subs[i]
        self._fill_local(j)

    def _remove_local(self):
        i = self._local_index()
        if i is not None:
            self.local_subs.pop(i)
            self._fill_local()
            self._update_summary()

    # ---------- 汇总 / 应用 ----------
    def _effective_container(self, video, audios):
        c = self._container()
        if c != "webm" or not video:
            return c
        vfam = vcodec_family(video.get("vcodec"))
        afams = {acodec_family(a.get("acodec")) for a in audios}
        if vfam not in ("VP9", "AV1") or not afams <= {"OPUS", "VORBIS"}:
            return "mkv"
        return c

    def _update_summary(self):
        video, audios = self._selected_video(), self._selected_audios()
        vsize = est_size(video, self.duration)[0] or 0 if video else 0
        asize = sum(est_size(a, self.duration)[0] or 0 for a in audios)
        exact = (not video or est_size(video, self.duration)[1]) and all(est_size(a, self.duration)[1] for a in audios)
        n_sub = len(self.sub_checked) + len(self.local_subs)
        self.size_lbl.configure(text=f"预计大小 {'' if exact else '≈ '}{fmt_size(vsize + asize)}"
                                     f"    画面 {fmt_size(vsize)}  +  {len(audios)} 条音轨 {fmt_size(asize)}"
                                     f"    ·  {n_sub} 条字幕")
        hints = []
        if not video:
            conv = QUALITY_PRESETS[self.app.quality_var.get()][1]
            hints.append(f"仅音频：输出 {conv.upper() if conv else '原始格式 (m4a / webm)'}，只取第一条勾选的音轨")
        else:
            eff = self._effective_container(video, audios)
            hints.append(f"输出容器 {eff}" + ("（webm 不支持所选编码，自动改用 mkv）" if eff != self._container() else ""))
            if len(audios) > 1:
                hints.append(f"{len(audios)} 条音轨合并为多音轨文件，按勾选顺序排列，第 1 条为默认"
                             + ("；mp4 多音轨部分播放器需手动切换，推荐 mkv" if eff == "mp4" else ""))
            if not audios and video.get("acodec") in (None, "none"):
                hints.append("⚠ 未勾选音轨，将下载无声视频")
        self.hint_lbl.configure(text="  ·  ".join(hints), text_color=C["warn"] if "⚠" in hints[-1] else C["muted"])

    def _make_custom(self):
        video, audios = self._selected_video(), self._selected_audios()
        langs = [lang for lang in self.audio_checked if lang in self.audio_groups]
        if not video and not audios:
            messagebox.showwarning("提示", "仅音频模式请至少勾选一条音轨", parent=self.win)
            return None
        if not video and len(audios) > 1:
            audios, langs = audios[:1], langs[:1]
        if video and not audios and video.get("acodec") in (None, "none"):
            if not messagebox.askyesno("确认", "没有勾选任何音轨，确定下载无声视频吗？", parent=self.win):
                return None
        ids = ([video["format_id"]] if video else []) + [a["format_id"] for a in audios]
        n_audio = len(audios) + (1 if video and video.get("acodec") not in (None, "none") else 0)
        subs = self._selected_subs()
        container = self._effective_container(video, audios) if video else None
        size = (est_size(video, self.duration)[0] or 0 if video else 0) + sum(
            est_size(a, self.duration)[0] or 0 for a in audios)
        vfam = vcodec_family(video.get("vcodec")) if video else None
        height = video.get("height") if video else None
        head = f"{height}p {vfam}" if video else "仅音频"
        aud = f"{len(audios)}音轨" if len(audios) > 1 else (lang_name(langs[0]) if langs else "默认音")
        n_sub = len(subs) + len(self.local_subs)
        label = f"{head} · {aud}" + (f" · {n_sub}字幕" if n_sub else "")
        common = dict(audio_only=not video, subs=subs, embed=self.embed_var.get(), keep_subs=self.keep_var.get(),
                      container=container, acodec_pref=self.acodec_var.get())
        rule = dict(common, mode="rule", selector=build_rule_selector(height, vfam, langs, self._acodec_pref(), not video),
                    multi_audio=len(langs) > 1, local_subs=[], size=None, label="规则 " + label.replace(
                        f" · {n_sub}字幕", f" · {len(subs)}字幕" if subs else ""))
        return dict(common, mode="exact", video=video["format_id"] if video else None, audio_langs=langs,
                    selector="+".join(ids), multi_audio=n_audio > 1,
                    local_subs=[tuple(x) for x in self.local_subs], size=size, label=label, rule=rule)

    def _apply_one(self):
        cu = self._make_custom()
        if cu:
            self.app._apply_custom(self.iid, cu)
            self.win.destroy()

    def _apply_all(self):
        cu = self._make_custom()
        if not cu:
            return
        others = sum(1 for i, t in self.app.tasks.items() if t["checked"] and i != self.iid)
        if self.local_subs and others:
            messagebox.showinfo("提示", "本地字幕文件只对当前视频生效，其他视频按画质/音轨/在线字幕规则匹配",
                                parent=self.win)
        self.app._apply_custom(self.iid, cu, to_checked=True)
        self.win.destroy()


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
