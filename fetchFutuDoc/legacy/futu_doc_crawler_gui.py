#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
富途牛牛帮助中心文档爬虫 - GUI版本
Futu Help Center Documentation Crawler - GUI Version
支持多语言文档生成：简体中文、繁体中文（香港）、英语
Supports multi-language documentation generation: Simplified Chinese, Traditional Chinese (Hong Kong), English
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import json
import os
from futu_doc_crawler import FutuDocCrawler
from datetime import datetime

class FutuDocCrawlerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("富途牛牛帮助中心文档爬虫 - Futu Help Center Doc Crawler")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 设置图标（如果有的话）
        try:
            self.root.iconbitmap('icon.ico')
        except:
            pass
            
        self.crawler = None
        self.is_crawling = False
        
        self.setup_ui()
        self.load_config()
        
    def setup_ui(self):
        """设置用户界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="富途牛牛帮助中心文档爬虫", font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # URL输入区域
        url_frame = ttk.LabelFrame(main_frame, text="目标URL设置", padding="10")
        url_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        url_frame.columnconfigure(0, weight=1)
        
        # URL文本框
        self.url_text = scrolledtext.ScrolledText(url_frame, height=6, width=70)
        self.url_text.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 默认URL
        default_urls = [
            "https://support.futunn.com/categories/2186",
            "https://support.futunn.com/categories/2185"
        ]
        self.url_text.insert(tk.END, "\n".join(default_urls))
        
        # URL操作按钮
        url_btn_frame = ttk.Frame(url_frame)
        url_btn_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        ttk.Button(url_btn_frame, text="添加URL", command=self.add_url).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(url_btn_frame, text="清空", command=self.clear_urls).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(url_btn_frame, text="从文件导入", command=self.import_urls).pack(side=tk.LEFT, padx=(0, 5))
        
        # 设置区域
        settings_frame = ttk.LabelFrame(main_frame, text="爬取设置", padding="10")
        settings_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 最大文章数设置
        ttk.Label(settings_frame, text="每个分类最大文章数:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.max_articles_var = tk.StringVar(value="30")
        max_articles_spinbox = ttk.Spinbox(settings_frame, from_=1, to=200, textvariable=self.max_articles_var, width=10)
        max_articles_spinbox.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # 输出目录设置
        ttk.Label(settings_frame, text="输出目录:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.output_dir_var = tk.StringVar(value="docs")
        output_dir_entry = ttk.Entry(settings_frame, textvariable=self.output_dir_var, width=20)
        output_dir_entry.grid(row=0, column=3, sticky=tk.W, padx=(0, 10))
        ttk.Button(settings_frame, text="浏览", command=self.browse_output_dir).grid(row=0, column=4, sticky=tk.W)
        
        # 语言选择
        lang_frame = ttk.LabelFrame(settings_frame, text="语言设置")
        lang_frame.grid(row=1, column=0, columnspan=5, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.lang_vars = {
            'zh-cn': tk.BooleanVar(value=True),
            'zh-hk': tk.BooleanVar(value=True),
            'en': tk.BooleanVar(value=True)
        }
        
        ttk.Checkbutton(lang_frame, text="简体中文", variable=self.lang_vars['zh-cn']).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Checkbutton(lang_frame, text="繁体中文（香港）", variable=self.lang_vars['zh-hk']).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Checkbutton(lang_frame, text="English", variable=self.lang_vars['en']).pack(side=tk.LEFT)
        
        # 控制按钮
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=3, column=0, columnspan=3, pady=(0, 10))
        
        self.start_btn = ttk.Button(control_frame, text="开始爬取", command=self.start_crawling)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = ttk.Button(control_frame, text="停止爬取", command=self.stop_crawling, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_frame, text="保存配置", command=self.save_config).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="加载配置", command=self.load_config).pack(side=tk.LEFT, padx=(0, 10))
        
        # 进度条
        self.progress_var = tk.StringVar(value="就绪")
        ttk.Label(control_frame, textvariable=self.progress_var).pack(side=tk.LEFT, padx=(20, 0))
        
        # 日志输出区域
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding="10")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 日志控制按钮
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Button(log_btn_frame, text="清空日志", command=self.clear_log).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(log_btn_frame, text="保存日志", command=self.save_log).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(log_btn_frame, text="打开输出目录", command=self.open_output_dir).pack(side=tk.LEFT)
        
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
        
    def add_url(self):
        """添加URL"""
        url = tk.simpledialog.askstring("添加URL", "请输入要爬取的URL:")
        if url:
            current_text = self.url_text.get(1.0, tk.END).strip()
            if current_text:
                self.url_text.insert(tk.END, f"\n{url}")
            else:
                self.url_text.insert(tk.END, url)
                
    def clear_urls(self):
        """清空URL"""
        self.url_text.delete(1.0, tk.END)
        
    def import_urls(self):
        """从文件导入URL"""
        file_path = filedialog.askopenfilename(
            title="选择URL文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    urls = f.read().strip()
                    self.url_text.delete(1.0, tk.END)
                    self.url_text.insert(1.0, urls)
                self.log_message(f"已导入URL文件: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导入文件失败: {e}")
                
    def browse_output_dir(self):
        """浏览输出目录"""
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir_var.set(directory)
            
    def save_config(self):
        """保存配置"""
        config = {
            'urls': self.url_text.get(1.0, tk.END).strip().split('\n'),
            'max_articles': self.max_articles_var.get(),
            'output_dir': self.output_dir_var.get(),
            'languages': {lang: var.get() for lang, var in self.lang_vars.items()}
        }
        
        file_path = filedialog.asksaveasfilename(
            title="保存配置文件",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                self.log_message(f"配置已保存: {file_path}")
                messagebox.showinfo("成功", "配置保存成功！")
            except Exception as e:
                messagebox.showerror("错误", f"保存配置失败: {e}")
                
    def load_config(self):
        """加载配置"""
        # 尝试加载默认配置文件
        default_config_file = 'config.json'
        if os.path.exists(default_config_file):
            try:
                with open(default_config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.apply_config(config)
                self.log_message(f"已加载默认配置: {default_config_file}")
                return
            except:
                pass
                
        # 如果没有默认配置，询问是否加载配置文件
        if messagebox.askyesno("加载配置", "是否要加载配置文件？"):
            file_path = filedialog.askopenfilename(
                title="选择配置文件",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
            )
            
            if file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    self.apply_config(config)
                    self.log_message(f"配置已加载: {file_path}")
                except Exception as e:
                    messagebox.showerror("错误", f"加载配置失败: {e}")
                    
    def apply_config(self, config):
        """应用配置"""
        if 'urls' in config:
            self.url_text.delete(1.0, tk.END)
            self.url_text.insert(1.0, '\n'.join(config['urls']))
            
        if 'max_articles' in config:
            self.max_articles_var.set(str(config['max_articles']))
            
        if 'output_dir' in config:
            self.output_dir_var.set(config['output_dir'])
            
        if 'languages' in config:
            for lang, enabled in config['languages'].items():
                if lang in self.lang_vars:
                    self.lang_vars[lang].set(enabled)
                    
    def clear_log(self):
        """清空日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def save_log(self):
        """保存日志"""
        file_path = filedialog.asksaveasfilename(
            title="保存日志文件",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                log_content = self.log_text.get(1.0, tk.END)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                messagebox.showinfo("成功", "日志保存成功！")
            except Exception as e:
                messagebox.showerror("错误", f"保存日志失败: {e}")
                
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
            
        # 获取URL列表
        urls_text = self.url_text.get(1.0, tk.END).strip()
        if not urls_text:
            messagebox.showwarning("警告", "请输入要爬取的URL！")
            return
            
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        if not urls:
            messagebox.showwarning("警告", "请输入有效的URL！")
            return
            
        # 检查语言选择
        selected_langs = [lang for lang, var in self.lang_vars.items() if var.get()]
        if not selected_langs:
            messagebox.showwarning("警告", "请至少选择一种语言！")
            return
            
        # 获取设置
        try:
            max_articles = int(self.max_articles_var.get())
        except ValueError:
            messagebox.showerror("错误", "最大文章数必须是数字！")
            return
            
        output_dir = self.output_dir_var.get()
        if not output_dir:
            messagebox.showwarning("警告", "请设置输出目录！")
            return
            
        # 开始爬取
        self.is_crawling = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_var.set("正在爬取...")
        
        # 在新线程中运行爬虫
        self.crawl_thread = threading.Thread(
            target=self.run_crawler,
            args=(urls, max_articles, output_dir, selected_langs)
        )
        self.crawl_thread.daemon = True
        self.crawl_thread.start()
        
    def run_crawler(self, urls, max_articles, output_dir, selected_langs):
        """运行爬虫（在后台线程中）"""
        try:
            self.log_message("开始爬取富途牛牛帮助中心文档...")
            self.log_message(f"目标URL数量: {len(urls)}")
            self.log_message(f"每个分类最大文章数: {max_articles}")
            self.log_message(f"输出目录: {output_dir}")
            self.log_message(f"选择的语言: {', '.join(selected_langs)}")
            
            # 创建爬虫实例
            self.crawler = FutuDocCrawler()
            
            # 重写日志方法以输出到GUI
            original_print = print
            def gui_print(*args, **kwargs):
                message = ' '.join(str(arg) for arg in args)
                self.root.after(0, self.log_message, message)
                
            # 临时替换print函数
            import builtins
            builtins.print = gui_print
            
            try:
                # 运行爬虫
                self.crawler.run(urls, max_articles)
                
                # 过滤语言
                filtered_docs = {}
                for lang in selected_langs:
                    if lang in self.crawler.docs_data:
                        filtered_docs[lang] = self.crawler.docs_data[lang]
                        
                self.crawler.docs_data = filtered_docs
                
                # 保存文档
                self.crawler.save_docs(output_dir)
                
                # 统计信息
                total_docs = sum(len(docs) for docs in self.crawler.docs_data.values())
                self.log_message(f"\n=== 爬取完成 ===")
                self.log_message(f"总文档数: {total_docs}")
                for lang, docs in self.crawler.docs_data.items():
                    self.log_message(f"{lang}: {len(docs)} 篇")
                    
                self.root.after(0, self.crawling_finished, True)
                
            finally:
                # 恢复原始print函数
                builtins.print = original_print
                
        except Exception as e:
            self.root.after(0, self.log_message, f"爬取过程中出现错误: {e}")
            self.root.after(0, self.crawling_finished, False)
            
    def stop_crawling(self):
        """停止爬取"""
        self.is_crawling = False
        self.progress_var.set("正在停止...")
        self.log_message("用户请求停止爬取")
        
        # 这里可以添加更复杂的停止逻辑
        if hasattr(self, 'crawl_thread') and self.crawl_thread.is_alive():
            # 注意：Python线程无法强制停止，只能通过标志位控制
            self.log_message("请等待当前操作完成...")
            
    def crawling_finished(self, success):
        """爬取完成回调"""
        self.is_crawling = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        if success:
            self.progress_var.set("爬取完成")
            messagebox.showinfo("成功", "文档爬取完成！")
        else:
            self.progress_var.set("爬取失败")
            messagebox.showerror("错误", "文档爬取失败，请查看日志了解详情。")
            
def main():
    """主函数"""
    root = tk.Tk()
    app = FutuDocCrawlerGUI(root)
    
    # 设置窗口关闭事件
    def on_closing():
        if app.is_crawling:
            if messagebox.askokcancel("退出", "爬取正在进行中，确定要退出吗？"):
                app.stop_crawling()
                root.destroy()
        else:
            root.destroy()
            
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
    
if __name__ == '__main__':
    main()