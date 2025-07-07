#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试链接提取功能
验证爬虫是否能正确提取子项链接和相关链接
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.deep_crawler import DeepFutuDocCrawler, CrawlerSettings
import logging

def test_link_extraction():
    """测试链接提取功能"""
    print("🔍 测试链接提取功能...")
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建爬虫设置
    settings = CrawlerSettings(
        max_workers=2,
        delay_range=(1, 3),
        timeout=30,
        retries=2,
        output_dir='test_output'
    )
    
    # 创建爬虫实例
    crawler = DeepFutuDocCrawler(settings)
    
    # 测试URL - 富途帮助中心的股票入门分类页面
    test_urls = [
        'https://support.futunn.com/zh-cn/categories/360000010781',  # 股票入门
        'https://support.futunn.com/zh-cn/topic37',  # 具体文章
    ]
    
    print(f"\n📋 测试URL列表:")
    for i, url in enumerate(test_urls, 1):
        print(f"  {i}. {url}")
    
    print(f"\n🚀 开始测试...")
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{'='*60}")
        print(f"测试 {i}/{len(test_urls)}: {url}")
        
        try:
            # 获取页面内容
            soup = crawler.get_page_content(url)
            if not soup:
                print(f"❌ 无法获取页面内容: {url}")
                continue
            
            # 提取内容
            content = crawler.extract_content_from_page(soup, url)
            
            print(f"✅ 成功提取内容:")
            print(f"   标题: {content['title'][:50]}...")
            print(f"   内容长度: {len(content['content'])} 字符")
            print(f"   语言: {content['language']}")
            
            # 检查子项链接
            sub_items = content.get('sub_items', [])
            print(f"   子项链接: {len(sub_items)} 个")
            if sub_items:
                print(f"   前3个子项:")
                for j, item in enumerate(sub_items[:3], 1):
                    print(f"     {j}. {item['title'][:30]}... -> {item['url']}")
            
            # 检查相关链接
            related_links = content.get('related_links', [])
            print(f"   相关链接: {len(related_links)} 个")
            if related_links:
                print(f"   前3个相关链接:")
                for j, link in enumerate(related_links[:3], 1):
                    print(f"     {j}. {link['title'][:30]}... -> {link['url']}")
            
            # 测试extract_all_links方法
            all_links = crawler.extract_all_links(soup, url)
            print(f"   所有链接统计:")
            print(f"     分类链接: {len(all_links['categories'])} 个")
            print(f"     文章链接: {len(all_links['articles'])} 个")
            print(f"     子分类链接: {len(all_links['subcategories'])} 个")
            
            if all_links['articles']:
                print(f"   前3个文章链接:")
                for j, article_url in enumerate(all_links['articles'][:3], 1):
                    print(f"     {j}. {article_url}")
                    
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("🎉 链接提取功能测试完成！")
    print(f"\n📊 爬虫统计信息:")
    for key, value in crawler.stats.items():
        print(f"   {key}: {value}")

if __name__ == '__main__':
    test_link_extraction()