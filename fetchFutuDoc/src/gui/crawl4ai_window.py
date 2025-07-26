#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawl4AI 富途文档爬虫 GUI 界面
Crawl4AI Futu Document Crawler GUI Interface

特性:
- 现代化的用户界面
- 实时爬取进度显示
- Crawl4AI 参数配置
- 异步爬取支持
- 结果预览和导出
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

try:
    from ..core.crawl4ai_crawler import (
        Crawl4AIFutuCrawler,
        Crawl4AISettings,
        run_crawl4ai_crawler
    )
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from core.crawl4ai_crawler import (
        Crawl4AIFutuCrawler,
        Crawl4AISettings,
        run_crawl4ai_crawler
    )

class Crawl4AIFutuGUI:
    """Crawl4AI 富途文档爬虫 GUI 主类"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("富途牛牛帮助中心 - Crawl4AI 优化爬虫")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # 状态变量
        self.is_crawling = False
        self.crawl_task = None
        self.results = []
        self.stats = {}
        
        # 创建界面
        self.create_widgets()
        self.setup_default_values()
        
        # 设置图标（如果存在）
        try:
            self.root.iconbitmap('icon.ico')
        except:
            pass
    
    def create_widgets(self):
        """创建GUI组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(
            main_frame, 
            text="🚀 富途牛牛帮助中心 - Crawl4AI 优化爬虫",
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # URL 配置区域
        self.create_url_section(main_frame, row=1)
        
        # 爬取参数配置区域
        self.create_params_section(main_frame, row=2)
        
        # Crawl4AI 特定参数区域
        self.create_crawl4ai_section(main_frame, row=3)
        
        # 控制按钮区域
        self.create_control_section(main_frame, row=4)
        
        # 进度显示区域
        self.create_progress_section(main_frame, row=5)
        
        # 结果显示区域
        self.create_results_section(main_frame, row=6)
    
    def create_url_section(self, parent, row):
        """创建URL配置区域"""
        url_frame = ttk.LabelFrame(parent, text="📋 URL 配置", padding="10")
        url_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        url_frame.columnconfigure(1, weight=1)
        
        # 预设URL选择
        ttk.Label(url_frame, text="预设URL组:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.preset_var = tk.StringVar(value="all")
        preset_combo = ttk.Combobox(
            url_frame, 
            textvariable=self.preset_var,
            values=[
                "all - 所有语言版本",
                "zh-cn - 简体中文",
                "zh-hk - 繁体中文",
                "en - 英文版本",
                "custom - 自定义URL"
            ],
            state="readonly",
            width=30
        )
        preset_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        preset_combo.bind('<<ComboboxSelected>>', self.on_preset_changed)
        
        # 自定义URL输入
        ttk.Label(url_frame, text="自定义URL:").grid(row=1, column=0, sticky=(tk.W, tk.N), padx=(0, 10), pady=(10, 0))
        
        self.url_text = scrolledtext.ScrolledText(
            url_frame, 
            height=4, 
            width=60,
            wrap=tk.WORD
        )
        self.url_text.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def create_params_section(self, parent, row):
        """创建爬取参数配置区域"""
        params_frame = ttk.LabelFrame(parent, text="⚙️ 爬取参数", padding="10")
        params_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 第一行参数
        row1_frame = ttk.Frame(params_frame)
        row1_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(row1_frame, text="最大深度:").grid(row=0, column=0, padx=(0, 5))
        self.max_depth_var = tk.IntVar(value=2)
        depth_spin = ttk.Spinbox(row1_frame, from_=1, to=5, textvariable=self.max_depth_var, width=10)
        depth_spin.grid(row=0, column=1, padx=(0, 20))
        
        ttk.Label(row1_frame, text="并发数:").grid(row=0, column=2, padx=(0, 5))
        self.max_concurrent_var = tk.IntVar(value=5)
        concurrent_spin = ttk.Spinbox(row1_frame, from_=1, to=20, textvariable=self.max_concurrent_var, width=10)
        concurrent_spin.grid(row=0, column=3, padx=(0, 20))
        
        ttk.Label(row1_frame, text="超时(秒):").grid(row=0, column=4, padx=(0, 5))
        self.timeout_var = tk.IntVar(value=30)
        timeout_spin = ttk.Spinbox(row1_frame, from_=10, to=120, textvariable=self.timeout_var, width=10)
        timeout_spin.grid(row=0, column=5)
        
        # 第二行参数
        row2_frame = ttk.Frame(params_frame)
        row2_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        ttk.Label(row2_frame, text="延迟范围:").grid(row=0, column=0, padx=(0, 5))
        self.delay_min_var = tk.DoubleVar(value=1.0)
        delay_min_spin = ttk.Spinbox(row2_frame, from_=0.1, to=10.0, increment=0.1, textvariable=self.delay_min_var, width=8)
        delay_min_spin.grid(row=0, column=1, padx=(0, 5))
        
        ttk.Label(row2_frame, text="-").grid(row=0, column=2, padx=(0, 5))
        self.delay_max_var = tk.DoubleVar(value=2.0)
        delay_max_spin = ttk.Spinbox(row2_frame, from_=0.1, to=10.0, increment=0.1, textvariable=self.delay_max_var, width=8)
        delay_max_spin.grid(row=0, column=3, padx=(0, 20))
        
        ttk.Label(row2_frame, text="输出目录:").grid(row=0, column=4, padx=(0, 5))
        self.output_dir_var = tk.StringVar(value="docs_crawl4ai")
        output_entry = ttk.Entry(row2_frame, textvariable=self.output_dir_var, width=20)
        output_entry.grid(row=0, column=5, padx=(0, 5))
        
        browse_btn = ttk.Button(row2_frame, text="浏览", command=self.browse_output_dir, width=8)
        browse_btn.grid(row=0, column=6)
    
    def create_crawl4ai_section(self, parent, row):
        """创建 Crawl4AI 特定参数区域"""
        crawl4ai_frame = ttk.LabelFrame(parent, text="🤖 Crawl4AI 特性", padding="10")
        crawl4ai_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 复选框选项
        options_frame = ttk.Frame(crawl4ai_frame)
        options_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.headless_var = tk.BooleanVar(value=True)
        headless_check = ttk.Checkbutton(options_frame, text="无头浏览器模式", variable=self.headless_var)
        headless_check.grid(row=0, column=0, padx=(0, 20), sticky=tk.W)
        
        self.enable_js_var = tk.BooleanVar(value=True)
        js_check = ttk.Checkbutton(options_frame, text="启用JavaScript", variable=self.enable_js_var)
        js_check.grid(row=0, column=1, padx=(0, 20), sticky=tk.W)
        
        self.screenshot_var = tk.BooleanVar(value=False)
        screenshot_check = ttk.Checkbutton(options_frame, text="保存截图", variable=self.screenshot_var)
        screenshot_check.grid(row=0, column=2, padx=(0, 20), sticky=tk.W)
        
        self.wait_images_var = tk.BooleanVar(value=False)
        wait_images_check = ttk.Checkbutton(options_frame, text="等待图片加载", variable=self.wait_images_var)
        wait_images_check.grid(row=0, column=3, sticky=tk.W)
    
    def create_control_section(self, parent, row):
        """创建控制按钮区域"""
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=row, column=0, columnspan=3, pady=(0, 10))
        
        self.start_btn = ttk.Button(
            control_frame, 
            text="🚀 开始爬取", 
            command=self.start_crawling,
            style="Accent.TButton"
        )
        self.start_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.stop_btn = ttk.Button(
            control_frame, 
            text="⏹️ 停止爬取", 
            command=self.stop_crawling,
            state=tk.DISABLED
        )
        self.stop_btn.grid(row=0, column=1, padx=(0, 10))
        
        self.export_btn = ttk.Button(
            control_frame, 
            text="📁 打开结果目录", 
            command=self.open_results_dir,
            state=tk.DISABLED
        )
        self.export_btn.grid(row=0, column=2, padx=(0, 10))
        
        self.clear_btn = ttk.Button(
            control_frame, 
            text="🗑️ 清空日志", 
            command=self.clear_log
        )
        self.clear_btn.grid(row=0, column=3)
    
    def create_progress_section(self, parent, row):
        """创建进度显示区域"""
        progress_frame = ttk.LabelFrame(parent, text="📊 爬取进度", padding="10")
        progress_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(1, weight=1)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            variable=self.progress_var, 
            mode='indeterminate'
        )
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 状态信息
        status_frame = ttk.Frame(progress_frame)
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        self.status_label = ttk.Label(status_frame, text="就绪")
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        self.stats_label = ttk.Label(status_frame, text="")
        self.stats_label.grid(row=0, column=1, sticky=tk.E)
        
        status_frame.columnconfigure(1, weight=1)
    
    def create_results_section(self, parent, row):
        """创建结果显示区域"""
        results_frame = ttk.LabelFrame(parent, text="📋 爬取日志", padding="10")
        results_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(
            results_frame, 
            height=15, 
            wrap=tk.WORD,
            font=('Consolas', 9)
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置主框架的行权重
        parent.rowconfigure(row, weight=1)
    
    def setup_default_values(self):
        """设置默认值"""
        self.on_preset_changed()
    
    def on_preset_changed(self, event=None):
        """预设URL组改变时的处理"""
        preset = self.preset_var.get().split(' - ')[0]
        
        url_sets = {
            'all': [
                "https://support.futunn.com/categories/2186",  # 基础知识入门
                "https://support.futunn.com/categories/2185",  # 市场介绍
                "https://support.futunn.com/categories/2187",  # 客户端功能
                "https://support.futunn.com/hant/categories/2186",  # 基础知识入门(繁体)
                "https://support.futunn.com/hant/categories/2185",  # 市场介绍(繁体)
                "https://support.futunn.com/hant/categories/2187",  # 客户端功能(繁体)
                "https://support.futunn.com/en/categories/2186",  # Getting started
                "https://support.futunn.com/en/categories/2185",  # Market Introduction
                "https://support.futunn.com/en/categories/2187",  # App Features
            ],
            'zh-cn': [
                "https://support.futunn.com/categories/2186",
                "https://support.futunn.com/categories/2185",
                "https://support.futunn.com/categories/2187",
            ],
            'zh-hk': [
                "https://support.futunn.com/hant/categories/2186",
                "https://support.futunn.com/hant/categories/2185",
                "https://support.futunn.com/hant/categories/2187",
            ],
            'en': [
                "https://support.futunn.com/en/categories/2186",
                "https://support.futunn.com/en/categories/2185",
                "https://support.futunn.com/en/categories/2187",
            ]
        }
        
        if preset in url_sets:
            self.url_text.delete(1.0, tk.END)
            self.url_text.insert(1.0, '\n'.join(url_sets[preset]))
    
    def browse_output_dir(self):
        """浏览输出目录"""
        directory = filedialog.askdirectory(
            title="选择输出目录",
            initialdir=self.output_dir_var.get()
        )
        if directory:
            self.output_dir_var.set(directory)
    
    def get_urls(self) -> List[str]:
        """获取URL列表"""
        urls_text = self.url_text.get(1.0, tk.END).strip()
        if not urls_text:
            return []
        
        urls = []
        for line in urls_text.split('\n'):
            url = line.strip()
            if url and url.startswith('http'):
                urls.append(url)
        
        return urls
    
    def validate_params(self) -> bool:
        """验证参数"""
        if self.delay_min_var.get() >= self.delay_max_var.get():
            messagebox.showerror("参数错误", "最小延迟必须小于最大延迟")
            return False
        
        urls = self.get_urls()
        if not urls:
            messagebox.showerror("参数错误", "请输入至少一个有效的URL")
            return False
        
        return True
    
    def log_message(self, message: str, level: str = "INFO"):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        level_emoji = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌"
        }
        
        emoji = level_emoji.get(level, "ℹ️")
        log_entry = f"[{timestamp}] {emoji} {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_status(self, status: str, stats: Optional[Dict] = None):
        """更新状态显示"""
        self.status_label.config(text=status)
        
        if stats:
            stats_text = f"成功: {stats.get('successful_crawls', 0)} | 失败: {stats.get('failed_crawls', 0)} | 总计: {stats.get('total_processed', 0)}"
            self.stats_label.config(text=stats_text)
        
        self.root.update_idletasks()
    
    def start_crawling(self):
        """开始爬取"""
        if not self.validate_params():
            return
        
        self.is_crawling = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.export_btn.config(state=tk.DISABLED)
        
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.start()
        
        self.log_message("🚀 开始 Crawl4AI 爬取任务...", "INFO")
        
        # 在新线程中运行爬取任务
        self.crawl_thread = threading.Thread(target=self.run_crawl_task, daemon=True)
        self.crawl_thread.start()
    
    def run_crawl_task(self):
        """运行爬取任务（在单独线程中）"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 获取参数
            urls = self.get_urls()
            settings = Crawl4AISettings(
                max_concurrent=self.max_concurrent_var.get(),
                delay_range=(self.delay_min_var.get(), self.delay_max_var.get()),
                timeout=self.timeout_var.get(),
                output_dir=self.output_dir_var.get(),
                headless=self.headless_var.get(),
                enable_js=self.enable_js_var.get(),
                screenshot=self.screenshot_var.get(),
                wait_for_images=self.wait_images_var.get()
            )
            
            self.root.after(0, lambda: self.log_message(f"📋 目标URL数量: {len(urls)}", "INFO"))
            self.root.after(0, lambda: self.update_status("正在初始化爬虫..."))
            
            # 运行异步爬取
            results, info = loop.run_until_complete(
                run_crawl4ai_crawler(
                    urls=urls,
                    max_depth=self.max_depth_var.get(),
                    settings=settings
                )
            )
            
            # 保存结果
            self.results = results
            self.stats = info['stats']
            saved_files = info['saved_files']
            
            # 更新UI
            self.root.after(0, lambda: self.on_crawl_completed(saved_files))
            
        except Exception as e:
            self.root.after(0, lambda: self.on_crawl_error(str(e)))
        finally:
            loop.close()
    
    def on_crawl_completed(self, saved_files: Dict):
        """爬取完成时的处理"""
        self.is_crawling = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.export_btn.config(state=tk.NORMAL)
        
        self.progress_bar.stop()
        self.progress_bar.config(mode='determinate', value=100)
        
        self.log_message("🎉 爬取任务完成！", "SUCCESS")
        self.log_message(f"✅ 成功爬取: {self.stats['successful_crawls']} 页面", "SUCCESS")
        self.log_message(f"❌ 失败爬取: {self.stats['failed_crawls']} 页面", "WARNING" if self.stats['failed_crawls'] > 0 else "INFO")
        self.log_message(f"📁 结果已保存到: {self.output_dir_var.get()}", "INFO")
        
        # 显示保存的文件信息
        for lang, file_info in saved_files.items():
            self.log_message(f"📄 {lang.upper()}: {file_info['count']} 篇文档", "INFO")
        
        self.update_status("爬取完成", self.stats)
        
        # 显示完成对话框
        messagebox.showinfo(
            "爬取完成",
            f"爬取任务已完成！\n\n"
            f"成功: {self.stats['successful_crawls']} 页面\n"
            f"失败: {self.stats['failed_crawls']} 页面\n"
            f"结果已保存到: {self.output_dir_var.get()}"
        )
    
    def on_crawl_error(self, error_msg: str):
        """爬取错误时的处理"""
        self.is_crawling = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        self.progress_bar.stop()
        self.progress_bar.config(value=0)
        
        self.log_message(f"❌ 爬取失败: {error_msg}", "ERROR")
        self.update_status("爬取失败")
        
        messagebox.showerror("爬取失败", f"爬取过程中发生错误:\n\n{error_msg}")
    
    def stop_crawling(self):
        """停止爬取"""
        if self.is_crawling:
            self.is_crawling = False
            self.log_message("⏹️ 正在停止爬取...", "WARNING")
            self.update_status("正在停止...")
            
            # 注意：实际的停止逻辑需要在爬虫中实现
            # 这里只是更新UI状态
    
    def open_results_dir(self):
        """打开结果目录"""
        output_dir = self.output_dir_var.get()
        if os.path.exists(output_dir):
            os.startfile(output_dir)
        else:
            messagebox.showwarning("目录不存在", f"输出目录不存在: {output_dir}")
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("🗑️ 日志已清空", "INFO")

# 测试代码
if __name__ == "__main__":
    root = tk.Tk()
    app = Crawl4AIFutuGUI(root)
    root.mainloop()