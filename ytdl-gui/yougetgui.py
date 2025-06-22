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
            
            try:
                proxies = {"http": proxy_url, "https": proxy_url}
                response = requests.get("https://www.baidu.com", 
                                       proxies=proxies, 
                                       timeout=10)
                
                if response.status_code == 200:
                    elapsed = time.time() - start_time
                    self.root.after(0, lambda: messagebox.showinfo("成功", 
                                                                f"代理连接成功！\n响应时间: {elapsed:.2f}秒"))
                    self.root.after(0, lambda: self.status_var.set(f"代理测试成功，延迟: {elapsed:.2f}秒"))
                else:
                    self.root.after(0, lambda: messagebox.showwarning("警告", 
                                                                   f"代理连接返回异常状态码: {response.status_code}"))
                    self.root.after(0, lambda: self.status_var.set("代理测试异常"))
            
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
    
    def update_format_options(self):
        """更新格式选项"""
        if self.download_type.get() == "audio":
            self.audio_format_frame.pack(fill=tk.X, pady=5)
            # 音频模式的预设选项
            audio_options = [
                "最佳音质",
                "高音质 (320kbps)",
                "标准音质 (192kbps)",
                "普通音质 (128kbps)",
                "低音质 (96kbps)"
            ]
            self.format_combo['values'] = audio_options
            if len(audio_options) > 0:
                self.format_combo.current(0)
        else:
            self.audio_format_frame.pack_forget()
            # 视频模式的预设选项
            video_options = [
                "最佳质量",
                "超高清 (4K)",
                "高清 (1080p)",
                "标清 (720p)",
                "普清 (480p)",
                "低清 (360p)"
            ]
            self.format_combo['values'] = video_options
            if len(video_options) > 0:
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
                
                # 构建you-get命令
                cmd = ['you-get', '--json', url]
                
                # 添加代理设置
                if self.use_proxy.get():
                    proxy_addr = self.proxy_entry.get().strip()
                    if proxy_addr:
                        proxy_type = self.proxy_type.get()
                        if proxy_type == "http":
                            cmd.extend(['--http-proxy', proxy_addr])
                        elif proxy_type == "socks5":
                            cmd.extend(['--socks-proxy', proxy_addr])
                
                # 执行命令 - 使用系统编码作为备选
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, 
                                           encoding='utf-8', errors='ignore', timeout=self.timeout)
                except UnicodeDecodeError:
                    # 如果UTF-8失败，尝试系统默认编码
                    result = subprocess.run(cmd, capture_output=True, text=True, 
                                           encoding=self.system_encoding, errors='ignore', timeout=self.timeout)
                
                if result.returncode == 0:
                    # 解析JSON输出
                    try:
                        self.video_info = json.loads(result.stdout)
                        self.root.after(0, self._update_video_info)
                        self.root.after(0, lambda: self.status_var.set("视频信息获取成功"))
                        self.root.after(0, lambda: self.fetch_btn.config(state="normal"))
                        return  # 成功获取信息，退出函数
                    except json.JSONDecodeError as e:
                        # 尝试从输出中提取有用信息
                        stderr_lower = result.stderr.lower()
                        if "not supported" in stderr_lower or "unsupported" in stderr_lower:
                            raise Exception(f"该网站暂不支持，请尝试更新you-get版本或使用其他下载工具")
                        elif "network" in stderr_lower or "timeout" in stderr_lower or "connection" in stderr_lower:
                            raise Exception(f"网络连接问题，建议：\n1. 检查网络连接\n2. 启用代理设置\n3. 稍后重试")
                        elif "403" in result.stderr or "forbidden" in stderr_lower:
                            raise Exception(f"访问被拒绝，可能需要登录或该视频有地区限制")
                        elif "404" in result.stderr or "not found" in stderr_lower:
                            raise Exception(f"视频不存在或链接已失效，请检查URL是否正确")
                        else:
                            raise Exception(f"解析视频信息失败: {str(e)}\n\n原始输出: {result.stderr[:200]}")
                else:
                    error_detail = result.stderr.strip()
                    stderr_lower = error_detail.lower()
                    
                    if "not supported" in stderr_lower or "unsupported" in stderr_lower:
                        raise Exception(f"该网站暂不支持\n\n建议：\n1. 更新you-get到最新版本\n2. 检查URL格式是否正确\n3. 尝试使用其他下载工具")
                    elif "network" in stderr_lower or "timeout" in stderr_lower or "connection" in stderr_lower:
                        raise Exception(f"网络连接问题\n\n建议：\n1. 检查网络连接\n2. 启用代理设置\n3. 稍后重试")
                    elif "403" in error_detail or "forbidden" in stderr_lower:
                        raise Exception(f"访问被拒绝\n\n可能原因：\n1. 视频需要登录观看\n2. 存在地区限制\n3. 网站反爬虫机制")
                    elif "404" in error_detail or "not found" in stderr_lower:
                        raise Exception(f"视频不存在\n\n请检查：\n1. URL是否正确\n2. 视频是否已被删除\n3. 是否为私有视频")
                    elif "rate limit" in stderr_lower or "too many" in stderr_lower:
                        raise Exception(f"请求过于频繁，请稍后重试")
                    else:
                        raise Exception(f"获取视频信息失败\n\n错误详情: {error_detail[:300]}")
                    
            except subprocess.TimeoutExpired:
                last_error = Exception("获取视频信息超时")
                retry_count += 1
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
            self.title_var.set(title)
            
            site = self.video_info.get('site', '未知网站')
            self.site_var.set(site)
            
            # 计算总大小
            streams = self.video_info.get('streams', {})
            total_size = 0
            available_formats = []
            
            for stream_id, stream_info in streams.items():
                size = stream_info.get('size', 0)
                if isinstance(size, (int, float)):
                    total_size += size
                
                # 构建格式描述
                quality = stream_info.get('quality', 'unknown')
                container = stream_info.get('container', 'unknown')
                size_mb = size / (1024 * 1024) if size else 0
                
                format_desc = f"{quality} ({container}) - {size_mb:.1f}MB"
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
            
            # 更新格式选项
            if available_formats:
                self.formats = available_formats
                format_names = [fmt[0] for fmt in available_formats]
                
                # 根据下载类型过滤格式
                if self.download_type.get() == "audio":
                    # 音频模式：添加预设选项
                    audio_presets = [
                        "最佳音质",
                        "高音质 (320kbps)", 
                        "标准音质 (192kbps)",
                        "普通音质 (128kbps)"
                    ]
                    format_names = audio_presets + ["--- 可用格式 ---"] + format_names
                else:
                    # 视频模式：添加预设选项
                    video_presets = [
                        "最佳质量",
                        "高清优先",
                        "标清优先"
                    ]
                    format_names = video_presets + ["--- 可用格式 ---"] + format_names
                
                self.format_combo['values'] = format_names
                self.format_combo.current(0)
            
            self.status_var.set("视频信息获取成功")
            self.download_btn.config(state="normal")
            
        except Exception as e:
            messagebox.showerror("错误", f"解析视频信息时出错: {str(e)}")
            self.status_var.set("解析视频信息失败")
        
        finally:
            self.fetch_btn.config(state="normal")
    
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
        
        # 在新线程中下载
        threading.Thread(target=self._download_thread, args=(url, save_path), daemon=True).start()
    
    def _download_thread(self, url, save_path):
        """在线程中执行下载"""
        try:
            # 构建you-get命令
            cmd = ['you-get', '-o', save_path]
            
            # 添加下载类型选项
            if self.download_type.get() == "audio":
                cmd.append('--extract-audio')
                
                # 添加音频格式选项
                audio_format = self.audio_format_var.get()
                if audio_format != "auto":
                    cmd.extend(['--audio-format', audio_format])
            else:
                # 视频模式：确保下载最佳质量的音视频
                output_format = self.output_format_var.get()
                if output_format == "最佳质量":
                    # 让you-get自动选择最佳格式
                    pass
                elif output_format == "高清优先":
                    cmd.extend(['--format', 'mp4'])
                elif output_format == "标清优先":
                    cmd.extend(['--format', 'flv'])
                elif output_format != "auto" and not output_format.startswith("---"):
                    cmd.extend(['--format', output_format])
            
            # 添加字幕选项
            if self.download_subtitle.get():
                cmd.append('--caption')
            
            # 添加播放列表选项
            if self.download_playlist.get():
                cmd.append('--playlist')
            
            # 添加跳过已存在文件选项
            if self.skip_existing.get():
                cmd.append('--skip-existing-file')
            
            # 添加自动重命名选项
            if self.auto_rename.get():
                cmd.append('--auto-rename')
            
            # 添加代理设置
            if self.use_proxy.get():
                proxy_addr = self.proxy_entry.get().strip()
                if proxy_addr:
                    proxy_type = self.proxy_type.get()
                    if proxy_type == "http":
                        cmd.extend(['--http-proxy', proxy_addr])
                    elif proxy_type == "socks5":
                        cmd.extend(['--socks-proxy', proxy_addr])
            
            # 添加并发连接数优化
            try:
                connections = int(self.connections.get())
                if 1 <= connections <= 20:
                    cmd.extend(['--timeout', '120'])  # 增加超时时间
                    if connections > 5:
                        cmd.append('--force')  # 强制下载模式
            except ValueError:
                pass
            
            # 注意：you-get不支持--retry参数，使用内置重试机制
            
            # 添加其他优化参数
            cmd.extend([
                '--debug',         # 启用调试信息
                '--insecure'       # 忽略SSL证书错误
            ])
            
            # 确保音视频合并（默认行为，但明确指定）
            if self.download_type.get() == "video":
                # 视频模式下确保音视频合并
                pass  # you-get默认会合并音视频
            
            # 添加URL
            cmd.append(url)
            
            self.root.after(0, lambda: self.status_var.set("正在下载..."))
            
            # 执行下载命令 - 使用更好的编码处理
            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                         text=True, encoding='utf-8', errors='ignore', 
                                         universal_newlines=True, bufsize=1)
            except UnicodeDecodeError:
                # 如果UTF-8失败，尝试系统默认编码
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                         text=True, encoding=self.system_encoding, errors='ignore', 
                                         universal_newlines=True, bufsize=1)
            
            # 读取输出并更新进度
            output_lines = []
            progress = 0
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    output_lines.append(line)
                    
                    # 解析进度信息
                    if '%' in line:
                        try:
                            import re
                            # 匹配各种进度格式
                            match = re.search(r'(\d+(?:\.\d+)?)%', line)
                            if match:
                                progress = float(match.group(1))
                                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                                self.root.after(0, lambda p=progress: self.status_var.set(f"下载中... {p:.1f}%"))
                        except:
                            pass
                    
                    # 检测下载状态
                    if 'Downloading' in line or '正在下载' in line:
                        self.root.after(0, lambda: self.status_var.set("正在下载视频文件..."))
                    elif 'Merging' in line or '合并' in line:
                        self.root.after(0, lambda: self.status_var.set("正在合并音视频..."))
                    elif 'Converting' in line or '转换' in line:
                        self.root.after(0, lambda: self.status_var.set("正在转换格式..."))
                else:
                    # 模拟进度更新（当没有详细进度信息时）
                    progress = min(progress + 0.5, 95)
                    self.root.after(0, lambda p=progress: self.progress_var.set(p))
                    time.sleep(0.1)
            
            # 等待进程完成
            return_code = process.wait()
            
            if return_code == 0:
                self.root.after(0, lambda: self.progress_var.set(100))
                self.root.after(0, lambda: self.status_var.set("下载完成"))
                
                # 检查是否有分离的音视频文件需要合并
                success_msg = "下载完成！"
                if '--no-merge' in cmd:
                    success_msg += "\n\n💡 提示：音视频文件已分别下载，如需合并请使用 FFmpeg 工具。"
                if self.download_subtitle.get():
                    success_msg += "\n📝 字幕文件已一同下载。"
                
                self.root.after(0, lambda: messagebox.showinfo("下载成功", success_msg))
            else:
                # 分析输出中的错误信息
                full_output = '\n'.join(output_lines)
                error_msg = "下载失败"
                
                if "HTTP Error 403" in full_output or "Forbidden" in full_output:
                    error_msg = "访问被拒绝 (403)\n\n💡 建议：\n• 尝试使用代理服务器\n• 稍后重试\n• 检查视频是否有地区限制"
                elif "HTTP Error 404" in full_output or "Not Found" in full_output:
                    error_msg = "视频不存在 (404)\n\n💡 建议：\n• 检查URL是否正确\n• 视频可能已被删除\n• 确认链接有效性"
                elif "timeout" in full_output.lower() or "超时" in full_output:
                    error_msg = "网络超时\n\n💡 建议：\n• 检查网络连接\n• 增加重试次数\n• 使用代理服务器\n• 选择较低质量"
                elif "not supported" in full_output.lower() or "不支持" in full_output:
                    error_msg = "网站不支持\n\n💡 建议：\n• 查看支持网站列表\n• 确认URL格式正确\n• 尝试其他下载工具"
                elif "Permission denied" in full_output or "权限" in full_output:
                    error_msg = "权限不足\n\n💡 建议：\n• 检查保存路径权限\n• 尝试以管理员身份运行\n• 更改保存目录"
                elif "No space" in full_output or "空间不足" in full_output:
                    error_msg = "磁盘空间不足\n\n💡 建议：\n• 清理磁盘空间\n• 更改保存目录\n• 选择较低质量"
                else:
                    # 显示原始错误信息的最后几行
                    error_lines = [line for line in output_lines if line and not line.startswith('[')]
                    if error_lines:
                        error_msg = f"下载失败\n\n错误信息：\n{error_lines[-1]}"
                
                self.root.after(0, lambda: self.progress_var.set(0))
                self.root.after(0, lambda: self.status_var.set("下载失败"))
                self.root.after(0, lambda: messagebox.showerror("下载失败", error_msg))
        
        except Exception as e:
            error_msg = f"下载过程中出错: {str(e)}\n\n💡 建议：\n• 检查URL是否正确\n• 确认网络连接\n• 查看支持网站列表\n• 检查you-get是否正确安装"
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
            self.root.after(0, lambda: self.status_var.set("下载出错"))
            self.root.after(0, lambda: self.progress_var.set(0))
        
        finally:
            self._downloading = False
            self.root.after(0, lambda: self.download_btn.config(state="normal"))


def main():
    # 检查you-get是否已安装
    try:
        subprocess.run(['you-get', '--version'], capture_output=True, check=True, 
                      encoding='utf-8', errors='ignore')
    except (subprocess.CalledProcessError, FileNotFoundError):
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        messagebox.showerror("错误", 
                           "未找到you-get命令！\n\n请先安装you-get:\n" +
                           "pip install you-get\n\n" +
                           "或者:\n" +
                           "pip3 install you-get")
        return
    
    root = tk.Tk()
    app = YouGetDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()