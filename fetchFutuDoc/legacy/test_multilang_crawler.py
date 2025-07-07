#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多语言爬虫测试脚本
Multi-language Crawler Test Script
测试富途牛牛帮助中心多语言版本的爬取功能
"""

import sys
import os
from enhanced_crawler import EnhancedFutuDocCrawler
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_single_url(crawler, url, lang_expected):
    """测试单个URL的爬取"""
    logger.info(f"\n=== 测试URL: {url} ===")
    logger.info(f"预期语言: {lang_expected}")
    
    # 获取页面内容
    soup = crawler.get_page_content(url)
    if not soup:
        logger.error(f"无法获取页面内容: {url}")
        return False
        
    # 提取内容
    content = crawler.extract_article_content(soup, url)
    
    # 检测语言
    detected_lang = crawler.detect_language(content['content'], url)
    
    logger.info(f"标题: {content['title'][:50]}...")
    logger.info(f"内容长度: {len(content['content'])}")
    logger.info(f"检测到的语言: {detected_lang}")
    logger.info(f"语言检测正确: {detected_lang == lang_expected}")
    
    # 检查是否找到content-box内容
    if soup.select_one('div.content-box') or soup.select_one('.content-box'):
        logger.info("✓ 找到content-box内容区域")
    else:
        logger.warning("⚠ 未找到content-box内容区域，使用备用选择器")
        
    return content

def main():
    """主测试函数"""
    logger.info("开始多语言爬虫测试...")
    
    # 创建爬虫实例
    crawler = EnhancedFutuDocCrawler()
    
    # 测试URL列表
    test_urls = [
        ('https://support.futunn.com/categories/2185', 'zh-cn', '简体中文'),
        ('https://support.futunn.com/hant/categories/2185', 'zh-hk', '繁体中文（香港）'),
        ('https://support.futunn.com/en/categories/2185', 'en', '英语'),
    ]
    
    results = []
    
    for url, expected_lang, lang_name in test_urls:
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"测试 {lang_name} 版本")
            logger.info(f"{'='*60}")
            
            content = test_single_url(crawler, url, expected_lang)
            if content:
                results.append({
                    'url': url,
                    'language': lang_name,
                    'expected_lang': expected_lang,
                    'detected_lang': crawler.detect_language(content['content'], url),
                    'title': content['title'],
                    'content_length': len(content['content']),
                    'success': True
                })
            else:
                results.append({
                    'url': url,
                    'language': lang_name,
                    'success': False
                })
                
        except Exception as e:
            logger.error(f"测试失败 {url}: {e}")
            results.append({
                'url': url,
                'language': lang_name,
                'success': False,
                'error': str(e)
            })
    
    # 输出测试结果摘要
    logger.info(f"\n{'='*60}")
    logger.info("测试结果摘要")
    logger.info(f"{'='*60}")
    
    successful_tests = 0
    for result in results:
        if result['success']:
            successful_tests += 1
            logger.info(f"✓ {result['language']}: 成功")
            logger.info(f"  - 标题: {result['title'][:50]}...")
            logger.info(f"  - 内容长度: {result['content_length']}")
            logger.info(f"  - 语言检测: {result['detected_lang']} (预期: {result['expected_lang']})")
        else:
            logger.error(f"✗ {result['language']}: 失败")
            if 'error' in result:
                logger.error(f"  - 错误: {result['error']}")
    
    logger.info(f"\n测试完成: {successful_tests}/{len(results)} 成功")
    
    if successful_tests == len(results):
        logger.info("🎉 所有测试通过！多语言爬虫配置正确。")
        return True
    else:
        logger.warning(f"⚠ {len(results) - successful_tests} 个测试失败，请检查配置。")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)