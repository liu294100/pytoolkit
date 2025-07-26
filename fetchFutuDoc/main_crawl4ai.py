#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
富途牛牛帮助中心 Crawl4AI 优化爬虫主启动脚本
Futu Help Center Crawl4AI Optimized Crawler Main Entry Point

使用方法:
1. GUI模式: python main_crawl4ai.py
2. 命令行模式: python main_crawl4ai.py --cli
3. 帮助信息: python main_crawl4ai.py --help

新特性:
- 基于 Crawl4AI 的高性能异步爬取
- AI 友好的内容提取
- 智能适应性爬取
- 更好的并发控制
- 结构化数据输出
"""

import sys
import os
import argparse
import asyncio
from typing import List
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def check_crawl4ai_installation():
    """检查 Crawl4AI 是否已安装"""
    try:
        import crawl4ai
        return True
    except ImportError:
        print("❌ Crawl4AI 未安装")
        print("请运行以下命令安装:")
        print("pip install crawl4ai aiohttp aiofiles")
        print("\n或者运行: pip install -r requirements.txt")
        return False

def run_gui():
    """运行GUI模式"""
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
        from src.gui.main_window import FutuCrawlerGUI
        
        # 检查 Crawl4AI
        if not check_crawl4ai_installation():
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "依赖缺失", 
                "Crawl4AI 未安装！\n\n请运行: pip install crawl4ai aiohttp aiofiles"
            )
            return
        
        print("启动 Crawl4AI 优化版 GUI 界面...")
        root = tk.Tk()
        
        # 设置主题
        try:
            style = ttk.Style()
            style.theme_use('clam')
        except:
            pass
        
        # 创建增强版GUI（如果存在）
        try:
            from src.gui.crawl4ai_window import Crawl4AIFutuGUI
            app = Crawl4AIFutuGUI(root)
        except ImportError:
            # 回退到原始GUI
            app = FutuCrawlerGUI(root)
            print("使用原始GUI界面（Crawl4AI GUI界面未找到）")
        
        # 设置窗口关闭事件
        def on_closing():
            if hasattr(app, 'is_crawling') and app.is_crawling:
                if messagebox.askokcancel("退出", "爬取正在进行中，确定要退出吗？"):
                    if hasattr(app, 'stop_crawling'):
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

async def run_cli_async(args):
    """异步运行命令行模式"""
    try:
        from src.core.crawl4ai_crawler import (
            Crawl4AIFutuCrawler, 
            Crawl4AISettings,
            run_crawl4ai_crawler
        )
        
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
        
        print("🚀 使用 Crawl4AI 框架进行深度爬取")
        print(f"📊 目标URL数量: {len(urls)}")
        print(f"⚙️  参数: 最大深度={args.max_depth}, 并发数={args.max_concurrent}")
        print(f"📁 输出目录: {args.output_dir}")
        print(f"🎯 启用JS: {args.enable_js}, 无头模式: {args.headless}")
        print("-" * 60)
        
        # 创建 Crawl4AI 设置
        settings = Crawl4AISettings(
            max_concurrent=args.max_concurrent,
            delay_range=(args.delay_min, args.delay_max),
            timeout=args.timeout,
            output_dir=args.output_dir,
            headless=args.headless,
            enable_js=args.enable_js,
            screenshot=args.screenshot,
            wait_for_images=args.wait_for_images
        )
        
        # 运行异步爬取
        results, info = await run_crawl4ai_crawler(
            urls=urls,
            max_depth=args.max_depth,
            settings=settings
        )
        
        # 显示结果统计
        stats = info['stats']
        saved_files = info['saved_files']
        
        print("\n" + "=" * 60)
        print("🎉 爬取完成！")
        print(f"📈 总处理页面: {stats['total_processed']}")
        print(f"✅ 成功爬取: {stats['successful_crawls']}")
        print(f"❌ 失败爬取: {stats['failed_crawls']}")
        print(f"🔗 唯一页面: {stats['unique_pages']}")
        print(f"📝 总内容长度: {stats['total_content_length']:,} 字符")
        
        if stats['start_time'] and stats['end_time']:
            duration = stats['end_time'] - stats['start_time']
            print(f"⏱️  耗时: {duration}")
        
        print(f"\n📁 文档已保存到: {args.output_dir}")
        
        # 按语言显示保存的文件
        for lang, file_info in saved_files.items():
            print(f"  📄 {lang.upper()}: {file_info['count']} 篇文档")
            print(f"    JSON: {Path(file_info['json']).name}")
            print(f"    Markdown: {Path(file_info['markdown']).name}")
        
        # 显示性能指标
        if stats['successful_crawls'] > 0:
            avg_content_length = stats['total_content_length'] / stats['successful_crawls']
            print(f"\n📊 性能指标:")
            print(f"  平均内容长度: {avg_content_length:.0f} 字符/页面")
            if stats['start_time'] and stats['end_time']:
                duration_seconds = duration.total_seconds()
                if duration_seconds > 0:
                    pages_per_second = stats['successful_crawls'] / duration_seconds
                    print(f"  爬取速度: {pages_per_second:.2f} 页面/秒")
        
    except Exception as e:
        print(f"❌ 爬取失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def run_cli(args):
    """运行命令行模式（同步包装）"""
    # 检查 Crawl4AI
    if not check_crawl4ai_installation():
        sys.exit(1)
    
    # 运行异步爬取
    asyncio.run(run_cli_async(args))

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="富途牛牛帮助中心 Crawl4AI 优化爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 使用示例:
  GUI模式:        python main_crawl4ai.py
  命令行模式:      python main_crawl4ai.py --cli
  自定义参数:      python main_crawl4ai.py --cli --max-depth 3 --max-concurrent 8
  启用截图:       python main_crawl4ai.py --cli --screenshot
  指定URL:       python main_crawl4ai.py --cli --urls https://support.futunn.com/categories/2186
  
🔧 Crawl4AI 特性:
  - AI 友好的内容提取
  - 高性能异步爬取
  - 智能适应性爬取
  - 结构化数据输出
  - 支持 JavaScript 渲染
        """
    )
    
    parser.add_argument('--cli', action='store_true', help='使用命令行模式')
    parser.add_argument('--urls', nargs='+', help='要爬取的URL列表')
    parser.add_argument('--max-depth', type=int, default=2, help='最大爬取深度 (默认: 2)')
    parser.add_argument('--max-concurrent', type=int, default=5, help='最大并发数 (默认: 5)')
    parser.add_argument('--delay-min', type=float, default=1.0, help='最小延迟秒数 (默认: 1.0)')
    parser.add_argument('--delay-max', type=float, default=2.0, help='最大延迟秒数 (默认: 2.0)')
    parser.add_argument('--timeout', type=int, default=30, help='请求超时时间 (默认: 30)')
    parser.add_argument('--output-dir', default='docs_crawl4ai', help='输出目录 (默认: docs_crawl4ai)')
    
    # Crawl4AI 特定参数
    parser.add_argument('--headless', action='store_true', default=True, help='使用无头浏览器模式 (默认: True)')
    parser.add_argument('--no-headless', action='store_false', dest='headless', help='禁用无头浏览器模式')
    parser.add_argument('--enable-js', action='store_true', default=True, help='启用JavaScript渲染 (默认: True)')
    parser.add_argument('--no-js', action='store_false', dest='enable_js', help='禁用JavaScript渲染')
    parser.add_argument('--screenshot', action='store_true', help='保存页面截图')
    parser.add_argument('--wait-for-images', action='store_true', help='等待图片加载完成')
    
    args = parser.parse_args()
    
    # 验证参数
    if args.delay_min >= args.delay_max:
        print("❌ 错误: 最小延迟必须小于最大延迟")
        sys.exit(1)
    
    if args.max_depth < 1 or args.max_depth > 5:
        print("❌ 错误: 最大深度必须在1-5之间")
        sys.exit(1)
    
    if args.max_concurrent < 1 or args.max_concurrent > 20:
        print("❌ 错误: 最大并发数必须在1-20之间")
        sys.exit(1)
    
    # 选择运行模式
    if args.cli:
        run_cli(args)
    else:
        run_gui()

if __name__ == '__main__':
    main()