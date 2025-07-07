#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
富途牛牛帮助中心爬虫GUI主窗口
Futu Help Center Crawler GUI Main Window
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import os
import sys
import json
from datetime import datetime
from typing import Dict, List

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.core.deep_crawler import DeepFutuDocCrawler

class FutuCrawlerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("富途牛牛帮助中心深度爬虫 - Futu Help Center Deep Crawler")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # 设置图标（如果存在）
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # 爬虫实例
        self.crawler = None
        self.crawl_thread = None
        self.is_crawling = False
        
        # 创建界面
        self.create_widgets()
        self.setup_default_urls()
        
    def create_widgets(self):
        """创建界面组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="富途牛牛帮助中心深度爬虫", font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # URL输入区域
        url_frame = ttk.LabelFrame(main_frame, text="目标URL配置", padding="10")
        url_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        url_frame.columnconfigure(0, weight=1)
        
        # URL文本框
        self.url_text = scrolledtext.ScrolledText(url_frame, height=8, width=80)
        self.url_text.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # URL按钮框架
        url_button_frame = ttk.Frame(url_frame)
        url_button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(url_button_frame, text="加载默认URL", command=self.setup_default_urls).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(url_button_frame, text="清空URL", command=self.clear_urls).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(url_button_frame, text="从文件加载", command=self.load_urls_from_file).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(url_button_frame, text="保存到文件", command=self.save_urls_to_file).pack(side=tk.LEFT)
        
        # 爬取参数配置
        config_frame = ttk.LabelFrame(main_frame, text="爬取参数配置", padding="10")
        config_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 第一行参数
        param_frame1 = ttk.Frame(config_frame)
        param_frame1.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(param_frame1, text="最大深度:").pack(side=tk.LEFT)
        self.max_depth_var = tk.StringVar(value="3")
        depth_spinbox = ttk.Spinbox(param_frame1, from_=1, to=5, width=5, textvariable=self.max_depth_var)
        depth_spinbox.pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Label(param_frame1, text="每分类最大文章数:").pack(side=tk.LEFT)
        self.max_articles_var = tk.StringVar(value="50")
        articles_spinbox = ttk.Spinbox(param_frame1, from_=10, to=200, width=8, textvariable=self.max_articles_var)
        articles_spinbox.pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Label(param_frame1, text="并发线程数:").pack(side=tk.LEFT)
        self.max_workers_var = tk.StringVar(value="3")
        workers_spinbox = ttk.Spinbox(param_frame1, from_=1, to=10, width=5, textvariable=self.max_workers_var)
        workers_spinbox.pack(side=tk.LEFT, padx=(5, 20))
        
        # 第二行参数
        param_frame2 = ttk.Frame(config_frame)
        param_frame2.pack(fill=tk.X)
        
        ttk.Label(param_frame2, text="延迟范围(秒):").pack(side=tk.LEFT)
        self.delay_min_var = tk.StringVar(value="1")
        delay_min_spinbox = ttk.Spinbox(param_frame2, from_=0.5, to=5, width=5, textvariable=self.delay_min_var, increment=0.5)
        delay_min_spinbox.pack(side=tk.LEFT, padx=(5, 5))
        
        ttk.Label(param_frame2, text="到").pack(side=tk.LEFT)
        self.delay_max_var = tk.StringVar(value="3")
        delay_max_spinbox = ttk.Spinbox(param_frame2, from_=1, to=10, width=5, textvariable=self.delay_max_var, increment=0.5)
        delay_max_spinbox.pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Label(param_frame2, text="输出目录:").pack(side=tk.LEFT)
        self.output_dir_var = tk.StringVar(value="docs_deep")
        output_entry = ttk.Entry(param_frame2, textvariable=self.output_dir_var, width=20)
        output_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(param_frame2, text="选择", command=self.select_output_dir).pack(side=tk.LEFT)
        
        # 控制按钮
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=3, column=0, columnspan=3, pady=(0, 10))
        
        self.start_button = ttk.Button(control_frame, text="开始深度爬取", command=self.start_crawling, style='Accent.TButton')
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(control_frame, text="停止爬取", command=self.stop_crawling, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_frame, text="清空日志", command=self.clear_log).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="打开输出目录", command=self.open_output_dir).pack(side=tk.LEFT)
        
        # 日志和进度区域
        log_frame = ttk.LabelFrame(main_frame, text="爬取日志和进度", padding="10")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)
        
        # 进度条
        self.progress_var = tk.StringVar(value="就绪")
        progress_label = ttk.Label(log_frame, textvariable=self.progress_var)
        progress_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(log_frame, mode='indeterminate')
        self.progress_bar.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=(0, 5))
        
        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state=tk.DISABLED)
        self.log_text.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def setup_default_urls(self):
        """设置默认URL"""
        default_urls = [
            "# 富途牛牛帮助中心多语言URL配置",
            "# 每行一个URL，以#开头的行为注释",
            "",
            "# 简体中文版本",
            "https://support.futunn.com/categories/2186  # 基础知识入门",
            "https://support.futunn.com/categories/2185  # 市场介绍",
            "https://support.futunn.com/categories/2187  # 客户端功能",
            "",
            "# 繁体中文（香港）版本",
            "https://support.futunn.com/hant/categories/2186  # 基础知识入门",
            "https://support.futunn.com/hant/categories/2185  # 市场介绍",
            "https://support.futunn.com/hant/categories/2187  # 客户端功能",
            "",
            "# 英语版本",
            "https://support.futunn.com/en/categories/2186  # Getting started",
            "https://support.futunn.com/en/categories/2185  # Market Introduction",
            "https://support.futunn.com/en/categories/2187  # App Features",
        ]
        
        self.url_text.delete(1.0, tk.END)
        self.url_text.insert(1.0, "\n".join(default_urls))
    
    def clear_urls(self):
        """清空URL"""
        self.url_text.delete(1.0, tk.END)
    
    def load_urls_from_file(self):
        """从文件加载URL"""
        file_path = filedialog.askopenfilename(
            title="选择URL配置文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.url_text.delete(1.0, tk.END)
                self.url_text.insert(1.0, content)
                self.log_message(f"已从文件加载URL配置: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"加载文件失败: {e}")
    
    def save_urls_to_file(self):
        """保存URL到文件"""
        file_path = filedialog.asksaveasfilename(
            title="保存URL配置文件",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                content = self.url_text.get(1.0, tk.END)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.log_message(f"已保存URL配置到文件: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存文件失败: {e}")
    
    def select_output_dir(self):
        """选择输出目录"""
        dir_path = filedialog.askdirectory(title="选择输出目录")
        if dir_path:
            self.output_dir_var.set(dir_path)
    
    def parse_urls(self) -> List[str]:
        """解析URL文本框中的URL"""
        content = self.url_text.get(1.0, tk.END)
        urls = []
        
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # 移除行内注释
                if '#' in line:
                    line = line.split('#')[0].strip()
                if line.startswith('http'):
                    urls.append(line)
        
        return urls
    
    def log_message(self, message: str):
        """添加日志消息"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # 更新界面
        self.root.update_idletasks()
    
    def clear_log(self):
        """清空日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def open_output_dir(self):
        """打开输出目录"""
        output_dir = self.output_dir_var.get()
        if os.path.exists(output_dir):
            os.startfile(output_dir)
        else:
            messagebox.showwarning("警告", f"输出目录不存在: {output_dir}")
    
    def start_crawling(self):
        """开始爬取"""
        if self.is_crawling:
            return
        
        # 解析URL
        urls = self.parse_urls()
        if not urls:
            messagebox.showwarning("警告", "请输入至少一个有效的URL")
            return
        
        # 获取参数
        try:
            max_depth = int(self.max_depth_var.get())
            max_articles = int(self.max_articles_var.get())
            max_workers = int(self.max_workers_var.get())
            delay_min = float(self.delay_min_var.get())
            delay_max = float(self.delay_max_var.get())
            output_dir = self.output_dir_var.get()
            
            if delay_min >= delay_max:
                messagebox.showerror("错误", "延迟最小值必须小于最大值")
                return
                
        except ValueError as e:
            messagebox.showerror("错误", f"参数格式错误: {e}")
            return
        
        # 更新界面状态
        self.is_crawling = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_bar.start()
        self.progress_var.set("正在初始化爬虫...")
        self.status_var.set("爬取中...")
        
        # 清空日志
        self.clear_log()
        
        # 创建爬虫配置
        from src.core.deep_crawler import CrawlerSettings
        settings = CrawlerSettings(
            max_workers=max_workers,
            delay_range=(delay_min, delay_max),
            timeout=30,
            retries=3
        )
        
        # 设置输出目录
        settings.output_dir = output_dir
        
        # 创建爬虫实例
        self.crawler = DeepFutuDocCrawler(settings=settings)
        
        # 重定向日志到GUI
        self.setup_crawler_logging()
        
        # 在新线程中运行爬虫
        self.crawl_thread = threading.Thread(
            target=self.run_crawler,
            args=(urls, max_depth, max_articles, output_dir),
            daemon=True
        )
        self.crawl_thread.start()
    
    def setup_crawler_logging(self):
        """设置爬虫日志重定向到GUI"""
        class GUILogHandler:
            def __init__(self, gui):
                self.gui = gui
            
            def write(self, message):
                if message.strip():
                    self.gui.log_message(message.strip())
            
            def flush(self):
                pass
        
        # 添加GUI日志处理器
        import logging
        gui_handler = logging.StreamHandler(GUILogHandler(self))
        gui_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        gui_handler.setFormatter(formatter)
        
        # 获取爬虫的logger并添加处理器
        crawler_logger = logging.getLogger('DeepFutuCrawler')
        crawler_logger.addHandler(gui_handler)
    
    def run_crawler(self, urls: List[str], max_depth: int, max_articles: int, output_dir: str):
        """在后台线程中运行爬虫"""
        try:
            self.log_message(f"开始深度爬取，目标URL数量: {len(urls)}")
            self.log_message(f"参数: 最大深度={max_depth}, 每分类最大文章数={max_articles}")
            
            # 更新进度
            self.progress_var.set(f"正在爬取 {len(urls)} 个分类...")
            
            # 运行爬虫
            docs_data, stats = self.crawler.run_deep_crawl(
                urls=urls,
                max_depth=max_depth,
                max_articles_per_category=max_articles
            )
            
            # 保存到指定目录（已在settings中设置）
            self.crawler.save_documents(output_dir)
            
            # 显示完成信息
            total_docs = sum(len(docs) for docs in docs_data.values())
            self.log_message(f"\n=== 爬取完成 ===")
            self.log_message(f"总文档数: {total_docs}")
            self.log_message(f"成功爬取: {stats['successful_crawls']}")
            self.log_message(f"失败爬取: {stats['failed_crawls']}")
            
            self.progress_var.set(f"爬取完成！共获得 {total_docs} 篇文档")
            
            # 显示完成对话框
            self.root.after(0, lambda: messagebox.showinfo(
                "爬取完成",
                f"深度爬取完成！\n\n总文档数: {total_docs}\n成功: {stats['successful_crawls']}\n失败: {stats['failed_crawls']}\n\n文档已保存到: {output_dir}"
            ))
            
        except Exception as e:
            self.log_message(f"爬取过程中出现错误: {e}")
            self.root.after(0, lambda: messagebox.showerror("错误", f"爬取失败: {e}"))
        
        finally:
            # 恢复界面状态
            self.root.after(0, self.crawling_finished)
    
    def stop_crawling(self):
        """停止爬取"""
        if self.is_crawling and self.crawler:
            self.log_message("正在停止爬取...")
            # 这里可以添加停止爬虫的逻辑
            self.is_crawling = False
            self.crawling_finished()
    
    def crawling_finished(self):
        """爬取完成后的界面恢复"""
        self.is_crawling = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_bar.stop()
        self.status_var.set("就绪")
        
        if not self.progress_var.get().startswith("爬取完成"):
            self.progress_var.set("已停止")

def main():
    """主函数"""
    root = tk.Tk()
    
    # 设置主题
    try:
        style = ttk.Style()
        style.theme_use('clam')  # 使用现代主题
    except:
        pass
    
    app = FutuCrawlerGUI(root)
    
    # 设置窗口关闭事件
    def on_closing():
        if app.is_crawling:
            if messagebox.askokcancel("退出", "爬取正在进行中，确定要退出吗？"):
                app.stop_crawling()
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # 启动GUI
    root.mainloop()

if __name__ == '__main__':
    main()