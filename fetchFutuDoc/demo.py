#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
富途牛牛帮助中心深度爬虫演示脚本
Futu Help Center Deep Crawler Demo Script

这个脚本演示了如何使用深度爬虫进行小规模测试爬取
"""

import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.deep_crawler import DeepFutuDocCrawler
from src.utils.config import CrawlerConfig

def demo_quick_crawl():
    """演示快速爬取"""
    print("=" * 60)
    print("富途牛牛帮助中心深度爬虫 - 快速演示")
    print("=" * 60)
    
    # 创建快速爬取配置
    config = CrawlerConfig(
        max_depth=2,
        max_articles_per_category=5,  # 每个分类只爬取5篇文章
        max_workers=2,
        delay_min=0.5,
        delay_max=1.5,
        output_dir="demo_output"
    )
    
    # 选择少量URL进行演示
    demo_urls = [
        "https://support.futunn.com/categories/2186",  # 基础知识入门（简体中文）
        "https://support.futunn.com/en/categories/2186",  # Getting started（英语）
    ]
    
    print(f"演示配置:")
    print(f"  - 最大深度: {config.max_depth}")
    print(f"  - 每分类最大文章数: {config.max_articles_per_category}")
    print(f"  - 并发线程数: {config.max_workers}")
    print(f"  - 延迟范围: {config.delay_min}-{config.delay_max}秒")
    print(f"  - 输出目录: {config.output_dir}")
    print(f"  - 目标URL数量: {len(demo_urls)}")
    print()
    
    # 创建爬虫实例
    crawler = DeepFutuDocCrawler(
        max_workers=config.max_workers,
        delay_range=(config.delay_min, config.delay_max)
    )
    
    try:
        print("开始演示爬取...")
        print("-" * 40)
        
        # 运行深度爬取
        docs_data, stats = crawler.run_deep_crawl(
            urls=demo_urls,
            max_depth=config.max_depth,
            max_articles_per_category=config.max_articles_per_category
        )
        
        # 保存到演示目录
        crawler.save_documents(config.output_dir)
        
        # 显示结果
        print("\n" + "=" * 40)
        print("演示爬取完成！")
        print("=" * 40)
        
        total_docs = sum(len(docs) for docs in docs_data.values())
        print(f"📊 爬取统计:")
        print(f"  - 总文档数: {total_docs}")
        print(f"  - 成功爬取: {stats['successful_crawls']}")
        print(f"  - 失败爬取: {stats['failed_crawls']}")
        print(f"  - 成功率: {stats['successful_crawls']/(stats['successful_crawls']+stats['failed_crawls'])*100:.1f}%")
        
        print(f"\n📁 按语言分类:")
        for lang, docs in docs_data.items():
            if docs:
                print(f"  - {lang}: {len(docs)} 篇文档")
        
        print(f"\n💾 文档已保存到: {config.output_dir}/")
        print(f"\n🎉 演示完成！你可以查看生成的JSON和Markdown文件。")
        
        # 显示文件路径
        if os.path.exists(config.output_dir):
            print(f"\n📂 生成的文件:")
            for root, dirs, files in os.walk(config.output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, config.output_dir)
                    print(f"  - {rel_path}")
        
    except KeyboardInterrupt:
        print("\n⏹️ 演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

def demo_config_management():
    """演示配置管理功能"""
    print("\n" + "=" * 60)
    print("配置管理演示")
    print("=" * 60)
    
    from src.utils.config import ConfigManager
    
    config_manager = ConfigManager()
    
    print("📋 可用的预设配置:")
    presets = config_manager.get_preset_names()
    for i, preset in enumerate(presets, 1):
        print(f"  {i}. {preset}")
    
    if presets:
        print(f"\n📄 '{presets[0]}' 配置详情:")
        try:
            preset_config = config_manager.load_config(f"config/preset_{presets[0]}.json")
            print(f"  - 最大深度: {preset_config.max_depth}")
            print(f"  - 每分类最大文章数: {preset_config.max_articles_per_category}")
            print(f"  - 并发线程数: {preset_config.max_workers}")
            print(f"  - 延迟范围: {preset_config.delay_min}-{preset_config.delay_max}秒")
        except Exception as e:
            print(f"  加载配置失败: {e}")

if __name__ == '__main__':
    print("富途牛牛帮助中心深度爬虫 - 演示模式")
    print("\n选择演示内容:")
    print("1. 快速爬取演示（推荐）")
    print("2. 配置管理演示")
    print("3. 退出")
    
    while True:
        try:
            choice = input("\n请选择 (1-3): ").strip()
            
            if choice == '1':
                demo_quick_crawl()
                break
            elif choice == '2':
                demo_config_management()
                break
            elif choice == '3':
                print("退出演示")
                break
            else:
                print("无效选择，请输入1-3")
                
        except KeyboardInterrupt:
            print("\n\n退出演示")
            break
        except EOFError:
            print("\n\n退出演示")
            break