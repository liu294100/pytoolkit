#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
富途牛牛帮助中心深度爬虫主启动脚本
Futu Help Center Deep Crawler Main Entry Point

使用方法:
1. GUI模式: python main.py
2. 命令行模式: python main.py --cli
3. 帮助信息: python main.py --help
"""

import sys
import os
import argparse
from typing import List

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def run_gui():
    """运行GUI模式"""
    try:
        import tkinter as tk
        from src.gui.main_window import FutuCrawlerGUI
        
        print("启动GUI界面...")
        root = tk.Tk()
        
        # 设置主题
        try:
            from tkinter import ttk
            style = ttk.Style()
            style.theme_use('clam')
        except:
            pass
        
        app = FutuCrawlerGUI(root)
        
        # 设置窗口关闭事件
        def on_closing():
            if app.is_crawling:
                from tkinter import messagebox
                if messagebox.askokcancel("退出", "爬取正在进行中，确定要退出吗？"):
                    app.stop_crawling()
                    root.destroy()
            else:
                root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()
        
    except ImportError as e:
        print(f"GUI依赖缺失: {e}")
        print("请安装tkinter: pip install tk")
        sys.exit(1)
    except Exception as e:
        print(f"GUI启动失败: {e}")
        sys.exit(1)

def run_cli(args):
    """运行命令行模式"""
    try:
        from src.core.deep_crawler import DeepFutuDocCrawler
        
        # 默认URL列表
        default_urls = [
            "https://support.futunn.com/categories/2186",  # 基础知识入门
            "https://support.futunn.com/categories/2185",  # 市场介绍
            "https://support.futunn.com/categories/2187",  # 客户端功能
            "https://support.futunn.com/hant/categories/2186",  # 基础知识入门(繁体)
            "https://support.futunn.com/hant/categories/2185",  # 市场介绍(繁体)
            "https://support.futunn.com/hant/categories/2187",  # 客户端功能(繁体)
            "https://support.futunn.com/en/categories/2186",  # Getting started
            "https://support.futunn.com/en/categories/2185",  # Market Introduction
            "https://support.futunn.com/en/categories/2187",  # App Features
        ]
        
        urls = args.urls if args.urls else default_urls
        
        print(f"开始深度爬取，目标URL数量: {len(urls)}")
        print(f"参数: 最大深度={args.max_depth}, 每分类最大文章数={args.max_articles}")
        print(f"输出目录: {args.output_dir}")
        print("-" * 50)
        
        # 创建爬虫实例
        crawler = DeepFutuDocCrawler(
            max_workers=args.max_workers,
            delay_range=(args.delay_min, args.delay_max)
        )
        
        # 运行深度爬取
        docs_data, stats = crawler.run_deep_crawl(
            urls=urls,
            max_depth=args.max_depth,
            max_articles_per_category=args.max_articles
        )
        
        # 保存文档
        if args.output_dir != 'docs_deep':
            crawler.save_documents(args.output_dir)
        
        # 显示统计信息
        total_docs = sum(len(docs) for docs in docs_data.values())
        print("\n" + "=" * 50)
        print("爬取完成！")
        print(f"总文档数: {total_docs}")
        print(f"成功爬取: {stats['successful_crawls']}")
        print(f"失败爬取: {stats['failed_crawls']}")
        print(f"文档已保存到: {args.output_dir}")
        
        # 按语言显示统计
        for lang, docs in docs_data.items():
            if docs:
                print(f"  {lang}: {len(docs)} 篇文档")
        
    except Exception as e:
        print(f"爬取失败: {e}")
        sys.exit(1)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="富途牛牛帮助中心深度爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  GUI模式:     python main.py
  命令行模式:   python main.py --cli
  自定义参数:   python main.py --cli --max-depth 2 --max-articles 30
  指定URL:     python main.py --cli --urls https://support.futunn.com/categories/2186
        """
    )
    
    parser.add_argument('--cli', action='store_true', help='使用命令行模式')
    parser.add_argument('--urls', nargs='+', help='要爬取的URL列表')
    parser.add_argument('--max-depth', type=int, default=3, help='最大爬取深度 (默认: 3)')
    parser.add_argument('--max-articles', type=int, default=50, help='每分类最大文章数 (默认: 50)')
    parser.add_argument('--max-workers', type=int, default=3, help='并发线程数 (默认: 3)')
    parser.add_argument('--delay-min', type=float, default=1.0, help='最小延迟秒数 (默认: 1.0)')
    parser.add_argument('--delay-max', type=float, default=3.0, help='最大延迟秒数 (默认: 3.0)')
    parser.add_argument('--output-dir', default='docs_deep', help='输出目录 (默认: docs_deep)')
    
    args = parser.parse_args()
    
    # 验证参数
    if args.delay_min >= args.delay_max:
        print("错误: 最小延迟必须小于最大延迟")
        sys.exit(1)
    
    if args.max_depth < 1 or args.max_depth > 5:
        print("错误: 最大深度必须在1-5之间")
        sys.exit(1)
    
    # 选择运行模式
    if args.cli:
        run_cli(args)
    else:
        run_gui()

if __name__ == '__main__':
    main()