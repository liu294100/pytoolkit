import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os

import requests
import yt_dlp


class YoutubeSubtitleDownloader:

    def __init__(self, root):
        self.root = root
        self.root.title("YouTube 字幕下载器")
        self.root.geometry("800x600")

        self.lang_map = {}

        self.build_ui()

    def build_ui(self):

        # URL
        url_frame = ttk.LabelFrame(
            self.root,
            text="YouTube 视频"
        )
        url_frame.pack(fill="x", padx=10, pady=5)

        self.url_var = tk.StringVar()

        ttk.Entry(
            url_frame,
            textvariable=self.url_var
        ).pack(
            fill="x",
            padx=10,
            pady=10
        )

        # 代理
        proxy_frame = ttk.LabelFrame(
            self.root,
            text="代理设置"
        )
        proxy_frame.pack(fill="x", padx=10, pady=5)

        self.use_proxy = tk.BooleanVar(
            value=True
        )

        ttk.Checkbutton(
            proxy_frame,
            text="启用代理",
            variable=self.use_proxy
        ).grid(
            row=0,
            column=0,
            padx=10,
            pady=10
        )

        ttk.Label(
            proxy_frame,
            text="地址"
        ).grid(row=0, column=1)

        self.proxy_host = tk.StringVar(
            value="127.0.0.1"
        )

        ttk.Entry(
            proxy_frame,
            textvariable=self.proxy_host,
            width=15
        ).grid(row=0, column=2)

        ttk.Label(
            proxy_frame,
            text="端口"
        ).grid(row=0, column=3)

        self.proxy_port = tk.StringVar(
            value="7890"
        )

        ttk.Entry(
            proxy_frame,
            textvariable=self.proxy_port,
            width=8
        ).grid(row=0, column=4)

        ttk.Button(
            proxy_frame,
            text="检测代理",
            command=self.check_proxy
        ).grid(row=0, column=5, padx=10)

        # 字幕
        sub_frame = ttk.LabelFrame(
            self.root,
            text="字幕"
        )
        sub_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            sub_frame,
            text="获取字幕语言",
            command=self.load_languages
        ).grid(
            row=0,
            column=0,
            padx=10,
            pady=10
        )

        self.lang_combo = ttk.Combobox(
            sub_frame,
            width=50,
            state="readonly"
        )

        self.lang_combo.grid(
            row=0,
            column=1,
            padx=10
        )

        ttk.Button(
            sub_frame,
            text="下载SRT",
            command=self.download_subtitle
        ).grid(
            row=0,
            column=2,
            padx=10
        )

        # 保存目录
        save_frame = ttk.LabelFrame(
            self.root,
            text="保存目录"
        )
        save_frame.pack(fill="x", padx=10, pady=5)

        self.save_dir = tk.StringVar(
            value=os.getcwd()
        )

        ttk.Entry(
            save_frame,
            textvariable=self.save_dir
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=10,
            pady=10
        )

        ttk.Button(
            save_frame,
            text="选择目录",
            command=self.select_folder
        ).pack(
            side="left",
            padx=10
        )

        # 日志
        log_frame = ttk.LabelFrame(
            self.root,
            text="日志"
        )
        log_frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5
        )

        self.log_text = tk.Text(
            log_frame
        )

        self.log_text.pack(
            fill="both",
            expand=True
        )

    def log(self, msg):
        self.log_text.insert(
            tk.END,
            msg + "\n"
        )
        self.log_text.see(tk.END)

    def get_proxy(self):

        if not self.use_proxy.get():
            return None

        host = self.proxy_host.get().strip()
        port = self.proxy_port.get().strip()

        if not host or not port:
            return None

        return f"http://{host}:{port}"

    def select_folder(self):

        path = filedialog.askdirectory()

        if path:
            self.save_dir.set(path)

    def check_proxy(self):

        threading.Thread(
            target=self._check_proxy,
            daemon=True
        ).start()

    def _check_proxy(self):

        proxy = self.get_proxy()

        if not proxy:
            self.log("未启用代理")
            return

        self.log("检测代理中...")

        try:

            requests.get(
                "https://www.youtube.com",
                proxies={
                    "http": proxy,
                    "https": proxy
                },
                timeout=5
            )

            self.log(
                f"代理可用: {proxy}"
            )

        except Exception as e:

            self.log(
                f"代理不可用: {e}"
            )

    def load_languages(self):

        threading.Thread(
            target=self._load_languages,
            daemon=True
        ).start()

    def _load_languages(self):

        try:

            url = self.url_var.get().strip()

            if not url:
                return

            self.log("获取视频信息...")

            opts = {
                "quiet": True
            }

            proxy = self.get_proxy()

            if proxy:
                opts["proxy"] = proxy

            with yt_dlp.YoutubeDL(opts) as ydl:

                info = ydl.extract_info(
                    url,
                    download=False
                )

            self.lang_map.clear()

            subtitles = info.get(
                "subtitles",
                {}
            )

            auto_subs = info.get(
                "automatic_captions",
                {}
            )

            langs = []

            for lang in subtitles:

                text = (
                    f"{lang} (人工字幕)"
                )

                langs.append(text)

                self.lang_map[text] = lang

            for lang in auto_subs:

                if lang not in subtitles:

                    text = (
                        f"{lang} (自动字幕)"
                    )

                    langs.append(text)

                    self.lang_map[text] = lang

            langs.sort()

            self.lang_combo["values"] = langs

            if langs:
                self.lang_combo.current(0)

            self.log(
                f"发现 {len(langs)} 个字幕语言"
            )

        except Exception as e:

            self.log(str(e))

    def download_subtitle(self):

        threading.Thread(
            target=self._download_subtitle,
            daemon=True
        ).start()

    def _download_subtitle(self):

        try:

            url = self.url_var.get().strip()

            if not url:
                return

            selected = (
                self.lang_combo.get()
            )

            if not selected:

                messagebox.showerror(
                    "错误",
                    "请选择字幕语言"
                )

                return

            lang = self.lang_map[selected]

            self.log(
                f"开始下载 {lang}"
            )

            opts = {
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": [lang],
                "subtitlesformat": "srt",
                "outtmpl": os.path.join(
                    self.save_dir.get(),
                    "%(title)s.%(ext)s"
                )
            }

            proxy = self.get_proxy()

            if proxy:
                opts["proxy"] = proxy

            with yt_dlp.YoutubeDL(opts) as ydl:

                ydl.download([url])

            self.log(
                "字幕下载完成"
            )

        except Exception as e:

            self.log(str(e))


def main():

    root = tk.Tk()

    YoutubeSubtitleDownloader(
        root
    )

    root.mainloop()


if __name__ == "__main__":
    main()