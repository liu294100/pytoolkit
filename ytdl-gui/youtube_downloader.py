#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube 视频下载器 - 基于 tkinter + yt_dlp 的桌面应用
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
import time

try:
    import requests
    if requests is None:
        raise ImportError("requests module is None")
    HAS_REQUESTS = True
except ImportError:
    requests = None
    HAS_REQUESTS = False

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


class UserCancelledError(Exception):
    pass


class YouTubeDownloader:
    AUDIO_CODEC_MAP = {
        "mp3": "mp3",
        "flac": "flac",
        "wav": "wav",
        "aac": "aac",
        "opus": "opus",
        "vorbis": "vorbis",
    }

    AUDIO_CONVERT_PRESETS = [
        ("仅音频 MP3 (192k)", "mp3"),
        ("仅音频 AAC (192k)", "aac"),
        ("仅音频 FLAC", "flac"),
    ]

    class _YDLLogger:
        def __init__(self, owner, scene):
            self.owner = owner
            self.scene = scene

        def _emit(self, level, message):
            if message is None:
                return
            text = str(message).replace("\r", "").strip()
            if not text:
                return
            self.owner._append_log(f"[{self.scene}/{level}] {text}")

        def debug(self, msg):
            self._emit("debug", msg)

        def warning(self, msg):
            self._emit("warning", msg)

        def error(self, msg):
            self._emit("error", msg)

    def __init__(self, root=None):
        self.root = root
        self.download_path = self._get_default_download_path()
        self.proxy_settings = {"type": "http", "host": "127.0.0.1", "port": "7890"}
        self.video_info = None
        self.current_format_selection = None
        self.format_map = {}
        self.subtitle_map = {}
        self.audio_track_map = {}
        self._task_token = 0
        self._cancel_requested = False
        self._action = "idle"
        self._logs = []
        self._log_lock = threading.Lock()
        self._log_queue = Queue()
        self._log_window = None
        self._log_text = None
        self._log_auto_refresh_job = None
        self._last_progress_bucket = -1
        self._last_ui_update_time = 0.0
        self._last_ui_percent = -1.0
        self._log_has_content = False
        self._last_log_drop_notice_time = 0.0
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ytdl")
        if root:
            self._setup_ui()

    def _get_default_download_path(self):
        if os.name == "nt":
            drives = [f"{letter}:\\" for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{letter}:\\")]
            if drives:
                return sorted(drives)[-1]
        fallback = os.path.expanduser("~/Downloads")
        return fallback if os.path.exists(fallback) else os.path.expanduser("~")

    def _setup_ui(self):
        self.root.title("YouTube 视频下载器")
        self.root.geometry("920x700")
        self.root.minsize(760, 560)
        self.root.configure(bg="#f0f0f0")

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0", foreground="#333333", font=("Microsoft YaHei UI", 10))
        self.style.configure("Title.TLabel", background="#f0f0f0", foreground="#1a1a1a", font=("Microsoft YaHei UI", 16, "bold"))
        self.style.configure("Info.TLabel", background="#f0f0f0", foreground="#666666", font=("Microsoft YaHei UI", 9))
        self.style.configure("TButton", background="#4a90d9", foreground="#ffffff", padding=(12, 6), font=("Microsoft YaHei UI", 10))
        self.style.map("TButton", background=[("active", "#357abd"), ("disabled", "#cccccc")], foreground=[("disabled", "#888888")])
        self.style.configure("Accent.TButton", background="#27ae60", foreground="#ffffff", padding=(14, 8), font=("Microsoft YaHei UI", 11, "bold"))
        self.style.map("Accent.TButton", background=[("active", "#219a52"), ("disabled", "#cccccc")])
        self.style.configure("Warn.TButton", background="#c0392b", foreground="#ffffff", padding=(14, 8), font=("Microsoft YaHei UI", 10, "bold"))
        self.style.map("Warn.TButton", background=[("active", "#a93226"), ("disabled", "#cccccc")])
        self.style.configure("Horizontal.TProgressbar", background="#4a90d9", troughcolor="#e0e0e0")
        self.style.configure("TLabelframe", background="#f0f0f0", foreground="#333333", font=("Microsoft YaHei UI", 10, "bold"))
        self.style.configure("TLabelframe.Label", background="#f0f0f0", foreground="#4a90d9", font=("Microsoft YaHei UI", 10, "bold"))

        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="YouTube 视频下载器", style="Title.TLabel").pack(pady=(0, 10))

        url_frame = ttk.LabelFrame(main_frame, text="视频链接", padding=10)
        url_frame.pack(fill=tk.X, pady=(0, 8))

        url_row = ttk.Frame(url_frame)
        url_row.pack(fill=tk.X)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_row, textvariable=self.url_var)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.fetch_btn = ttk.Button(url_row, text="获取信息", command=self._on_fetch_click)
        self.fetch_btn.pack(side=tk.RIGHT)

        info_frame = ttk.LabelFrame(main_frame, text="视频信息", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 8))

        self.info_title_var = tk.StringVar(value="等待获取...")
        self.info_duration_var = tk.StringVar(value="")
        self.info_extra_var = tk.StringVar(value="")
        ttk.Label(info_frame, textvariable=self.info_title_var, wraplength=860).pack(anchor=tk.W)
        ttk.Label(info_frame, textvariable=self.info_duration_var, style="Info.TLabel").pack(anchor=tk.W, pady=(2, 0))
        ttk.Label(info_frame, textvariable=self.info_extra_var, style="Info.TLabel").pack(anchor=tk.W, pady=(2, 0))

        opts_frame = ttk.LabelFrame(main_frame, text="下载选项", padding=10)
        opts_frame.pack(fill=tk.X, pady=(0, 8))

        row1 = ttk.Frame(opts_frame)
        row1.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(row1, text="格式:").pack(side=tk.LEFT, padx=(0, 5))
        self.format_var = tk.StringVar(value="")
        self.format_combo = ttk.Combobox(row1, textvariable=self.format_var, state="readonly", width=50)
        self.format_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.format_combo.bind("<<ComboboxSelected>>", self._on_format_selected)
        self.playlist_var = tk.BooleanVar(value=False)
        self.playlist_check = tk.Checkbutton(
            row1,
            text="合集下载",
            variable=self.playlist_var,
            bg="#f0f0f0",
            activebackground="#f0f0f0",
            font=("Microsoft YaHei UI", 10),
            relief=tk.FLAT,
            anchor="w",
        )
        self.playlist_check.pack(side=tk.LEFT)

        row2 = ttk.Frame(opts_frame)
        row2.pack(fill=tk.X, pady=(0, 8))
        self.subtitle_enabled_var = tk.BooleanVar(value=False)
        self.subtitle_check = tk.Checkbutton(
            row2,
            text="下载字幕",
            variable=self.subtitle_enabled_var,
            command=self._toggle_subtitle_widgets,
            bg="#f0f0f0",
            activebackground="#f0f0f0",
            font=("Microsoft YaHei UI", 10),
            relief=tk.FLAT,
            anchor="w",
        )
        self.subtitle_check.pack(side=tk.LEFT, padx=(0, 8))
        self.subtitle_var = tk.StringVar(value="")
        self.subtitle_combo = ttk.Combobox(row2, textvariable=self.subtitle_var, state="disabled", width=35)
        self.subtitle_combo.pack(side=tk.LEFT, padx=(0, 15))

        row3 = ttk.Frame(opts_frame)
        row3.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(row3, text="音轨:").pack(side=tk.LEFT, padx=(0, 5))
        self.audio_track_var = tk.StringVar(value="自动选择")
        self.audio_track_combo = ttk.Combobox(row3, textvariable=self.audio_track_var, state="readonly", width=35)
        self.audio_track_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.audio_track_combo["values"] = ["自动选择"]

        ttk.Label(row3, text="保存到:").pack(side=tk.LEFT, padx=(0, 5))
        self.path_var = tk.StringVar(value=self.download_path)
        self.path_entry = ttk.Entry(row3, textvariable=self.path_var)
        self.path_entry.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        self.browse_btn = ttk.Button(row3, text="浏览", command=self._on_browse_click)
        self.browse_btn.pack(side=tk.LEFT)

        proxy_frame = ttk.LabelFrame(main_frame, text="代理设置（可选）", padding=10)
        proxy_frame.pack(fill=tk.X, pady=(0, 8))

        proxy_row = ttk.Frame(proxy_frame)
        proxy_row.pack(fill=tk.X)
        ttk.Label(proxy_row, text="类型:").pack(side=tk.LEFT, padx=(0, 5))
        self.proxy_type_var = tk.StringVar(value="http")
        self.proxy_type_combo = ttk.Combobox(proxy_row, textvariable=self.proxy_type_var, values=["none", "http", "socks5"], state="readonly", width=8)
        self.proxy_type_combo.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(proxy_row, text="主机:").pack(side=tk.LEFT, padx=(0, 5))
        self.proxy_host_var = tk.StringVar(value="127.0.0.1")
        self.proxy_host_entry = ttk.Entry(proxy_row, textvariable=self.proxy_host_var, width=18)
        self.proxy_host_entry.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(proxy_row, text="端口:").pack(side=tk.LEFT, padx=(0, 5))
        self.proxy_port_var = tk.StringVar(value="7890")
        self.proxy_port_entry = ttk.Entry(proxy_row, textvariable=self.proxy_port_var, width=8)
        self.proxy_port_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.proxy_test_btn = ttk.Button(proxy_row, text="测试连接", command=self._on_test_proxy_click)
        self.proxy_test_btn.pack(side=tk.LEFT)

        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 8))
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, style="Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, pady=(0, 4))
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(progress_frame, textvariable=self.status_var, style="Info.TLabel").pack(anchor=tk.W)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=(5, 0))
        self.download_btn = ttk.Button(btn_frame, text="开始下载", style="Accent.TButton", command=self._on_download_click)
        self.download_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.cancel_btn = ttk.Button(btn_frame, text="取消当前任务", style="Warn.TButton", command=self._on_cancel_click, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT)
        self.log_btn = ttk.Button(btn_frame, text="查看日志", command=self._on_show_log_click)
        self.log_btn.pack(side=tk.LEFT, padx=(8, 0))

    def _append_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        with self._log_lock:
            self._logs.append(line)
            if len(self._logs) > 1200:
                self._logs = self._logs[-1200:]
        if self._log_queue.qsize() >= 2000:
            now = time.time()
            if now - self._last_log_drop_notice_time > 3:
                self._last_log_drop_notice_time = now
                dropped = f"[{timestamp}] 日志过多，已跳过部分输出以保持界面流畅"
                self._log_queue.put(dropped)
            return
        self._log_queue.put(line)

    def _get_log_text(self):
        with self._log_lock:
            return "\n".join(self._logs)

    def _on_show_log_click(self):
        if self._log_window and self._log_window.winfo_exists():
            self._log_window.lift()
            self._refresh_log_window(full=True)
            return
        self._log_window = tk.Toplevel(self.root)
        self._log_window.title("yt-dlp 运行日志")
        self._log_window.geometry("900x460")
        self._log_window.minsize(680, 360)
        container = ttk.Frame(self._log_window, padding=10)
        container.pack(fill=tk.BOTH, expand=True)
        top_row = ttk.Frame(container)
        top_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(top_row, text="命令与响应日志").pack(side=tk.LEFT)
        ttk.Button(top_row, text="刷新", command=self._refresh_log_window).pack(side=tk.RIGHT)
        ttk.Button(top_row, text="清空", command=self._clear_logs).pack(side=tk.RIGHT, padx=(0, 6))
        text_frame = ttk.Frame(container)
        text_frame.pack(fill=tk.BOTH, expand=True)
        y_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL)
        self._log_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            yscrollcommand=y_scroll.set,
            background="#ffffff",
            foreground="#1e1e1e",
        )
        y_scroll.config(command=self._log_text.yview)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._log_window.protocol("WM_DELETE_WINDOW", self._on_log_window_close)
        self._refresh_log_window(full=True)
        self._schedule_log_auto_refresh()

    def _append_log_to_widget(self, line):
        if not self._log_text:
            return
        self._log_text.config(state=tk.NORMAL)
        if not self._log_has_content:
            self._log_text.delete("1.0", tk.END)
            self._log_text.insert(tk.END, line)
            self._log_has_content = True
        else:
            self._log_text.insert(tk.END, f"\n{line}")
        line_count = int(self._log_text.index("end-1c").split(".")[0])
        if line_count > 1600:
            self._log_text.delete("1.0", f"{line_count - 1200}.0")
        self._log_text.see(tk.END)
        self._log_text.config(state=tk.DISABLED)

    def _refresh_log_window(self, full=False):
        if not self._log_window or not self._log_window.winfo_exists() or not self._log_text:
            return
        if full:
            self._log_text.config(state=tk.NORMAL)
            self._log_text.delete("1.0", tk.END)
            text = self._get_log_text()
            if text:
                self._log_text.insert(tk.END, text)
                self._log_has_content = True
            else:
                self._log_text.insert(tk.END, "暂无日志")
                self._log_has_content = False
            self._log_text.see(tk.END)
            self._log_text.config(state=tk.DISABLED)
            while True:
                try:
                    self._log_queue.get_nowait()
                except Empty:
                    break
            return
        updated_lines = []
        max_batch = 80
        while True:
            if len(updated_lines) >= max_batch:
                break
            try:
                updated_lines.append(self._log_queue.get_nowait())
            except Empty:
                break
        if not updated_lines:
            return
        self._log_text.config(state=tk.NORMAL)
        current = self._log_text.get("1.0", "end-1c")
        if not self._log_has_content and current == "暂无日志":
            self._log_text.delete("1.0", tk.END)
            self._log_has_content = True
        prefix = "" if not self._log_has_content else "\n"
        self._log_text.insert(tk.END, prefix + "\n".join(updated_lines))
        self._log_has_content = True
        line_count = int(self._log_text.index("end-1c").split(".")[0])
        if line_count > 2000:
            self._log_text.delete("1.0", f"{line_count - 1200}.0")
        self._log_text.see(tk.END)
        self._log_text.config(state=tk.DISABLED)

    def _clear_logs(self):
        with self._log_lock:
            self._logs.clear()
        while True:
            try:
                self._log_queue.get_nowait()
            except Empty:
                break
        self._log_has_content = False
        self._refresh_log_window(full=True)

    def _schedule_log_auto_refresh(self):
        if not self._log_window or not self._log_window.winfo_exists():
            return
        self._refresh_log_window()
        self._log_auto_refresh_job = self.root.after(200, self._schedule_log_auto_refresh)

    def _on_log_window_close(self):
        if self._log_auto_refresh_job:
            self.root.after_cancel(self._log_auto_refresh_job)
            self._log_auto_refresh_job = None
        if self._log_window and self._log_window.winfo_exists():
            self._log_window.destroy()
        self._log_window = None
        self._log_text = None

    def _build_ydl_command_preview(self, ydl_opts, url):
        parts = ["yt-dlp"]
        if ydl_opts.get("proxy"):
            parts.extend(["--proxy", ydl_opts["proxy"]])
        if ydl_opts.get("noplaylist"):
            parts.append("--no-playlist")
        fmt = ydl_opts.get("format")
        if fmt:
            parts.extend(["-f", f'"{fmt}"'])
        if ydl_opts.get("writesubtitles"):
            parts.append("--write-subs")
        if ydl_opts.get("writeautomaticsub"):
            parts.append("--write-auto-subs")
        sub_langs = ydl_opts.get("subtitleslangs")
        if sub_langs:
            parts.extend(["--sub-langs", ",".join(sub_langs)])
        output = ydl_opts.get("outtmpl")
        if output:
            parts.extend(["-o", f'"{output}"'])
        parts.append(f'"{url}"')
        return " ".join(parts)

    def _toggle_subtitle_widgets(self):
        enabled = self.subtitle_enabled_var.get()
        state = "readonly" if enabled and self.subtitle_map else "disabled"
        self.subtitle_combo.config(state=state)
        if not enabled:
            self.subtitle_var.set("")

    def _set_action_state(self, action):
        self._action = action
        busy = action in {"fetching", "downloading"}
        normal_or_disabled = tk.DISABLED if busy else tk.NORMAL
        for widget in [self.fetch_btn, self.download_btn, self.browse_btn, self.proxy_test_btn]:
            widget.config(state=normal_or_disabled)
        self.cancel_btn.config(state=tk.NORMAL if busy else tk.DISABLED)
        self.url_entry.config(state="readonly" if busy else "normal")
        self.path_entry.config(state="readonly" if busy else "normal")
        self.format_combo.config(state="disabled" if busy else "readonly")
        self.audio_track_combo.config(state="disabled" if busy else "readonly")
        self.playlist_check.config(state=tk.DISABLED if busy else tk.NORMAL)
        self.subtitle_check.config(state=tk.DISABLED if busy else tk.NORMAL)
        subtitle_state = "readonly" if (not busy and self.subtitle_enabled_var.get() and self.subtitle_map) else "disabled"
        self.subtitle_combo.config(state=subtitle_state)

    def _next_task_token(self):
        self._task_token += 1
        return self._task_token

    def _sync_proxy_settings(self):
        ptype = self.proxy_type_var.get()
        self.proxy_settings = {
            "type": ptype,
            "host": self.proxy_host_var.get().strip(),
            "port": self.proxy_port_var.get().strip(),
        }

    def _on_fetch_click(self):
        url = self.url_var.get().strip()
        if not self.validate_url(url):
            messagebox.showwarning("提示", "请输入有效的 YouTube 链接")
            return
        self._sync_proxy_settings()
        self._cancel_requested = False
        token = self._next_task_token()
        self._append_log(f"开始获取信息，链接: {url}")
        self._set_action_state("fetching")
        self.info_title_var.set("正在获取...")
        self.info_duration_var.set("")
        self.info_extra_var.set("")
        self.status_var.set("正在获取视频信息...")
        self.fetch_info_threaded(
            url=url,
            playlist_mode=self.playlist_var.get(),
            token=token,
            on_success=self._on_fetch_success,
            on_error=self._on_fetch_error,
        )

    def _on_fetch_success(self, normalized):
        self.video_info = normalized
        active_info = normalized.get("active", {})
        title = active_info.get("title", "未知标题")
        duration = active_info.get("duration")
        self.info_title_var.set(title)
        self.info_duration_var.set(self._format_duration(duration))
        if normalized.get("is_playlist"):
            pl_title = normalized.get("playlist_title") or "未知合集"
            self.info_extra_var.set(f"合集: {pl_title} | 共 {normalized.get('entry_count', 0)} 条")
        else:
            uploader = active_info.get("uploader") or "未知作者"
            self.info_extra_var.set(f"作者: {uploader}")
        self._populate_format_options(active_info)
        self._populate_audio_track_options(active_info)
        self._populate_subtitle_options(active_info)
        self.status_var.set("获取完成，请选择格式后下载")

    def _on_fetch_error(self, error):
        self._append_log(f"获取信息失败: {error}")
        self.info_title_var.set("获取失败")
        self.info_duration_var.set("")
        self.info_extra_var.set("")
        self.status_var.set("就绪")
        messagebox.showerror("错误", f"获取视频信息失败：{error}")

    def _on_format_selected(self, event=None):
        selected = self.format_var.get()
        if selected in self.format_map:
            self.current_format_selection = selected

    def _on_browse_click(self):
        current = self.path_var.get().strip() or self.download_path
        path = filedialog.askdirectory(initialdir=current)
        if path:
            self.download_path = path
            self.path_var.set(path)

    def _on_test_proxy_click(self):
        host = self.proxy_host_var.get().strip()
        port = self.proxy_port_var.get().strip()
        ptype = self.proxy_type_var.get()
        if ptype == "none" or not host or not port:
            messagebox.showinfo("提示", "请先填写代理信息")
            return
        self.proxy_settings = {"type": ptype, "host": host, "port": port}
        self.status_var.set("正在测试代理...")
        self.proxy_test_btn.config(state=tk.DISABLED)

        def _test():
            return self.test_proxy(host, port, ptype)

        future = self._executor.submit(_test)
        future.add_done_callback(lambda f: self.root.after(0, lambda: self._on_proxy_test_done(bool(f.result()))))

    def _on_proxy_test_done(self, ok):
        self.proxy_test_btn.config(state=tk.NORMAL)
        self.status_var.set("就绪")
        if ok:
            messagebox.showinfo("成功", "代理连接正常")
        else:
            messagebox.showwarning("失败", "代理连接失败，请检查设置")

    def _on_cancel_click(self):
        if self._action in {"fetching", "downloading"}:
            self._cancel_requested = True
            self._append_log(f"收到取消请求，当前任务: {self._action}")
            self.status_var.set("正在取消，请稍候...")
            self.cancel_btn.config(state=tk.DISABLED)

    def _on_download_click(self):
        url = self.url_var.get().strip()
        if not self.validate_url(url):
            messagebox.showwarning("提示", "请输入有效的 YouTube 链接")
            return
        if not self.current_format_selection or self.current_format_selection not in self.format_map:
            messagebox.showwarning("提示", "请先获取信息并选择下载格式")
            return

        selected_path = self.path_var.get().strip()
        if not selected_path:
            messagebox.showwarning("提示", "请选择保存路径")
            return
        try:
            os.makedirs(selected_path, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("错误", f"保存路径不可用：{exc}")
            return

        subtitle_choice = self.subtitle_var.get().strip()
        subtitle_config = None
        if self.subtitle_enabled_var.get():
            if not subtitle_choice or subtitle_choice not in self.subtitle_map:
                messagebox.showwarning("提示", "已启用字幕下载，请选择字幕语言")
                return
            subtitle_config = self.subtitle_map[subtitle_choice]

        self.download_path = selected_path
        self._sync_proxy_settings()
        self._cancel_requested = False
        token = self._next_task_token()
        self.progress_var.set(0)
        self._last_progress_bucket = -1
        self._last_ui_update_time = 0.0
        self._last_ui_percent = -1.0
        selected_audio_track = self.audio_track_var.get().strip()
        self._append_log(
            f"开始下载，格式: {self.current_format_selection}，音轨: {selected_audio_track or '自动选择'}，合集下载: {'是' if self.playlist_var.get() else '否'}，字幕: {subtitle_choice if subtitle_config else '关闭'}"
        )
        self.status_var.set("正在下载...")
        self._set_action_state("downloading")
        self.start_download_threaded(
            url=url,
            token=token,
            format_config=self.format_map[self.current_format_selection],
            audio_track_config=self.audio_track_map.get(selected_audio_track),
            playlist_mode=self.playlist_var.get(),
            subtitle_config=subtitle_config,
            on_success=self._on_download_success,
            on_error=self._on_download_error,
            on_cancel=self._on_download_cancelled,
        )

    def _on_download_success(self):
        self._append_log("下载完成")
        self.progress_var.set(100)
        self.status_var.set("下载完成")
        messagebox.showinfo("完成", "下载完成")

    def _on_download_error(self, error):
        self._append_log(f"下载失败: {error}")
        self.progress_var.set(0)
        self.status_var.set("下载失败")
        messagebox.showerror("错误", f"下载失败：{error}")

    def _on_download_cancelled(self):
        self._append_log("任务已取消")
        self.progress_var.set(0)
        self.status_var.set("已取消")
        messagebox.showinfo("提示", "任务已取消")

    def _format_duration(self, duration):
        if duration is None:
            return "时长: 未知"
        try:
            total = int(duration)
        except (TypeError, ValueError):
            return "时长: 未知"
        hours, remain = divmod(total, 3600)
        mins, secs = divmod(remain, 60)
        if hours:
            return f"时长: {hours}:{mins:02d}:{secs:02d}"
        return f"时长: {mins}:{secs:02d}"

    def _format_size(self, size_bytes):
        if size_bytes is None:
            return "未知"
        size = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}PB"

    def _format_speed(self, bytes_per_sec):
        if not bytes_per_sec:
            return "速度未知"
        return f"{self._format_size(bytes_per_sec)}/s"

    def _format_eta(self, seconds):
        if seconds is None:
            return "未知"
        try:
            value = int(seconds)
        except (TypeError, ValueError):
            return "未知"
        if value < 0:
            return "未知"
        hours, remain = divmod(value, 3600)
        mins, secs = divmod(remain, 60)
        if hours:
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    def _populate_format_options(self, info):
        self.format_map = {}
        options = []

        best_label = "最佳质量（自动）"
        self.format_map[best_label] = {
            "selector": "bestvideo*+bestaudio/best",
            "audio_codec": None,
            "kind": "video",
            "has_audio": False,
            "format_id": None,
        }
        options.append(best_label)

        formats = info.get("formats") or []
        video_formats = []
        for f in formats:
            if f.get("vcodec") == "none":
                continue
            if not f.get("format_id"):
                continue
            if f.get("height") is None:
                continue
            video_formats.append(f)

        video_formats.sort(key=lambda x: (x.get("height") or 0, x.get("fps") or 0, x.get("tbr") or 0), reverse=True)

        seen = set()
        for f in video_formats:
            key = (f.get("height"), f.get("ext"), f.get("fps"), f.get("vcodec"), f.get("acodec") != "none")
            if key in seen:
                continue
            seen.add(key)
            format_id = f.get("format_id")
            height = f.get("height")
            fps = f.get("fps") or 0
            ext = f.get("ext") or "未知"
            size = self._format_size(f.get("filesize") or f.get("filesize_approx"))
            has_audio = f.get("acodec") != "none"
            selector = format_id if has_audio else f"{format_id}+bestaudio/best"
            audio_text = "含音频" if has_audio else "视频+音频合并"
            label = f"{height}p | {ext} | {int(fps) if fps else '-'}fps | {audio_text} | {size}"
            self.format_map[label] = {
                "selector": selector,
                "audio_codec": None,
                "kind": "video",
                "has_audio": has_audio,
                "format_id": format_id,
            }
            options.append(label)
            if len(options) >= 13:
                break

        for label, codec in self.AUDIO_CONVERT_PRESETS:
            self.format_map[label] = {
                "selector": "bestaudio/best",
                "audio_codec": codec,
                "kind": "audio_only",
                "has_audio": True,
                "format_id": None,
            }
            options.append(label)

        self.format_combo["values"] = options
        if options:
            self.current_format_selection = options[0]
            self.format_var.set(options[0])
        else:
            self.current_format_selection = None
            self.format_var.set("")

    def _get_language_name(self, language_code):
        mapping = {
            "zh": "中文",
            "zh-cn": "中文(简体)",
            "zh-tw": "中文(繁体)",
            "en": "英语",
            "ja": "日语",
            "ko": "韩语",
            "fr": "法语",
            "de": "德语",
            "es": "西班牙语",
            "it": "意大利语",
            "pt": "葡萄牙语",
            "ru": "俄语",
        }
        key = str(language_code or "").strip().lower()
        return mapping.get(key, key or "未知")

    def _populate_audio_track_options(self, info):
        self.audio_track_map = {"自动选择": None}
        options = ["自动选择"]
        seen = set()
        formats = info.get("formats") or []
        for f in formats:
            if f.get("acodec") in (None, "none"):
                continue
            language = (f.get("language") or "").strip()
            acodec = f.get("acodec") or "未知编码"
            abr = f.get("abr")
            format_id = f.get("format_id")
            ext = f.get("ext") or "未知"
            if language:
                key = ("lang", language)
                if key in seen:
                    continue
                seen.add(key)
                name = self._get_language_name(language)
                label = f"{name} ({language}) | {acodec} | {ext}"
                self.audio_track_map[label] = {"mode": "language", "value": language}
                options.append(label)
            elif format_id:
                key = ("id", format_id)
                if key in seen:
                    continue
                seen.add(key)
                abr_text = f"{int(abr)}kbps" if abr else "未知码率"
                label = f"轨道ID:{format_id} | {acodec} | {abr_text} | {ext}"
                self.audio_track_map[label] = {"mode": "format_id", "value": format_id}
                options.append(label)
            if len(options) >= 16:
                break
        self.audio_track_combo["values"] = options
        self.audio_track_var.set(options[0])

    def _build_audio_selector(self, audio_track_config):
        if not audio_track_config:
            return "bestaudio/best"
        mode = audio_track_config.get("mode")
        value = audio_track_config.get("value")
        if mode == "language" and value:
            return f"bestaudio[language={value}]/bestaudio/best"
        if mode == "format_id" and value:
            return f"{value}/bestaudio/best"
        return "bestaudio/best"

    def _build_download_selector(self, format_config, audio_track_config):
        base_selector = format_config.get("selector", "bestvideo*+bestaudio/best")
        if not audio_track_config:
            return base_selector
        mode = audio_track_config.get("mode")
        value = audio_track_config.get("value")
        audio_selector = self._build_audio_selector(audio_track_config)
        if format_config.get("kind") == "audio_only":
            return audio_selector
        format_id = format_config.get("format_id")
        if format_id:
            if mode == "language" and value:
                return f"{format_id}+bestaudio[language={value}]/{format_id}+bestaudio/{base_selector}"
            if mode == "format_id" and value:
                return f"{format_id}+{value}/{base_selector}"
            return f"{format_id}+{audio_selector}/{base_selector}"
        return f"bestvideo*+{audio_selector}/{base_selector}"

    def _populate_subtitle_options(self, info):
        self.subtitle_map = {}
        options = []

        subtitles = info.get("subtitles") or {}
        for lang, tracks in subtitles.items():
            if tracks:
                label = f"{lang}（人工字幕）"
                self.subtitle_map[label] = {"lang": lang, "auto": False}
                options.append(label)

        automatic = info.get("automatic_captions") or {}
        for lang, tracks in automatic.items():
            if tracks and all(not k.startswith(f"{lang}（") for k in self.subtitle_map):
                label = f"{lang}（自动字幕）"
                self.subtitle_map[label] = {"lang": lang, "auto": True}
                options.append(label)

        self.subtitle_combo["values"] = options
        if options:
            self.subtitle_var.set(options[0])
        else:
            self.subtitle_var.set("")
            self.subtitle_enabled_var.set(False)
        self._toggle_subtitle_widgets()

    def test_proxy(self, proxy_host, proxy_port, proxy_type="http"):
        proxy_url = f"{proxy_type}://{proxy_host}:{proxy_port}"
        if HAS_REQUESTS:
            proxies = {"http": proxy_url, "https": proxy_url}
            try:
                response = requests.get("https://www.youtube.com", proxies=proxies, timeout=10)
                return response.status_code == 200
            except Exception:
                return False
        import urllib.request
        try:
            proxy_handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
            opener = urllib.request.build_opener(proxy_handler)
            response = opener.open("https://www.youtube.com", timeout=10)
            return response.status == 200
        except Exception:
            return False

    def validate_url(self, url):
        if not url:
            return False
        return "youtube.com" in url or "youtu.be" in url

    def _normalize_info(self, info):
        if info.get("_type") == "playlist":
            entries = [entry for entry in (info.get("entries") or []) if entry]
            active = entries[0] if entries else {}
            return {
                "is_playlist": True,
                "playlist_title": info.get("title"),
                "entry_count": len(entries),
                "active": active,
                "raw": info,
            }
        return {
            "is_playlist": False,
            "playlist_title": "",
            "entry_count": 1,
            "active": info,
            "raw": info,
        }

    def fetch_info(self, url, playlist_mode=False):
        if not yt_dlp:
            raise ImportError("yt_dlp 未安装")
        ydl_opts = {
            "noplaylist": not playlist_mode,
            "extract_flat": False,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 20,
            "logger": self._YDLLogger(self, "info"),
        }
        if not playlist_mode:
            ydl_opts["playlistend"] = 1
        if self.proxy_settings["type"] != "none":
            proxy = f"{self.proxy_settings['type']}://{self.proxy_settings['host']}:{self.proxy_settings['port']}"
            ydl_opts["proxy"] = proxy
        self._append_log(f"yt-dlp 命令(信息): {self._build_ydl_command_preview(ydl_opts, url)}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if info.get("_type") == "playlist":
            entries = [entry for entry in (info.get("entries") or []) if entry]
            self._append_log(f"获取信息成功: 合集 {len(entries)} 条")
        else:
            self._append_log(f"获取信息成功: 标题 {info.get('title', '未知')}")
        return self._normalize_info(info)

    def fetch_info_threaded(self, url, playlist_mode, token, on_success=None, on_error=None):
        def _worker():
            return self.fetch_info(url, playlist_mode=playlist_mode)

        future = self._executor.submit(_worker)

        def _on_done(f):
            try:
                info = f.result()
                self.root.after(0, lambda: self._on_fetch_complete(token, info, None, on_success, on_error))
            except Exception as exc:
                self.root.after(0, lambda err=exc: self._on_fetch_complete(token, None, err, on_success, on_error))

        future.add_done_callback(_on_done)
        return future

    def _on_fetch_complete(self, token, info, error, on_success, on_error):
        if token != self._task_token:
            return
        was_cancelled = self._cancel_requested
        self._cancel_requested = False
        self._set_action_state("idle")
        if was_cancelled:
            self.status_var.set("已取消")
            return
        if error:
            if on_error:
                on_error(error)
        elif on_success:
            on_success(info)

    def _make_progress_hook(self, token):
        def _hook(data):
            if token != self._task_token or self._cancel_requested:
                raise UserCancelledError("用户取消下载")
            status = data.get("status")
            if status == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
                downloaded = data.get("downloaded_bytes") or 0
                speed = data.get("speed")
                eta = data.get("eta")
                percent = 0.0
                if total > 0:
                    percent = max(0.0, min(100.0, downloaded * 100.0 / total))
                info = data.get("info_dict") or {}
                playlist_index = info.get("playlist_index")
                playlist_total = info.get("n_entries") or info.get("playlist_count") or info.get("playlist_size")
                try:
                    playlist_index = int(playlist_index) if playlist_index is not None else None
                except (TypeError, ValueError):
                    playlist_index = None
                try:
                    playlist_total = int(playlist_total) if playlist_total is not None else None
                except (TypeError, ValueError):
                    playlist_total = None

                ui_progress = percent
                prefix = ""
                if playlist_index and playlist_total:
                    overall = ((playlist_index - 1) + (percent / 100.0)) / max(playlist_total, 1) * 100.0
                    ui_progress = max(0.0, min(100.0, overall))
                    prefix = f"[{playlist_index}/{playlist_total}] "
                elif playlist_index:
                    prefix = f"[第{playlist_index}条] "

                total_text = self._format_size(total) if total > 0 else "未知"
                status_text = (
                    f"{prefix}{percent:.1f}% | {self._format_size(downloaded)}/{total_text} | "
                    f"{self._format_speed(speed)} | ETA {self._format_eta(eta)}"
                )
                now = time.time()
                should_update_ui = (
                    abs(percent - self._last_ui_percent) >= 0.3
                    or (now - self._last_ui_update_time) >= 0.2
                    or percent >= 99.9
                )
                if should_update_ui:
                    self._last_ui_percent = percent
                    self._last_ui_update_time = now
                    self.root.after(0, lambda p=ui_progress: self.progress_var.set(p))
                    self.root.after(0, lambda s=status_text: self.status_var.set(s))

                bucket = int(percent // 10) if total > 0 else -1
                if bucket > self._last_progress_bucket:
                    self._last_progress_bucket = bucket
                    self._append_log(f"{prefix}下载进度: {status_text}")
            elif status == "finished":
                self._append_log("下载完成，进入后处理阶段")
                self.root.after(0, lambda: self.status_var.set("下载完成，正在处理文件..."))
        return _hook

    def start_download(self, url, token, format_config, audio_track_config=None, playlist_mode=False, subtitle_config=None):
        if not yt_dlp:
            raise ImportError("yt_dlp 未安装")
        selector = self._build_download_selector(format_config, audio_track_config)
        ydl_opts = {
            "outtmpl": os.path.join(self.download_path, "%(title)s.%(ext)s"),
            "noplaylist": not playlist_mode,
            "concurrent_fragment_downloads": 8,
            "socket_timeout": 20,
            "retries": 5,
            "progress_hooks": [self._make_progress_hook(token)],
            "format": selector,
            "merge_output_format": "mp4",
            "logger": self._YDLLogger(self, "download"),
            "progress_with_newline": True,
        }
        if self.proxy_settings["type"] != "none":
            proxy = f"{self.proxy_settings['type']}://{self.proxy_settings['host']}:{self.proxy_settings['port']}"
            ydl_opts["proxy"] = proxy

        audio_codec = format_config.get("audio_codec")
        if audio_codec:
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": self.AUDIO_CODEC_MAP.get(audio_codec, audio_codec),
                "preferredquality": "192",
            }]

        if subtitle_config:
            ydl_opts["writesubtitles"] = not subtitle_config.get("auto", False)
            ydl_opts["writeautomaticsub"] = subtitle_config.get("auto", False)
            ydl_opts["subtitleslangs"] = [subtitle_config["lang"]]
            ydl_opts["subtitlesformat"] = "best"
        self._append_log(f"yt-dlp 命令(下载): {self._build_ydl_command_preview(ydl_opts, url)}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            if self._cancel_requested:
                return {"success": False, "cancelled": True, "error": "已取消"}
            return {"success": True}
        except UserCancelledError:
            return {"success": False, "cancelled": True, "error": "已取消"}
        except ConnectionError:
            return {"success": False, "error": "网络连接失败，请检查网络设置"}
        except TimeoutError:
            return {"success": False, "error": "连接超时，请稍后重试"}
        except OSError as exc:
            return {"success": False, "error": f"文件系统错误：{exc}"}
        except Exception as exc:
            if yt_dlp and hasattr(yt_dlp, "utils") and hasattr(yt_dlp.utils, "DownloadError"):
                if isinstance(exc, yt_dlp.utils.DownloadError):
                    if "用户取消下载" in str(exc):
                        return {"success": False, "cancelled": True, "error": "已取消"}
                    return {"success": False, "error": f"下载失败：{exc}"}
            return {"success": False, "error": f"发生未知错误：{exc}"}

    def start_download_threaded(self, url, token, format_config, audio_track_config=None, playlist_mode=False, subtitle_config=None, on_success=None, on_error=None, on_cancel=None):
        def _worker():
            return self.start_download(
                url=url,
                token=token,
                format_config=format_config,
                audio_track_config=audio_track_config,
                playlist_mode=playlist_mode,
                subtitle_config=subtitle_config,
            )

        future = self._executor.submit(_worker)

        def _on_done(f):
            try:
                result = f.result()
            except Exception as exc:
                result = {"success": False, "error": str(exc)}
            if self.root:
                self.root.after(0, lambda r=result: self._on_download_complete(token, r, on_success, on_error, on_cancel))

        future.add_done_callback(_on_done)
        return future

    def _on_download_complete(self, token, result, on_success, on_error, on_cancel):
        if token != self._task_token:
            return
        was_cancelled = self._cancel_requested or result.get("cancelled", False)
        self._cancel_requested = False
        self._set_action_state("idle")
        if was_cancelled:
            if on_cancel:
                on_cancel()
            return
        if result.get("success"):
            if on_success:
                on_success()
        elif on_error:
            on_error(result.get("error", "未知错误"))


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()
