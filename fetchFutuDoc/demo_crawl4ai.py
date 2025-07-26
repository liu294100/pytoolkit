#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawl4AI 富途文档爬虫演示脚本
Crawl4AI Futu Document Crawler Demo Script

这个脚本演示了如何使用新的 Crawl4AI 框架来爬取富途牛牛帮助文档

运行方式:
1. 基础演示: python demo_crawl4ai.py
2. 自定义URL: python demo_crawl4ai.py --urls https://support.futunn.com/categories/2186
3. 高并发模式: python demo_crawl4ai.py --max-concurrent 10
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.core.crawl4ai_crawler import (
        Crawl4AIFutuCrawler,
        Crawl4AISettings,
        run_crawl4ai_crawler
    )
except ImportError:
    print("❌ 无法导入 Crawl4AI 爬虫模块")
    print("请确保已安装依赖: pip install crawl4ai aiohttp aiofiles")
    sys.exit(1)

async def demo_basic_crawl():
    """基础爬取演示"""
    print("🚀 Crawl4AI 基础爬取演示")
    print("=" * 50)
    
    # 演示URL（简体中文版本）
    demo_urls = [
        "https://support.futunn.com/categories/2186",  # 基础知识入门
        "https://support.futunn.com/categories/2187",  # 客户端功能
    ]
    
    print(f"📋 演示URL数量: {len(demo_urls)}")
    for i, url in enumerate(demo_urls, 1):
        print(f"  {i}. {url}")
    
    # 创建设置
    settings = Crawl4AISettings(
        max_concurrent=3,
        delay_range=(1.0, 2.0),
        timeout=30,
        output_dir='demo_output',
        headless=True,
        enable_js=True
    )
    
    print(f"\n⚙️ 爬取设置:")
    print(f"  最大并发: {settings.max_concurrent}")
    print(f"  延迟范围: {settings.delay_range}")
    print(f"  超时时间: {settings.timeout}秒")
    print(f"  输出目录: {settings.output_dir}")
    print(f"  无头模式: {settings.headless}")
    print(f"  启用JS: {settings.enable_js}")
    
    print("\n🔄 开始爬取...")
    
    try:
        # 运行爬取
        results, info = await run_crawl4ai_crawler(
            urls=demo_urls,
            max_depth=2,
            settings=settings
        )
        
        # 显示结果
        stats = info['stats']
        saved_files = info['saved_files']
        
        print("\n" + "=" * 50)
        print("🎉 爬取完成！")
        print(f"📊 统计信息:")
        print(f"  总处理页面: {stats['total_processed']}")
        print(f"  成功爬取: {stats['successful_crawls']}")
        print(f"  失败爬取: {stats['failed_crawls']}")
        print(f"  唯一页面: {stats['unique_pages']}")
        print(f"  总内容长度: {stats['total_content_length']:,} 字符")
        
        if stats['start_time'] and stats['end_time']:
            duration = stats['end_time'] - stats['start_time']
            print(f"  耗时: {duration}")
        
        print(f"\n📁 保存的文件:")
        for lang, file_info in saved_files.items():
            print(f"  📄 {lang.upper()}: {file_info['count']} 篇文档")
            print(f"    JSON: {Path(file_info['json']).name}")
            print(f"    Markdown: {Path(file_info['markdown']).name}")
        
        # 显示部分结果内容
        print(f"\n📝 内容预览:")
        successful_results = [r for r in results if r.success]
        for i, result in enumerate(successful_results[:3], 1):
            print(f"\n  {i}. {result.title}")
            print(f"     URL: {result.url}")
            print(f"     语言: {result.language}")
            print(f"     内容长度: {len(result.content)} 字符")
            print(f"     链接数量: {len(result.links)}")
            if result.content:
                preview = result.content[:200].replace('\n', ' ')
                print(f"     内容预览: {preview}...")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 爬取失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def demo_custom_crawl(urls, max_concurrent=5, max_depth=2):
    """自定义爬取演示"""
    print("🎯 Crawl4AI 自定义爬取演示")
    print("=" * 50)
    
    print(f"📋 自定义URL数量: {len(urls)}")
    for i, url in enumerate(urls, 1):
        print(f"  {i}. {url}")
    
    # 创建高性能设置
    settings = Crawl4AISettings(
        max_concurrent=max_concurrent,
        delay_range=(0.5, 1.0),  # 更短的延迟
        timeout=45,
        output_dir='custom_output',
        headless=True,
        enable_js=True,
        screenshot=False,
        wait_for_images=False
    )
    
    print(f"\n⚙️ 高性能设置:")
    print(f"  最大并发: {settings.max_concurrent}")
    print(f"  最大深度: {max_depth}")
    print(f"  延迟范围: {settings.delay_range}")
    
    print("\n🚀 开始高性能爬取...")
    
    try:
        results, info = await run_crawl4ai_crawler(
            urls=urls,
            max_depth=max_depth,
            settings=settings
        )
        
        stats = info['stats']
        saved_files = info['saved_files']
        
        print("\n" + "=" * 50)
        print("🎉 自定义爬取完成！")
        print(f"📊 性能统计:")
        print(f"  总处理页面: {stats['total_processed']}")
        print(f"  成功率: {stats['successful_crawls']}/{stats['total_processed']} ({stats['successful_crawls']/max(stats['total_processed'], 1)*100:.1f}%)")
        
        if stats['start_time'] and stats['end_time']:
            duration = stats['end_time'] - stats['start_time']
            duration_seconds = duration.total_seconds()
            if duration_seconds > 0:
                pages_per_second = stats['successful_crawls'] / duration_seconds
                print(f"  爬取速度: {pages_per_second:.2f} 页面/秒")
                print(f"  平均响应时间: {duration_seconds/max(stats['total_processed'], 1):.2f} 秒/页面")
        
        # 按语言分组统计
        lang_stats = {}
        for result in results:
            if result.success:
                lang = result.language
                if lang not in lang_stats:
                    lang_stats[lang] = {'count': 0, 'total_length': 0}
                lang_stats[lang]['count'] += 1
                lang_stats[lang]['total_length'] += len(result.content)
        
        print(f"\n🌐 语言分布:")
        for lang, stats_data in lang_stats.items():
            avg_length = stats_data['total_length'] / stats_data['count']
            print(f"  {lang.upper()}: {stats_data['count']} 页面, 平均长度: {avg_length:.0f} 字符")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 自定义爬取失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Crawl4AI 富途文档爬虫演示",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 演示示例:
  基础演示:     python demo_crawl4ai.py
  自定义URL:    python demo_crawl4ai.py --urls https://support.futunn.com/categories/2186
  高并发模式:   python demo_crawl4ai.py --max-concurrent 10 --max-depth 3
  多语言爬取:   python demo_crawl4ai.py --urls https://support.futunn.com/categories/2186 https://support.futunn.com/en/categories/2186
        """
    )
    
    parser.add_argument(
        '--urls', 
        nargs='+', 
        help='自定义URL列表（如果不指定，将使用演示URL）'
    )
    parser.add_argument(
        '--max-concurrent', 
        type=int, 
        default=5, 
        help='最大并发数 (默认: 5)'
    )
    parser.add_argument(
        '--max-depth', 
        type=int, 
        default=2, 
        help='最大爬取深度 (默认: 2)'
    )
    parser.add_argument(
        '--demo-type', 
        choices=['basic', 'custom'], 
        default='basic',
        help='演示类型 (默认: basic)'
    )
    
    args = parser.parse_args()
    
    # 检查 Crawl4AI 安装
    try:
        import crawl4ai
        print(f"✅ Crawl4AI 已安装 (版本: {crawl4ai.__version__ if hasattr(crawl4ai, '__version__') else '未知'})")
    except ImportError:
        print("❌ Crawl4AI 未安装")
        print("请运行: pip install crawl4ai aiohttp aiofiles")
        sys.exit(1)
    
    print(f"🤖 Python 版本: {sys.version}")
    print(f"📁 工作目录: {os.getcwd()}")
    print()
    
    # 运行演示
    if args.urls:
        # 自定义URL演示
        success = asyncio.run(demo_custom_crawl(
            urls=args.urls,
            max_concurrent=args.max_concurrent,
            max_depth=args.max_depth
        ))
    else:
        # 基础演示
        success = asyncio.run(demo_basic_crawl())
    
    if success:
        print("\n🎉 演示完成！")
        print("\n💡 提示:")
        print("  - 查看生成的输出目录以获取完整结果")
        print("  - 尝试不同的参数组合以优化性能")
        print("  - 使用 GUI 界面获得更好的用户体验: python main_crawl4ai.py")
    else:
        print("\n❌ 演示失败")
        sys.exit(1)

if __name__ == '__main__':
    main()