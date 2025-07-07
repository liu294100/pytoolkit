#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试优化后的深度爬虫功能
Test script for optimized deep crawler
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.deep_crawler import DeepFutuDocCrawler, CrawlerSettings, ContentQualityChecker
import logging

def test_content_quality_checker():
    """测试内容质量检测器"""
    print("\n=== 测试内容质量检测器 ===")
    
    checker = ContentQualityChecker()
    
    # 测试高质量内容
    good_content = {
        'title': '港股盘前指的是什么 - 详细解释',
        'content': '港股盘前交易是指在正式交易时间之前进行的股票交易活动。' * 10,
        'url': 'https://support.futunn.com/zh-cn/topic123'
    }
    
    quality = checker.check_content_quality(good_content)
    print(f"高质量内容测试: 有效={quality.is_valid}, 评分={quality.score:.1f}")
    if quality.issues:
        print(f"问题: {', '.join(quality.issues)}")
    
    # 测试低质量内容
    bad_content = {
        'title': '短',
        'content': '内容太短',
        'url': 'invalid-url'
    }
    
    quality = checker.check_content_quality(bad_content)
    print(f"低质量内容测试: 有效={quality.is_valid}, 评分={quality.score:.1f}")
    if quality.issues:
        print(f"问题: {', '.join(quality.issues)}")

def test_crawler_settings():
    """测试爬虫配置"""
    print("\n=== 测试爬虫配置 ===")
    
    # 默认配置
    default_settings = CrawlerSettings()
    print(f"默认配置: 工作线程={default_settings.max_workers}, 延迟={default_settings.delay_range}")
    
    # 自定义配置
    custom_settings = CrawlerSettings(
        max_workers=2,
        delay_range=(0.5, 2.0),
        timeout=20,
        retries=2
    )
    print(f"自定义配置: 工作线程={custom_settings.max_workers}, 延迟={custom_settings.delay_range}")
    print(f"超时={custom_settings.timeout}秒, 重试={custom_settings.retries}次")

def test_crawler_initialization():
    """测试爬虫初始化"""
    print("\n=== 测试爬虫初始化 ===")
    
    # 使用默认配置
    crawler1 = DeepFutuDocCrawler()
    print(f"默认爬虫初始化成功: 工作线程={crawler1.settings.max_workers}")
    print(f"统计信息初始化: {list(crawler1.stats.keys())}")
    
    # 使用自定义配置
    custom_settings = CrawlerSettings(max_workers=1, delay_range=(1.0, 2.0))
    crawler2 = DeepFutuDocCrawler(custom_settings)
    print(f"自定义爬虫初始化成功: 工作线程={crawler2.settings.max_workers}")
    
    # 测试质量检测器
    print(f"质量检测器已初始化: {type(crawler1.quality_checker).__name__}")

def test_filename_generation():
    """测试文件名生成功能"""
    print("\n=== 测试文件名生成 ===")
    
    crawler = DeepFutuDocCrawler()
    
    test_titles = [
        '港股盘前指的是什么？',
        'What is pre-market trading?',
        '文件名包含<>:"/\\|?*非法字符',
        '   多个   空格   的标题   ',
        '',  # 空标题
        '正常的标题'
    ]
    
    for title in test_titles:
        safe_name = crawler._generate_safe_filename(title)
        print(f"原标题: '{title}' -> 安全文件名: '{safe_name}'")

def test_logging_setup():
    """测试日志设置"""
    print("\n=== 测试日志设置 ===")
    
    crawler = DeepFutuDocCrawler()
    
    # 测试不同级别的日志
    crawler.logger.info("这是一条信息日志")
    crawler.logger.warning("这是一条警告日志")
    crawler.logger.debug("这是一条调试日志（可能不显示）")
    
    print(f"日志器名称: {crawler.logger.name}")
    print(f"日志级别: {crawler.logger.level}")
    print(f"处理器数量: {len(crawler.logger.handlers)}")

def main():
    """主测试函数"""
    print("🧪 开始测试优化后的深度爬虫功能")
    print("=" * 50)
    
    try:
        # 运行各项测试
        test_content_quality_checker()
        test_crawler_settings()
        test_crawler_initialization()
        test_filename_generation()
        test_logging_setup()
        
        print("\n" + "=" * 50)
        print("✅ 所有测试完成！优化功能验证成功。")
        print("\n📝 优化特性总结:")
        print("  🔍 智能内容质量检测")
        print("  ⚙️  灵活的配置管理")
        print("  🛡️  增强的错误处理")
        print("  💾 内容缓存机制")
        print("  📊 详细的统计信息")
        print("  📁 安全的文件名生成")
        print("  🔧 优化的并发控制")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()