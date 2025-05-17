import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import re
import threading
import time
from datetime import timedelta
import yt_dlp

class YoutubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube 下载器")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        
        # 设置样式
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Arial", 10))
        self.style.configure("TLabel", font=("Arial", 10))
        self.style.configure("TRadiobutton", font=("Arial", 10))
        self.style.configure("TCheckbutton", font=("Arial", 10))
        
        # 设置网络参数
        self.max_retries = 3  # 最大重试次数
        self.timeout = 30     # 超时时间（秒）
        
        # 创建主框架
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # URL 输入区域
        url_frame = ttk.Frame(main_frame)
        url_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(url_frame, text="YouTube URL:").pack(side=tk.LEFT, padx=5)
        self.url_entry = ttk.Entry(url_frame)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.fetch_btn = ttk.Button(url_frame, text="获取信息", command=self.fetch_video_info)
        self.fetch_btn.pack(side=tk.LEFT, padx=5)
        
        # 视频信息区域
        info_frame = ttk.LabelFrame(main_frame, text="视频信息", padding="5")
        info_frame.pack(fill=tk.X, pady=5)
        
        self.title_var = tk.StringVar(value="")
        ttk.Label(info_frame, text="标题:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, textvariable=self.title_var, wraplength=600).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        self.duration_var = tk.StringVar(value="")
        ttk.Label(info_frame, text="时长:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, textvariable=self.duration_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
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
        
        # 清晰度/质量选择
        format_frame = ttk.Frame(options_frame)
        format_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(format_frame, text="质量选择:").pack(side=tk.LEFT, padx=5)
        self.format_combo = ttk.Combobox(format_frame, width=40, state="readonly")
        self.format_combo.pack(side=tk.LEFT, padx=5)
        
        # 代理设置
        proxy_frame = ttk.LabelFrame(options_frame, text="代理设置", padding="5")
        proxy_frame.pack(fill=tk.X, pady=5)
        
        # 代理启用选项
        proxy_enable_frame = ttk.Frame(proxy_frame)
        proxy_enable_frame.pack(fill=tk.X, pady=2)
        
        self.use_proxy = tk.BooleanVar(value=True)  # 默认启用代理
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
        self.proxy_entry.config(state="normal")  # 默认启用状态
        
        # 常用代理配置
        proxy_presets_frame = ttk.Frame(proxy_frame)
        proxy_presets_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(proxy_presets_frame, text="常用配置:").pack(side=tk.LEFT, padx=5)
        presets = [("Clash", "127.0.0.1:7890"), ("ClashVerge", "127.0.0.1:7897"),("V2Ray", "127.0.0.1:10809"), ("自定义", "")]
        
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
        self.format_ids = []
        
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
        
        proxy_type = self.proxy_type.get()
        proxy_addr = self.proxy_entry.get().strip()
        
        if not proxy_addr:
            messagebox.showerror("错误", "请输入代理地址")
            return
        
        # 构建完整的代理URL
        proxy_url = f"{proxy_type}://{proxy_addr}"
        
        # 禁用测试按钮，防止重复点击
        self.test_proxy_btn.config(state="disabled")
        self.status_var.set("正在测试代理连接...")
        
        # 在新线程中测试连接
        threading.Thread(target=self._test_proxy_thread, args=(proxy_url,), daemon=True).start()
    
    def _test_proxy_thread(self, proxy_url):
        """在线程中测试代理连接"""
        try:
            import requests
            start_time = time.time()
            
            # 测试连接YouTube
            try:
                proxies = {"http": proxy_url, "https": proxy_url}
                response = requests.get("https://www.youtube.com", 
                                       proxies=proxies, 
                                       timeout=10)
                
                # 检查响应状态
                if response.status_code == 200:
                    elapsed = time.time() - start_time
                    self.root.after(0, lambda: messagebox.showinfo("成功", 
                                                                f"代理连接成功！\n响应时间: {elapsed:.2f}秒"))
                    self.root.after(0, lambda: self.status_var.set(f"代理测试成功，延迟: {elapsed:.2f}秒"))
                else:
                    self.root.after(0, lambda: messagebox.showwarning("警告", 
                                                                   f"代理连接返回异常状态码: {response.status_code}"))
                    self.root.after(0, lambda: self.status_var.set("代理测试异常"))
            
            except requests.exceptions.ProxyError:
                self.root.after(0, lambda: messagebox.showerror("错误", 
                                                             "代理服务器连接失败，请检查代理地址是否正确或代理服务是否运行"))
                self.root.after(0, lambda: self.status_var.set("代理连接失败"))
            
            except requests.exceptions.ConnectTimeout:
                self.root.after(0, lambda: messagebox.showerror("错误", 
                                                             "连接超时，请检查代理服务器状态或网络连接"))
                self.root.after(0, lambda: self.status_var.set("代理连接超时"))
            
            except requests.exceptions.SSLError:
                self.root.after(0, lambda: messagebox.showerror("错误", 
                                                             "SSL证书验证失败，可能是代理服务器配置问题"))
                self.root.after(0, lambda: self.status_var.set("代理SSL错误"))
            
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", 
                                                             f"测试代理时出现未知错误: {str(e)}"))
                self.root.after(0, lambda: self.status_var.set("代理测试失败"))
        
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
    
    def fetch_video_info(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("错误", "请输入YouTube视频URL")
            return
        
        self.status_var.set("正在获取视频信息...")
        self.fetch_btn.config(state="disabled")
        
        # 在新线程中获取视频信息
        threading.Thread(target=self._fetch_video_info_thread, args=(url,), daemon=True).start()
    
    def check_network_connection(self, url="https://www.youtube.com"):
        """检查网络连接状态"""
        try:
            import socket
            import requests
            # 先检查DNS解析
            try:
                socket.gethostbyname("www.youtube.com")
            except socket.gaierror:
                return False, "DNS解析失败，请检查您的网络连接或DNS设置"
            
            # 检查代理连接
            if self.use_proxy.get():
                proxy = self.proxy_entry.get().strip()
                if proxy:
                    try:
                        proxies = {"http": proxy, "https": proxy}
                        requests.get("https://www.youtube.com", proxies=proxies, timeout=5)
                        return True, "代理连接正常"
                    except requests.exceptions.ProxyError:
                        return False, "代理服务器连接失败，请检查代理地址是否正确或代理服务是否运行"
                    except requests.exceptions.ConnectTimeout:
                        return False, "通过代理连接超时，请检查代理服务器状态"
                    except Exception as e:
                        return False, f"代理连接出现问题: {str(e)}"
            
            # 直接连接测试
            try:
                requests.get(url, timeout=5)
                return True, "网络连接正常"
            except requests.exceptions.ConnectionError:
                return False, "无法连接到YouTube，请检查您的网络连接或考虑使用代理"
            except requests.exceptions.Timeout:
                return False, "连接YouTube超时，网络状况不佳或需要使用代理"
            except Exception as e:
                return False, f"网络连接出现问题: {str(e)}"
        except ImportError:
            # 如果没有requests库，使用更基本的方法
            try:
                socket.create_connection(("www.youtube.com", 80), timeout=5)
                return True, "网络连接正常"
            except Exception as e:
                return False, f"网络连接出现问题: {str(e)}"
    
    def _fetch_video_info_thread(self, url):
        # 首先检查网络连接
        connection_ok, message = self.check_network_connection()
        if not connection_ok:
            self.root.after(0, lambda: messagebox.showerror("网络错误", f"无法连接到YouTube: {message}\n\n建议:\n1. 检查您的网络连接\n2. 确认代理设置正确\n3. 确认代理服务正在运行"))
            self.root.after(0, lambda: self.status_var.set("网络连接失败"))
            self.root.after(0, lambda: self.fetch_btn.config(state="normal"))
            return
        
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:  # 尝试获取视频信息
                retry_msg = f'(重试 {retry_count}/{self.max_retries})' if retry_count > 0 else ''
                self.root.after(0, lambda: self.status_var.set(f"正在获取视频信息...{retry_msg}"))

                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'no_color': True,
                    'socket_timeout': self.timeout,  # 设置超时时间
                }
                
                # 添加代理设置
                if self.use_proxy.get():
                    proxy_addr = self.proxy_entry.get().strip()
                    proxy_type = self.proxy_type.get() # 获取代理类型
                    if proxy_addr:
                        # 确保代理地址包含协议前缀
                        full_proxy_url = f"{proxy_type}://{proxy_addr}"
                        ydl_opts['proxy'] = full_proxy_url
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    self.video_info = ydl.extract_info(url, download=False)
                    
                    # 在主线程中更新UI
                    self.root.after(0, self._update_video_info)
                    return  # 成功获取信息，退出函数
                    
            except Exception as e:
                last_error = e
                retry_count += 1
                
                # 更新状态显示重试信息
                self.root.after(0, lambda count=retry_count: self.status_var.set(f"获取信息失败，准备重试 ({count}/{self.max_retries})..."))
                
                # 如果还有重试机会，等待一段时间后重试
                if retry_count < self.max_retries:
                    time.sleep(2)  # 等待2秒后重试
        
        # 所有重试都失败了
        error_msg = str(last_error) if last_error else "未知错误"
        self.root.after(0, lambda: messagebox.showerror("错误", 
                                                      f"获取视频信息失败 (已重试 {self.max_retries} 次):\n{error_msg}\n\n可能的原因:\n1. 视频不存在或已被删除\n2. 网络连接不稳定\n3. 代理设置不正确或代理服务未运行"))
        self.root.after(0, lambda: self.status_var.set("获取视频信息失败"))
        self.root.after(0, lambda: self.fetch_btn.config(state="normal"))
    
    def _update_video_info(self):
        if not self.video_info:
            self.status_var.set("获取视频信息失败")
            self.fetch_btn.config(state="normal")
            return
        
        # 更新视频信息
        self.title_var.set(self.video_info.get('title', 'Unknown'))
        
        # 格式化时长
        duration = self.video_info.get('duration')
        if duration:
            duration_str = str(timedelta(seconds=int(duration)))
            self.duration_var.set(duration_str)
        else:
            self.duration_var.set("未知")
        
        # 更新格式选项
        self.update_format_options()
        
        self.status_var.set("视频信息获取成功")
        self.fetch_btn.config(state="normal")
        self.download_btn.config(state="normal")
    
    def update_format_options(self):
        if not self.video_info:
            return
        
        self.formats = []
        self.format_ids = []
        
        download_type = self.download_type.get()
        
        if download_type == "video":
            # 视频格式
            for f in self.video_info.get('formats', []):
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':  # 同时有视频和音频的格式
                    format_note = f.get('format_note', '')
                    resolution = f.get('resolution', '')
                    ext = f.get('ext', '')
                    format_id = f.get('format_id', '')
                    
                    format_str = f"{resolution} ({format_note}) [{ext}] - ID: {format_id}"
                    self.formats.append(format_str)
                    self.format_ids.append(format_id)
            
            # 添加最佳质量选项
            self.formats.insert(0, "最佳质量 (自动选择)")
            self.format_ids.insert(0, "best")
        else:  # audio
            # 音频格式
            for f in self.video_info.get('formats', []):
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none':  # 只有音频的格式
                    format_note = f.get('format_note', '')
                    abr = f.get('abr', 0)
                    ext = f.get('ext', '')
                    format_id = f.get('format_id', '')
                    
                    format_str = f"{format_note} {abr}kbps [{ext}] - ID: {format_id}"
                    self.formats.append(format_str)
                    self.format_ids.append(format_id)
            
            # 添加最佳音质选项
            self.formats.insert(0, "最佳音质 (自动选择)")
            self.format_ids.insert(0, "bestaudio")
        
        # 更新下拉框
        self.format_combo['values'] = self.formats
        if self.formats:
            self.format_combo.current(0)
    
    def start_download(self):
        if not self.video_info:
            messagebox.showerror("错误", "请先获取视频信息")
            return
        
        save_path = self.save_path_var.get()
        if not os.path.isdir(save_path):
            messagebox.showerror("错误", "保存位置无效")
            return
        
        # 获取选择的格式
        format_index = self.format_combo.current()
        if format_index < 0:
            messagebox.showerror("错误", "请选择下载格式")
            return
        
        format_id = self.format_ids[format_index]
        
        # 禁用按钮，防止重复点击
        self.download_btn.config(state="disabled")
        self.fetch_btn.config(state="disabled")
        
        # 重置进度条
        self.progress_var.set(0)
        self.status_var.set("准备下载...")
        self.eta_var.set("")
        
        # 在新线程中下载
        threading.Thread(target=self._download_thread, 
                        args=(self.video_info['webpage_url'], format_id, save_path), 
                        daemon=True).start()
    
    def _download_thread(self, url, format_id, save_path):
        try:
            # 准备文件名模板
            outtmpl = os.path.join(save_path, '%(title)s.%(ext)s')
            
            ydl_opts = {
                'format': format_id,
                'outtmpl': outtmpl,
                'progress_hooks': [self._progress_hook],
            }
            
            # 添加代理设置
            if self.use_proxy.get():
                proxy_addr = self.proxy_entry.get().strip()
                proxy_type = self.proxy_type.get() # 获取代理类型
                if proxy_addr:
                    # 确保代理地址包含协议前缀
                    full_proxy_url = f"{proxy_type}://{proxy_addr}"
                    ydl_opts['proxy'] = full_proxy_url
            
            # 如果是仅音频，添加音频后处理器
            if self.download_type.get() == "audio":
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # 下载完成
            self.root.after(0, lambda: self.status_var.set("下载完成"))
            self.root.after(0, lambda: self.eta_var.set(""))
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: messagebox.showinfo("成功", "视频下载完成！"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"下载失败: {str(e)}"))
            self.root.after(0, lambda: self.status_var.set("下载失败"))
        finally:
            # 恢复按钮状态
            self.root.after(0, lambda: self.download_btn.config(state="normal"))
            self.root.after(0, lambda: self.fetch_btn.config(state="normal"))
    
    def _progress_hook(self, d):
        if d['status'] == 'downloading':
            # 计算下载进度
            downloaded_bytes = d.get('downloaded_bytes', 0)
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            
            if total_bytes > 0:
                percent = (downloaded_bytes / total_bytes) * 100
                self.root.after(0, lambda: self.progress_var.set(percent))
            
            # 更新状态信息
            speed = d.get('speed', 0)
            if speed:
                speed_str = self._format_size(speed) + '/s'
            else:
                speed_str = "未知速度"
            
            # 更新剩余时间
            eta = d.get('eta', None)
            if eta is not None:
                eta_str = str(timedelta(seconds=eta))
                self.root.after(0, lambda: self.eta_var.set(f"剩余时间: {eta_str}"))
            
            # 更新状态栏
            if total_bytes > 0:
                downloaded_str = self._format_size(downloaded_bytes)
                total_str = self._format_size(total_bytes)
                status_text = f"下载中: {downloaded_str}/{total_str} ({speed_str})"
            else:
                downloaded_str = self._format_size(downloaded_bytes)
                status_text = f"下载中: {downloaded_str} ({speed_str})"
            
            self.root.after(0, lambda: self.status_var.set(status_text))
    
    def _format_size(self, bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024
        return f"{bytes:.2f} PB"


def main():
    # 检查是否安装了yt-dlp
    try:
        import yt_dlp
    except ImportError:
        print("错误: 未安装yt-dlp库。请使用以下命令安装:")
        print("pip install yt-dlp")
        sys.exit(1)
    
    root = tk.Tk()
    app = YoutubeDownloaderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()