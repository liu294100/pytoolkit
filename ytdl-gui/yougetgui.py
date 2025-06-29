import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import re
import threading
import time
import subprocess
import json
import locale
from datetime import timedelta
import you_get
import you_get.common
import you_get.util
import you_get.extractors
import io
from contextlib import redirect_stdout, redirect_stderr

class YouGetDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("You-Get 多站点下载器")
        self.root.geometry("800x750")
        self.root.minsize(700, 650)
        
        # 设置样式
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Arial", 10))
        self.style.configure("TLabel", font=("Arial", 10))
        self.style.configure("TRadiobutton", font=("Arial", 10))
        self.style.configure("TCheckbutton", font=("Arial", 10))
        
        # 设置网络参数
        self.max_retries = 3  # 最大重试次数
        self.timeout = 30     # 超时时间（秒）
        
        # 检测系统编码
        self.system_encoding = locale.getpreferredencoding() or 'utf-8'
        
        # 创建主框架
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # URL 输入区域
        url_frame = ttk.Frame(main_frame)
        url_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(url_frame, text="视频URL:").pack(side=tk.LEFT, padx=5)
        self.url_entry = ttk.Entry(url_frame)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.fetch_btn = ttk.Button(url_frame, text="获取信息", command=self.fetch_video_info)
        self.fetch_btn.pack(side=tk.LEFT, padx=5)
        
        # 查看支持网站按钮
        sites_btn = ttk.Button(url_frame, text="查看支持网站", command=self.show_supported_sites)
        sites_btn.pack(side=tk.LEFT, padx=5)
        
        # 视频信息区域
        info_frame = ttk.LabelFrame(main_frame, text="视频信息", padding="5")
        info_frame.pack(fill=tk.X, pady=5)
        
        self.title_var = tk.StringVar(value="")
        ttk.Label(info_frame, text="标题:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, textvariable=self.title_var, wraplength=600).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        self.site_var = tk.StringVar(value="")
        ttk.Label(info_frame, text="网站:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, textvariable=self.site_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        self.size_var = tk.StringVar(value="")
        ttk.Label(info_frame, text="大小:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, textvariable=self.size_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # 下载选项区域
        options_frame = ttk.LabelFrame(main_frame, text="下载选项", padding="5")
        options_frame.pack(fill=tk.X, pady=5)
        
        # 下载类型选择
        type_frame = ttk.Frame(options_frame)
        type_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(type_frame, text="下载类型:").pack(side=tk.LEFT, padx=5)
        
        self.download_type = tk.StringVar(value="video")
        ttk.Radiobutton(type_frame, text="视频", variable=self.download_type, 
                       value="video", command=self.update_format_options).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_frame, text="仅音频", variable=self.download_type, 
                       value="audio", command=self.update_format_options).pack(side=tk.LEFT, padx=5)
        
        # 质量选择
        format_frame = ttk.Frame(options_frame)
        format_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(format_frame, text="质量选择:").pack(side=tk.LEFT, padx=5)
        self.format_combo = ttk.Combobox(format_frame, width=40, state="readonly")
        self.format_combo.pack(side=tk.LEFT, padx=5)
        
        # 音频格式选择（仅在音频模式下显示）
        self.audio_format_frame = ttk.Frame(options_frame)
        
        ttk.Label(self.audio_format_frame, text="输出格式:").pack(side=tk.LEFT, padx=5)
        self.audio_format_var = tk.StringVar(value="mp3")
        audio_formats = [("MP3", "mp3"), ("AAC", "aac"), ("OGG", "ogg"), ("FLAC", "flac"), ("WAV", "wav")]
        
        for text, value in audio_formats:
            ttk.Radiobutton(self.audio_format_frame, text=text, variable=self.audio_format_var, 
                           value=value).pack(side=tk.LEFT, padx=5)
        
        # 高级选项
        advanced_frame = ttk.LabelFrame(options_frame, text="高级选项", padding="3")
        advanced_frame.pack(fill=tk.X, pady=3)
        
        # 第一行：字幕、播放列表和文件选项
        advanced_row1 = ttk.Frame(advanced_frame)
        advanced_row1.pack(fill=tk.X, pady=1)
        
        self.download_subtitle = tk.BooleanVar(value=False)
        ttk.Checkbutton(advanced_row1, text="下载字幕", variable=self.download_subtitle).pack(side=tk.LEFT, padx=3)
        
        self.download_playlist = tk.BooleanVar(value=False)
        ttk.Checkbutton(advanced_row1, text="下载播放列表", variable=self.download_playlist).pack(side=tk.LEFT, padx=8)
        
        self.skip_existing = tk.BooleanVar(value=False)
        ttk.Checkbutton(advanced_row1, text="跳过已存在文件", variable=self.skip_existing).pack(side=tk.LEFT, padx=8)
        
        self.auto_rename = tk.BooleanVar(value=False)
        ttk.Checkbutton(advanced_row1, text="自动重命名", variable=self.auto_rename).pack(side=tk.LEFT, padx=8)
        
        # 第二行：输出格式和连接设置
        advanced_row2 = ttk.Frame(advanced_frame)
        advanced_row2.pack(fill=tk.X, pady=1)
        
        ttk.Label(advanced_row2, text="输出格式:").pack(side=tk.LEFT, padx=3)
        self.output_format_var = tk.StringVar(value="auto")
        format_options = [("自动", "auto"), ("MP4", "mp4"), ("FLV", "flv"), ("WebM", "webm")]
        
        for text, value in format_options:
            ttk.Radiobutton(advanced_row2, text=text, variable=self.output_format_var, 
                           value=value).pack(side=tk.LEFT, padx=3)
        
        ttk.Label(advanced_row2, text="并发连接:").pack(side=tk.LEFT, padx=(15,3))
        self.connections = tk.StringVar(value="5")
        conn_spinbox = ttk.Spinbox(advanced_row2, from_=1, to=20, width=4, textvariable=self.connections)
        conn_spinbox.pack(side=tk.LEFT, padx=3)
        
        # 代理设置
        proxy_frame = ttk.LabelFrame(options_frame, text="代理设置", padding="5")
        proxy_frame.pack(fill=tk.X, pady=5)
        
        # 代理启用选项
        proxy_enable_frame = ttk.Frame(proxy_frame)
        proxy_enable_frame.pack(fill=tk.X, pady=2)
        
        self.use_proxy = tk.BooleanVar(value=False)  # 默认不启用代理
        ttk.Checkbutton(proxy_enable_frame, text="使用代理", variable=self.use_proxy, 
                       command=self.toggle_proxy).pack(side=tk.LEFT, padx=5)
        
        # 代理类型选择
        self.proxy_type = tk.StringVar(value="http")
        proxy_types = [("HTTP", "http"), ("SOCKS5", "socks5")]
        for text, value in proxy_types:
            ttk.Radiobutton(proxy_enable_frame, text=text, variable=self.proxy_type, 
                           value=value).pack(side=tk.LEFT, padx=10)
        
        # 代理地址输入
        proxy_addr_frame = ttk.Frame(proxy_frame)
        proxy_addr_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(proxy_addr_frame, text="代理地址:").pack(side=tk.LEFT, padx=5)
        self.proxy_entry = ttk.Entry(proxy_addr_frame, width=30)
        self.proxy_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.proxy_entry.insert(0, "127.0.0.1:7890")
        self.proxy_entry.config(state="disabled")  # 默认禁用状态
        
        # 常用代理配置
        proxy_presets_frame = ttk.Frame(proxy_frame)
        proxy_presets_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(proxy_presets_frame, text="常用配置:").pack(side=tk.LEFT, padx=5)
        presets = [("Clash", "127.0.0.1:7890"), ("ClashVerge", "127.0.0.1:7897"), ("V2Ray", "127.0.0.1:10809"), ("自定义", "")]
        
        self.proxy_preset = tk.StringVar()
        proxy_preset_combo = ttk.Combobox(proxy_presets_frame, textvariable=self.proxy_preset, 
                                        values=[p[0] for p in presets], width=10, state="readonly")
        proxy_preset_combo.pack(side=tk.LEFT, padx=5)
        proxy_preset_combo.current(0)  # 默认选择第一个
        
        # 绑定选择事件
        def on_preset_selected(event):
            selected = self.proxy_preset.get()
            for name, addr in presets:
                if name == selected and addr:  # 如果地址不为空
                    self.proxy_entry.delete(0, tk.END)
                    self.proxy_entry.insert(0, addr)
        
        proxy_preset_combo.bind("<<ComboboxSelected>>", on_preset_selected)
        
        # 测试连接按钮
        self.test_proxy_btn = ttk.Button(proxy_presets_frame, text="测试连接", 
                                       command=self.test_proxy_connection)
        self.test_proxy_btn.pack(side=tk.RIGHT, padx=5)
        self.test_proxy_btn.config(state="disabled")
        
        # 保存位置
        save_frame = ttk.Frame(options_frame)
        save_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(save_frame, text="保存位置:").pack(side=tk.LEFT, padx=5)
        self.save_path_var = tk.StringVar(value=os.path.expanduser("~/Downloads"))
        ttk.Entry(save_frame, textvariable=self.save_path_var, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(save_frame, text="浏览...", command=self.browse_save_location).pack(side=tk.LEFT, padx=5)
        
        # 下载按钮
        self.download_btn = ttk.Button(main_frame, text="开始下载", command=self.start_download)
        self.download_btn.pack(pady=10)
        self.download_btn.config(state="disabled")
        
        # 进度条
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        self.eta_var = tk.StringVar(value="")
        
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X)
        
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=5)
        ttk.Label(status_frame, textvariable=self.eta_var).pack(side=tk.RIGHT, padx=5)
        
        # 存储视频信息
        self.video_info = None
        self.formats = []
        
        # 初始化格式选项
        self.update_format_options()
        
        # 绑定快捷键
        self.url_entry.bind('<Return>', lambda event: self.fetch_video_info())
        self.root.bind('<Control-v>', self._paste_url)
        self.root.bind('<Control-d>', lambda event: self.download_video())
        self.root.bind('<F1>', lambda event: self.show_supported_sites())
        self.root.bind('<F5>', lambda event: self.fetch_video_info())
        
        # 设置窗口属性
        self.root.minsize(800, 650)  # 最小窗口大小
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # 添加状态栏提示
        self.status_var.set("就绪 - 快捷键: Ctrl+V粘贴URL, F5获取信息, Ctrl+D下载, F1查看支持网站")
    
    def _paste_url(self, event=None):
        """粘贴URL到输入框"""
        try:
            clipboard_text = self.root.clipboard_get()
            if clipboard_text and ('http' in clipboard_text or 'www.' in clipboard_text):
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, clipboard_text.strip())
                self.status_var.set("URL已粘贴，按F5获取视频信息")
        except:
            pass
    
    def _on_closing(self):
        """窗口关闭事件处理"""
        # 如果有正在进行的下载，询问是否确认关闭
        if hasattr(self, '_downloading') and self._downloading:
            if messagebox.askokcancel("确认退出", "正在下载中，确定要退出吗？"):
                self.root.destroy()
        else:
            self.root.destroy()
    
    def show_supported_sites(self):
        """显示支持的网站列表"""
        sites_info = """
🌐 You-Get 支持的主要网站和平台：

📺 视频平台：
• YouTube - 全球最大视频平台
• 哔哩哔哩 (Bilibili) - 中国知名弹幕视频网站
• 优酷 (Youku) - 阿里巴巴旗下视频平台
• 爱奇艺 (iQiyi) - 百度旗下视频平台
• 腾讯视频 - 腾讯旗下视频平台
• 芒果TV - 湖南卫视官方平台
• 搜狐视频 - 搜狐旗下视频平台
• 网易云音乐 - 网易旗下音乐平台
• QQ音乐 - 腾讯旗下音乐平台
• 酷狗音乐 - 酷狗旗下音乐平台

📱 短视频平台：
• 抖音 (TikTok) - 字节跳动短视频平台
• 快手 - 快手科技短视频平台
• 微博视频 - 新浪微博视频内容
• 小红书 - 生活方式分享平台

🎬 国际平台：
• Vimeo - 高质量视频分享平台
• Dailymotion - 法国视频分享网站
• Facebook - 社交媒体视频
• Instagram - 图片和短视频分享
• Twitter - 社交媒体视频

🎵 音频平台：
• SoundCloud - 音频分享平台
• Bandcamp - 独立音乐平台
• MixCloud - DJ混音平台

📚 教育平台：
• Coursera - 在线课程平台
• Khan Academy - 免费教育资源
• TED - 思想分享平台

🎮 游戏平台：
• Twitch - 游戏直播平台
• Steam - 游戏平台视频内容

📰 新闻媒体：
• BBC iPlayer - 英国广播公司
• CNN - 美国有线电视新闻网
• 央视网 - 中央电视台官网

⚠️ 注意事项：
• 部分网站可能需要代理访问
• 某些内容可能有地区限制
• 建议使用最新版本的 you-get
• 如遇问题，请检查网络连接和代理设置

💡 提示：
• 支持播放列表批量下载
• 可下载字幕文件
• 支持多种视频质量选择
• 支持音频格式转换
        """
        
        # 创建新窗口显示支持网站信息
        sites_window = tk.Toplevel(self.root)
        sites_window.title("You-Get 支持的网站列表")
        sites_window.geometry("600x700")
        sites_window.resizable(True, True)
        
        # 创建滚动文本框
        text_frame = ttk.Frame(sites_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 文本框和滚动条
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Arial", 10))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 插入内容
        text_widget.insert(tk.END, sites_info)
        text_widget.config(state=tk.DISABLED)  # 设为只读
        
        # 添加关闭按钮
        close_btn = ttk.Button(sites_window, text="关闭", command=sites_window.destroy)
        close_btn.pack(pady=10)
        
        # 居中显示窗口
        sites_window.transient(self.root)
        sites_window.grab_set()
        
        # 计算居中位置
        sites_window.update_idletasks()
        x = (sites_window.winfo_screenwidth() // 2) - (sites_window.winfo_width() // 2)
        y = (sites_window.winfo_screenheight() // 2) - (sites_window.winfo_height() // 2)
        sites_window.geometry(f"+{x}+{y}")
    
    def toggle_proxy(self):
        if self.use_proxy.get():
            self.proxy_entry.config(state="normal")
            self.test_proxy_btn.config(state="normal")
        else:
            self.proxy_entry.config(state="disabled")
            self.test_proxy_btn.config(state="disabled")
    
    def test_proxy_connection(self):
        """测试代理连接是否正常"""
        if not self.use_proxy.get():
            messagebox.showinfo("提示", "请先启用代理")
            return
        
        proxy_addr = self.proxy_entry.get().strip()
        
        if not proxy_addr:
            messagebox.showerror("错误", "请输入代理地址")
            return
        
        # 禁用测试按钮，防止重复点击
        self.test_proxy_btn.config(state="disabled")
        self.status_var.set("正在测试代理连接...")
        
        # 在新线程中测试连接
        threading.Thread(target=self._test_proxy_thread, args=(proxy_addr,), daemon=True).start()
    
    def _test_proxy_thread(self, proxy_addr):
        """在线程中测试代理连接"""
        try:
            import requests
            start_time = time.time()
            
            proxy_type = self.proxy_type.get()
            proxy_url = f"{proxy_type}://{proxy_addr}"
            
            # 测试多个网站以确保代理可用性
            test_urls = [
                "http://httpbin.org/ip",
                "https://api.github.com",
                "http://www.google.com"
            ]
            
            success_count = 0
            total_time = 0
            
            try:
                proxies = {"http": proxy_url, "https": proxy_url}
                
                for url in test_urls:
                    try:
                        response = requests.get(url, proxies=proxies, timeout=8)
                        if response.status_code == 200:
                            success_count += 1
                            total_time += time.time() - start_time
                            break  # 只要有一个成功就行
                    except:
                        continue
                
                if success_count > 0:
                    elapsed = time.time() - start_time
                    self.root.after(0, lambda: messagebox.showinfo("成功", 
                                                                f"代理连接成功！\n响应时间: {elapsed:.2f}秒"))
                    self.root.after(0, lambda: self.status_var.set(f"代理测试成功，延迟: {elapsed:.2f}秒"))
                else:
                    self.root.after(0, lambda: messagebox.showwarning("警告", 
                                                                   "代理连接失败，无法访问测试网站"))
                    self.root.after(0, lambda: self.status_var.set("代理测试失败"))
            
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", 
                                                             f"代理连接失败: {str(e)}"))
                self.root.after(0, lambda: self.status_var.set("代理连接失败"))
        
        except ImportError:
            self.root.after(0, lambda: messagebox.showerror("错误", 
                                                         "缺少requests库，无法测试代理连接"))
            self.root.after(0, lambda: self.status_var.set("缺少依赖库"))
        
        finally:
            # 恢复按钮状态
            self.root.after(0, lambda: self.test_proxy_btn.config(state="normal"))
    
    def browse_save_location(self):
        directory = filedialog.askdirectory(initialdir=self.save_path_var.get())
        if directory:
            self.save_path_var.set(directory)
    
    def update_format_options(self, event=None):
        """根据下载类型更新格式选项"""
        # 如果已经获取了视频信息，使用详细的格式选项
        if hasattr(self, 'video_info') and self.video_info:
            self._update_format_combo()
        else:
            # 如果还没有视频信息，显示基本预设选项
            if self.download_type.get() == "audio":
                self.audio_format_frame.pack(fill=tk.X, pady=5)
                # 音频格式选项
                audio_formats = [
                    "最佳音质",
                    "高音质 (320kbps)", 
                    "标准音质 (192kbps)",
                    "普通音质 (128kbps)",
                    "低音质 (96kbps)"
                ]
                self.format_combo['values'] = audio_formats
            else:
                self.audio_format_frame.pack_forget()
                # 视频格式选项
                video_formats = [
                    "最佳质量",
                    "8K (4320p)",
                    "4K (2160p)", 
                    "2K (1440p)",
                    "全高清 (1080p)",
                    "高清 (720p)",
                    "标清 (480p)",
                    "低清 (360p)",
                    "最低质量"
                ]
                self.format_combo['values'] = video_formats
            
            # 设置默认选择
            if len(self.format_combo['values']) > 0:
                self.format_combo.current(0)
    
    def fetch_video_info(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("错误", "请输入视频URL")
            return
        
        # 基本URL格式验证
        if not (url.startswith('http://') or url.startswith('https://')):
            if messagebox.askyesno("提示", "URL似乎缺少协议前缀，是否自动添加 https:// ？"):
                url = 'https://' + url
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, url)
            else:
                return
        
        self.status_var.set("正在获取视频信息...")
        self.fetch_btn.config(state="disabled")
        
        # 在新线程中获取视频信息
        threading.Thread(target=self._fetch_video_info_thread, args=(url,), daemon=True).start()
    
    def _fetch_video_info_thread(self, url):
        """在线程中获取视频信息"""
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                if retry_count == 0:
                    retry_msg = ''
                else:
                    retry_msg = f' - 重试 {retry_count}/{self.max_retries}'
                self.root.after(0, lambda msg=retry_msg: self.status_var.set(f"正在获取视频信息{msg}"))
                
                # 设置代理
                if self.use_proxy.get():
                    proxy_addr = self.proxy_entry.get().strip()
                    if proxy_addr:
                        proxy_type = self.proxy_type.get()
                        proxy_url = f"{proxy_type}://{proxy_addr}"
                        try:
                            you_get.common.set_proxy(proxy_url)
                        except Exception as e:
                            print(f"设置代理失败: {e}")
                else:
                    # 清除代理设置
                    try:
                        you_get.common.set_proxy(None)
                    except:
                        pass
                
                # 使用you-get的内部API获取视频信息
                try:
                    import you_get.extractors
                    from you_get.common import url_info
                    
                    # 设置User-Agent和其他请求头来避免反爬虫
                    import you_get.common
                    you_get.common.headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1'
                    }
                    
                    # 获取视频信息
                    info = None
                    try:
                        info = url_info(url)
                    except Exception as api_error:
                        print(f"API获取失败: {api_error}")
                        info = None
                    
                    if not info:
                        # 如果直接获取失败，尝试使用输出捕获方式
                        stdout_capture = io.StringIO()
                        stderr_capture = io.StringIO()
                        
                        try:
                            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                                you_get.common.any_download(url, info_only=True)
                        except Exception as download_error:
                            print(f"下载信息获取失败: {download_error}")
                            # 继续尝试解析已有的输出
                        
                        output = stdout_capture.getvalue()
                        error_output = stderr_capture.getvalue()
                        
                        print(f"输出内容: {output[:500]}...")  # 调试信息
                        print(f"错误输出: {error_output[:500]}...")  # 调试信息
                        
                        if not output and error_output:
                            # 分析错误类型并提供针对性解决方案
                            if "HTTP Error 412" in error_output:
                                raise Exception("获取视频信息失败: HTTP Error 412: Precondition Failed\n\n这是B站等网站的反爬虫机制导致的。\n\n解决方案：\n1. 尝试使用yt-dlp替代you-get\n2. 使用浏览器插件下载\n3. 等待一段时间后重试\n4. 检查是否需要登录账号")
                            elif "HTTP Error 403" in error_output:
                                raise Exception("访问被拒绝: HTTP Error 403\n\n可能原因：\n1. 视频需要登录观看\n2. 存在地区限制\n3. 网站反爬虫机制\n\n建议解决方案：\n1. 检查是否需要登录\n2. 尝试使用代理\n3. 确认视频链接是否正确")
                            elif "HTTP Error 404" in error_output:
                                raise Exception("视频不存在: HTTP Error 404\n\n请检查：\n1. URL是否正确\n2. 视频是否已被删除\n3. 是否为私有视频")
                            elif "not supported" in error_output.lower():
                                raise Exception(f"该网站暂不支持\n\n建议：\n1. 尝试使用yt-dlp工具\n2. 检查you-get版本是否最新\n3. 查看官方支持的网站列表")
                            else:
                                raise Exception(f"获取视频信息失败:\n{error_output}\n\n通用解决方案：\n1. 检查网络连接\n2. 尝试使用代理\n3. 更新you-get版本\n4. 稍后重试")
                        
                        # 解析输出信息
                        title = "未知标题"
                        site = "未知网站"
                        streams = {}
                        
                        # 更精确的解析模式
                        lines = output.split('\n')
                        current_section = None
                        
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                                
                            # 解析标题
                            if line.startswith('Title:') or line.startswith('title:'):
                                title = line.split(':', 1)[1].strip()
                            elif line.startswith('Site:') or line.startswith('site:'):
                                site = line.split(':', 1)[1].strip()
                            # 解析格式信息
                            elif 'format' in line.lower() and 'available' in line.lower():
                                current_section = 'formats'
                            elif current_section == 'formats' and ('x' in line or 'p' in line or 'kbps' in line):
                                # 解析格式行，例如: "mp4_hd2 1920x1080 video/mp4 123.45MB"
                                parts = line.split()
                                if len(parts) >= 2:
                                    format_id = parts[0]
                                    quality = parts[1] if len(parts) > 1 else 'unknown'
                                    
                                    # 查找文件大小
                                    size_bytes = 0
                                    for part in parts:
                                        size_match = re.match(r'([\d.]+)\s*([KMG]?)B', part)
                                        if size_match:
                                            size_num = float(size_match.group(1))
                                            size_unit = size_match.group(2)
                                            
                                            if size_unit == 'K':
                                                size_bytes = size_num * 1024
                                            elif size_unit == 'M':
                                                size_bytes = size_num * 1024 * 1024
                                            elif size_unit == 'G':
                                                size_bytes = size_num * 1024 * 1024 * 1024
                                            else:
                                                size_bytes = size_num
                                            break
                                    
                                    streams[format_id] = {
                                        'quality': quality,
                                        'container': format_id,
                                        'size': int(size_bytes),
                                        'format': format_id
                                    }
                    else:
                        # 使用you-get内部API返回的信息
                        title = info.get('title', '未知标题')
                        site = info.get('site', '未知网站')
                        streams = {}
                        
                        # 处理流信息
                        if 'streams' in info:
                            for stream_id, stream_data in info['streams'].items():
                                quality_info = stream_data.get('video_profile', stream_data.get('quality', 'unknown'))
                                container = stream_data.get('container', stream_id)
                                size = stream_data.get('size', 0)
                                
                                # 构建更详细的质量描述
                                if 'video_profile' in stream_data:
                                    quality = f"{quality_info} ({container})"
                                elif 'quality' in stream_data:
                                    quality = f"{quality_info} ({container})"
                                else:
                                    quality = f"{container}格式"
                                
                                streams[stream_id] = {
                                    'quality': quality,
                                    'container': container,
                                    'size': size if isinstance(size, (int, float)) else 0,
                                    'format': stream_id
                                }
                    
                    # 如果没有找到具体格式，添加默认格式选项
                    if not streams:
                        # 添加常见的视频格式选项
                        default_formats = [
                            ('best', '最佳质量', 0),
                            ('worst', '最低质量', 0),
                            ('mp4', 'MP4格式', 0),
                            ('flv', 'FLV格式', 0),
                            ('webm', 'WebM格式', 0)
                        ]
                        
                        for fmt_id, fmt_desc, size in default_formats:
                            streams[fmt_id] = {
                                'quality': fmt_desc,
                                'container': fmt_id,
                                'size': size,
                                'format': fmt_id
                            }
                    
                    # 构建视频信息
                    self.video_info = {
                        'title': title,
                        'site': site,
                        'streams': streams
                    }
                    
                    self.root.after(0, self._update_video_info)
                    self.root.after(0, lambda: self.status_var.set("视频信息获取成功"))
                    self.root.after(0, lambda: self.fetch_btn.config(state="normal"))
                    return
                
                except Exception as e:
                    error_msg = str(e)
                    
                    # 如果是HTTP 412错误，尝试使用yt-dlp作为备用方案
                    if "HTTP Error 412" in error_msg and retry_count == 0:
                        try:
                            print("尝试使用yt-dlp作为备用方案...")
                            self.root.after(0, lambda: self.status_var.set("you-get失败，尝试yt-dlp..."))
                            
                            # 尝试使用yt-dlp获取信息
                            import subprocess
                            import json
                            
                            cmd = ['yt-dlp', '--dump-json', '--no-download', url]
                            if self.use_proxy.get() and self.proxy_entry.get().strip():
                                proxy_addr = self.proxy_entry.get().strip()
                                proxy_type = self.proxy_type.get()
                                proxy_url = f"{proxy_type}://{proxy_addr}"
                                cmd.extend(['--proxy', proxy_url])
                            
                            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                            
                            if result.returncode == 0 and result.stdout:
                                # 解析yt-dlp的JSON输出
                                try:
                                    json_data = json.loads(result.stdout)
                                    # 处理可能的数组格式（播放列表）或单个对象
                                    if isinstance(json_data, list):
                                        if len(json_data) > 0:
                                            video_data = json_data[0]  # 取第一个视频
                                        else:
                                            raise ValueError("yt-dlp返回空列表")
                                    else:
                                        video_data = json_data
                                    
                                    # 确保video_data是字典类型
                                    if not isinstance(video_data, dict):
                                        raise ValueError(f"yt-dlp返回的数据格式不正确: {type(video_data)}")
                                    
                                    title = video_data.get('title', '未知标题')
                                    site = video_data.get('extractor', '未知网站')
                                    streams = {}
                                except (json.JSONDecodeError, ValueError, KeyError) as parse_error:
                                    raise Exception(f"解析yt-dlp输出失败: {str(parse_error)}")
                                
                                # 处理格式信息
                                formats = video_data.get('formats', [])
                                for fmt in formats:
                                    format_id = fmt.get('format_id', 'unknown')
                                    height = fmt.get('height')
                                    width = fmt.get('width')
                                    fps = fmt.get('fps')
                                    vcodec = fmt.get('vcodec', 'none')
                                    acodec = fmt.get('acodec', 'none')
                                    container = fmt.get('ext', 'unknown')
                                    filesize = fmt.get('filesize', 0) or 0
                                    format_note = fmt.get('format_note', '')
                                    
                                    # 构建更详细的质量描述
                                    quality_parts = []
                                    
                                    # 添加分辨率信息
                                    if height:
                                        if height >= 2160:
                                            quality_parts.append(f"4K ({height}p)")
                                        elif height >= 1440:
                                            quality_parts.append(f"2K ({height}p)")
                                        elif height >= 1080:
                                            quality_parts.append(f"全高清 ({height}p)")
                                        elif height >= 720:
                                            quality_parts.append(f"高清 ({height}p)")
                                        elif height >= 480:
                                            quality_parts.append(f"标清 ({height}p)")
                                        else:
                                            quality_parts.append(f"{height}p")
                                    
                                    # 添加帧率信息
                                    if fps and fps > 30:
                                        quality_parts.append(f"{fps}fps")
                                    
                                    # 添加编码信息
                                    if vcodec != 'none' and acodec != 'none':
                                        quality_parts.append(f"视频+音频")
                                    elif vcodec != 'none':
                                        quality_parts.append("仅视频")
                                    elif acodec != 'none':
                                        quality_parts.append("仅音频")
                                    
                                    # 添加格式备注
                                    if format_note:
                                        quality_parts.append(format_note)
                                    
                                    # 构建最终的质量描述
                                    if quality_parts:
                                        quality = " ".join(quality_parts) + f" ({container})"
                                    else:
                                        quality = f"{format_id} ({container})"
                                    
                                    streams[format_id] = {
                                        'quality': quality,
                                        'container': container,
                                        'size': filesize,
                                        'format': format_id,
                                        'height': height,
                                        'width': width,
                                        'fps': fps,
                                        'vcodec': vcodec,
                                        'acodec': acodec
                                    }
                                
                                # 如果没有格式信息，添加默认选项
                                if not streams:
                                    streams['best'] = {
                                        'quality': '最佳质量',
                                        'container': 'mp4',
                                        'size': 0,
                                        'format': 'best'
                                    }
                                
                                # 构建视频信息
                                self.video_info = {
                                    'title': title,
                                    'site': site,
                                    'streams': streams,
                                    'source': 'yt-dlp'  # 标记数据来源
                                }
                                
                                self.root.after(0, self._update_video_info)
                                self.root.after(0, lambda: self.status_var.set("视频信息获取成功 (使用yt-dlp)"))
                                self.root.after(0, lambda: self.fetch_btn.config(state="normal"))
                                return
                                
                        except subprocess.TimeoutExpired:
                            print("yt-dlp超时")
                        except FileNotFoundError:
                            print("未找到yt-dlp命令")
                        except Exception as ytdlp_error:
                            print(f"yt-dlp失败: {ytdlp_error}")
                    
                    # 原有的错误处理逻辑
                    if "not supported" in error_msg.lower() or "unsupported" in error_msg.lower():
                        # 网站不支持的错误
                        if retry_count < self.max_retries - 1:
                            retry_count += 1
                            time.sleep(2)  # 等待2秒后重试
                            continue
                        else:
                            raise Exception(f"该网站暂不支持\n\n建议：\n1. 更新you-get到最新版本\n2. 检查URL格式是否正确\n3. 尝试使用yt-dlp工具")
                    elif "network" in error_msg.lower() or "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                        # 网络错误，重试
                        if retry_count < self.max_retries - 1:
                            retry_count += 1
                            time.sleep(3)  # 网络错误等待更长时间
                            continue
                        else:
                            raise Exception(f"网络连接问题\n\n建议：\n1. 检查网络连接\n2. 启用代理设置\n3. 稍后重试")
                    elif "403" in error_msg or "forbidden" in error_msg.lower():
                        raise Exception(f"访问被拒绝\n\n可能原因：\n1. 视频需要登录观看\n2. 存在地区限制\n3. 网站反爬虫机制")
                    elif "404" in error_msg or "not found" in error_msg.lower():
                        raise Exception(f"视频不存在\n\n请检查：\n1. URL是否正确\n2. 视频是否已被删除\n3. 是否为私有视频")
                    else:
                        raise Exception(f"获取视频信息失败: {error_msg}")
            
            except FileNotFoundError:
                last_error = Exception("未找到you-get命令，请确保已正确安装you-get")
                break  # 不需要重试
            except Exception as e:
                last_error = e
                retry_count += 1
                
                # 如果还有重试机会，等待一段时间后重试
                if retry_count < self.max_retries:
                    time.sleep(2)
        
        # 所有重试都失败了
        error_msg = str(last_error) if last_error else "未知错误"
        
        # 构建详细的错误信息
        detailed_error = f"获取视频信息失败 (已重试 {self.max_retries} 次)\n\n{error_msg}"
        
        # 添加通用建议
        if "网络" in error_msg or "连接" in error_msg or "timeout" in error_msg.lower():
            detailed_error += "\n\n通用解决方案：\n1. 检查网络连接\n2. 尝试启用代理\n3. 稍后重试\n4. 检查防火墙设置"
        elif "不支持" in error_msg:
            detailed_error += "\n\n通用解决方案：\n1. 更新you-get到最新版本\n2. 检查URL格式\n3. 尝试其他下载工具"
        else:
            detailed_error += "\n\n通用解决方案：\n1. 检查URL是否正确\n2. 确认视频是否可正常访问\n3. 尝试使用代理\n4. 更新you-get版本"
        
        self.root.after(0, lambda: messagebox.showerror("获取失败", detailed_error))
        self.root.after(0, lambda: self.status_var.set(f"获取失败 (重试{self.max_retries}次)"))
        self.root.after(0, lambda: self.fetch_btn.config(state="normal"))
    
    def _update_video_info(self):
        """更新视频信息显示"""
        if not self.video_info:
            self.status_var.set("获取视频信息失败")
            self.fetch_btn.config(state="normal")
            return
        
        try:
            # 更新基本信息
            title = self.video_info.get('title', '未知标题')
            if title and title != '未知标题':
                # 清理标题中的特殊字符
                title = re.sub(r'[\r\n\t]', ' ', title).strip()
                title = re.sub(r'\s+', ' ', title)  # 合并多个空格
            self.title_var.set(title)
            
            site = self.video_info.get('site', '未知网站')
            if site and site != '未知网站':
                site = site.strip()
            self.site_var.set(site)
            
            # 计算总大小
            streams = self.video_info.get('streams', {})
            total_size = 0
            available_formats = []
            video_formats = []
            audio_formats = []
            
            # 分析可用的流格式
            for stream_id, stream_info in streams.items():
                size = stream_info.get('size', 0)
                if isinstance(size, (int, float)) and size > 0:
                    total_size += size
                
                # 构建格式描述
                quality = stream_info.get('quality', stream_id)
                container = stream_info.get('container', 'unknown')
                
                # 改进格式描述的构建
                if quality == stream_id:
                    # 如果quality就是stream_id，尝试构建更友好的描述
                    if 'hd' in stream_id.lower():
                        format_desc = f"高清 ({container})"
                    elif 'sd' in stream_id.lower():
                        format_desc = f"标清 ({container})"
                    elif 'audio' in stream_id.lower():
                        format_desc = f"音频 ({container})"
                    else:
                        format_desc = f"{stream_id} ({container})"
                else:
                    format_desc = quality
                
                # 添加文件大小信息
                if size > 0:
                    size_mb = size / (1024 * 1024)
                    if size_mb > 1024:
                        size_gb = size_mb / 1024
                        format_desc += f" - {size_gb:.2f}GB"
                    else:
                        format_desc += f" - {size_mb:.1f}MB"
                
                # 分类视频和音频格式
                if 'audio' in quality.lower() or 'audio' in stream_id.lower():
                    audio_formats.append((format_desc, stream_id))
                else:
                    video_formats.append((format_desc, stream_id))
                
                available_formats.append((format_desc, stream_id))
            
            # 显示总大小
            if total_size > 0:
                size_mb = total_size / (1024 * 1024)
                if size_mb > 1024:
                    size_gb = size_mb / 1024
                    self.size_var.set(f"{size_gb:.2f} GB")
                else:
                    self.size_var.set(f"{size_mb:.1f} MB")
            else:
                self.size_var.set("未知大小")
            
            # 存储格式信息
            self.formats = available_formats
            self.video_formats = video_formats
            self.audio_formats = audio_formats
            
            # 更新格式选项
            self._update_format_combo()
            
            self.status_var.set("视频信息获取成功")
            self.download_btn.config(state="normal")
            
        except Exception as e:
            messagebox.showerror("错误", f"解析视频信息时出错: {str(e)}")
            self.status_var.set("解析视频信息失败")
        
        finally:
            self.fetch_btn.config(state="normal")
    
    def _update_format_combo(self):
        """根据下载类型更新格式选择框"""
        if self.download_type.get() == "audio":
            # 音频模式：显示音频预设和可用音频格式
            audio_presets = [
                "最佳音质",
                "高音质 (320kbps)", 
                "标准音质 (192kbps)",
                "普通音质 (128kbps)",
                "低音质 (96kbps)"
            ]
            
            format_names = audio_presets.copy()
            
            # 如果有可用的音频格式，添加分隔符和具体格式
            if hasattr(self, 'audio_formats') and self.audio_formats:
                format_names.extend(["--- 可用音频格式 ---"])
                format_names.extend([fmt[0] for fmt in self.audio_formats])
            elif hasattr(self, 'formats') and self.formats:
                format_names.extend(["--- 可用格式 ---"])
                format_names.extend([fmt[0] for fmt in self.formats])
            
            self.format_combo['values'] = format_names
        else:
            # 视频模式：显示更全面的视频质量选项
            video_presets = [
                "最佳质量",
                "8K (4320p)",
                "4K (2160p)", 
                "2K (1440p)",
                "全高清 (1080p)",
                "高清 (720p)",
                "标清 (480p)",
                "低清 (360p)",
                "最低质量"
            ]
            
            format_names = video_presets.copy()
            
            # 如果有可用的视频格式，添加分隔符和具体格式
            if hasattr(self, 'video_formats') and self.video_formats:
                format_names.extend(["--- 可用视频格式 ---"])
                format_names.extend([fmt[0] for fmt in self.video_formats])
            elif hasattr(self, 'formats') and self.formats:
                format_names.extend(["--- 可用格式 ---"])
                format_names.extend([fmt[0] for fmt in self.formats])
            
            self.format_combo['values'] = format_names
        
        # 设置默认选择
        if len(self.format_combo['values']) > 0:
            self.format_combo.current(0)
    
    def start_download(self):
        """开始下载"""
        if not self.video_info:
            messagebox.showerror("错误", "请先获取视频信息")
            return
        
        url = self.url_entry.get().strip()
        save_path = self.save_path_var.get().strip()
        
        if not save_path:
            messagebox.showerror("错误", "请选择保存位置")
            return
        
        if not os.path.exists(save_path):
            try:
                os.makedirs(save_path)
            except Exception as e:
                messagebox.showerror("错误", f"创建保存目录失败: {str(e)}")
                return
        
        # 立即响应用户操作，提升响应速度
        self.download_btn.config(state="disabled")
        self.progress_var.set(0)
        self.status_var.set("正在启动下载...")
        self.root.update()  # 强制更新界面
        
        # 设置下载状态
        self._downloading = True
        
        # 准备下载选项
        options = {
            "merge": True
        }
        
        # 在新线程中下载
        threading.Thread(target=self._download_video_thread, args=(url, save_path, options), daemon=True).start()
    
    def _download_video_thread(self, url, save_path, options):
        """在线程中执行下载"""
        self._downloading = True
        self.download_btn.config(state="disabled")
        self.status_var.set("准备下载...")
        self.progress_var.set(0)
        
        # 准备下载参数
        download_params = {
            'output_dir': save_path,
            'merge': options.get("merge", True),
            'caption': self.download_subtitle.get(),
            'playlist': self.download_playlist.get(),
            'skip_existing_file_size_check': self.skip_existing.get(),
            'auto_rename': self.auto_rename.get(),
        }
        
        # 设置代理
        if self.use_proxy.get():
            proxy_addr = self.proxy_entry.get().strip()
            if proxy_addr:
                proxy_type = self.proxy_type.get()
                proxy_url = f"{proxy_type}://{proxy_addr}"
                try:
                    you_get.common.set_proxy(proxy_url)
                    self.root.after(0, lambda: self.status_var.set(f"使用代理: {proxy_addr}"))
                except Exception as e:
                    self.root.after(0, lambda: self.status_var.set(f"代理设置失败: {str(e)}"))
        else:
            # 清除代理设置
            try:
                you_get.common.set_proxy(None)
            except:
                pass
        
        # 设置输出格式
        output_format = self.output_format_var.get()
        if output_format != "auto":
            download_params['format'] = output_format
        
        # 设置并发连接数
        try:
            connections = int(self.connections.get())
            if connections > 1:
                download_params['concurrent_fragments'] = connections
        except ValueError:
            pass  # 使用默认值
        
        # 处理下载类型和质量选择
        if self.download_type.get() == "audio":
            download_params['audio_only'] = True
            
            # 添加音频格式转换
            audio_format = self.audio_format_var.get()
            download_params['audio_format'] = audio_format
            
            # 处理音质选择
            quality_option = self.format_combo.get()
            if "---" not in quality_option:  # 跳过分隔符
                audio_presets = {
                    "最佳音质": None,  # 使用默认最佳音质
                    "高音质 (320kbps)": 0,
                    "标准音质 (192kbps)": 2,
                    "普通音质 (128kbps)": 4,
                    "低音质 (96kbps)": 6
                }
                
                if quality_option in audio_presets:
                    quality_value = audio_presets[quality_option]
                    if quality_value is not None:
                        download_params['audio_quality'] = quality_value
                else:
                    # 查找对应的流ID
                    for fmt_desc, stream_id in getattr(self, 'audio_formats', []):
                        if fmt_desc == quality_option:
                            download_params['format'] = stream_id
                            break
        else:
            # 视频质量选择
            quality_option = self.format_combo.get()
            if "---" not in quality_option:  # 跳过分隔符
                video_presets = {
                    "最佳质量": None,  # 使用默认最佳质量
                    "8K (4320p)": 'best[height<=4320]',
                    "4K (2160p)": 'best[height<=2160]', 
                    "2K (1440p)": 'best[height<=1440]',
                    "全高清 (1080p)": 'best[height<=1080]',
                    "高清 (720p)": 'best[height<=720]',
                    "标清 (480p)": 'best[height<=480]',
                    "低清 (360p)": 'best[height<=360]',
                    "最低质量": 'worst'
                }
                
                if quality_option in video_presets:
                    format_value = video_presets[quality_option]
                    if format_value is not None:
                        download_params['format'] = format_value
                else:
                    # 查找对应的流ID
                    for fmt_desc, stream_id in getattr(self, 'video_formats', []):
                        if fmt_desc == quality_option:
                            download_params['format'] = stream_id
                            break
        
        try:
            # 检查视频信息来源，选择相应的下载工具
            if self.video_info.get('source') == 'yt-dlp':
                # 使用yt-dlp下载
                self._download_with_ytdlp(url, save_path, download_params)
            else:
                # 使用you-get下载
                self._download_with_youget(url, save_path, download_params)
            
            # 下载完成
            self.root.after(0, lambda: self.status_var.set("下载完成"))
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: messagebox.showinfo("下载完成", 
                                                        f"视频已成功下载到:\n{save_path}"))
        
        except Exception as e:
            error_msg = f"下载过程中出错: {str(e)}\n\n💡 建议：\n• 检查URL是否正确\n• 确认网络连接\n• 查看支持网站列表\n• 检查you-get是否正确安装"
            self.root.after(0, lambda: messagebox.showerror("下载失败", error_msg))
            self.root.after(0, lambda: self.status_var.set("下载失败"))
        
        finally:
            self._downloading = False
            self._current_process = None
            self.root.after(0, lambda: self.download_btn.config(state="normal"))
            self.root.after(0, lambda: self.fetch_btn.config(state="normal"))
    
    def download_video(self):
        """下载视频的快捷方法"""
        self.start_download()
    
    def _download_thread(self, url, save_path):
        """旧的下载方法，重定向到新的下载方法"""
        options = {"merge": True}
        self._download_video_thread(url, save_path, options)
    
    def _download_with_youget(self, url, save_path, download_params):
        """使用you-get下载"""
        # 创建自定义输出捕获器来监控下载进度
        class ProgressCapture(io.StringIO):
            def __init__(self, app):
                super().__init__()
                self.app = app
                self.last_update = time.time()
                self.progress_pattern = re.compile(r'(\d+)%')
                self.speed_pattern = re.compile(r'(\d+\.\d+\s*[KMG]?B/s)')
                self.eta_pattern = re.compile(r'ETA:\s*(\d+:\d+)')
            
            def write(self, text):
                super().write(text)
                
                # 限制UI更新频率，避免过于频繁
                current_time = time.time()
                if current_time - self.last_update < 0.1:  # 最多每100ms更新一次
                    return
                
                self.last_update = current_time
                
                # 解析进度
                progress_match = self.progress_pattern.search(text)
                if progress_match:
                    progress = int(progress_match.group(1))
                    self.app.root.after(0, lambda p=progress: self.app.progress_var.set(p))
                
                # 解析速度
                speed_match = self.speed_pattern.search(text)
                eta_match = self.eta_pattern.search(text)
                
                status_text = "下载中"
                if speed_match:
                    status_text += f" - {speed_match.group(1)}"
                
                if eta_match:
                    self.app.root.after(0, lambda e=eta_match.group(1): self.app.eta_var.set(f"剩余时间: {e}"))
                
                self.app.root.after(0, lambda s=status_text: self.app.status_var.set(s))
        
        # 创建进度捕获器
        progress_capture = ProgressCapture(self)
        
        # 重定向输出以捕获进度
        with redirect_stdout(progress_capture), redirect_stderr(progress_capture):
            # 执行下载
            you_get.common.any_download(url, **download_params)
    
    def _download_with_ytdlp(self, url, save_path, download_params):
        """使用yt-dlp下载"""
        import subprocess
        
        # 构建yt-dlp命令
        cmd = ['yt-dlp']
        
        # 添加输出目录
        cmd.extend(['-o', os.path.join(save_path, '%(title)s.%(ext)s')])
        
        # 处理格式选择
        format_option = download_params.get('format')
        if format_option:
            cmd.extend(['-f', format_option])
        
        # 处理代理设置
        if self.use_proxy.get() and self.proxy_entry.get().strip():
            proxy_addr = self.proxy_entry.get().strip()
            proxy_type = self.proxy_type.get()
            proxy_url = f"{proxy_type}://{proxy_addr}"
            cmd.extend(['--proxy', proxy_url])
        
        # 处理字幕下载
        if download_params.get('caption', False):
            cmd.extend(['--write-subs', '--write-auto-subs'])
        
        # 处理音频下载
        if download_params.get('audio_only', False):
            cmd.extend(['-x'])
            audio_format = download_params.get('audio_format', 'mp3')
            cmd.extend(['--audio-format', audio_format])
        
        # 添加进度显示
        cmd.extend(['--progress'])
        
        # 添加URL
        cmd.append(url)
        
        self.root.after(0, lambda: self.status_var.set("使用yt-dlp下载中..."))
        
        # 执行命令并捕获输出
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        self._current_process = process
        
        # 实时读取输出
        progress_pattern = re.compile(r'(\d+\.\d+)%')
        speed_pattern = re.compile(r'at\s+([\d\.]+\s*[KMG]?iB/s)')
        
        for line in iter(process.stdout.readline, ''):
            if not self._downloading:
                process.terminate()
                break
            
            # 解析进度
            progress_match = progress_pattern.search(line)
            if progress_match:
                progress = float(progress_match.group(1))
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
            
            # 解析速度
            speed_match = speed_pattern.search(line)
            if speed_match:
                speed = speed_match.group(1)
                self.root.after(0, lambda s=speed: self.status_var.set(f"下载中 - {s}"))
        
        process.wait()
        
        if process.returncode != 0 and self._downloading:
            raise Exception(f"yt-dlp下载失败，退出码: {process.returncode}")


def main():
    # 检查you-get模块是否已安装
    try:
        import you_get
    except ImportError:
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        messagebox.showerror("错误", 
                           "未找到you-get模块！\n\n请先安装you-get:\n" +
                           "pip install you-get\n\n" +
                           "或者:\n" +
                           "pip3 install you-get")
        return
    
    root = tk.Tk()
    app = YouGetDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()