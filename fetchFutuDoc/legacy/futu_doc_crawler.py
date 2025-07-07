#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
富途牛牛帮助中心文档爬虫
Futu Help Center Documentation Crawler
支持多语言文档生成：简体中文、繁体中文（香港）、英语
Supports multi-language documentation generation: Simplified Chinese, Traditional Chinese (Hong Kong), English
"""

import requests
import json
import os
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
import re
from typing import Dict, List, Optional

class FutuDocCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.base_url = 'https://support.futunn.com'
        self.crawled_urls = set()
        self.docs_data = {
            'zh-cn': {},  # 简体中文
            'zh-hk': {},  # 繁体中文（香港）
            'en': {}      # 英语
        }
        
    def get_page_content(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """获取页面内容"""
        for attempt in range(retries):
            try:
                print(f"正在爬取: {url} (尝试 {attempt + 1}/{retries})")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                response.encoding = 'utf-8'
                
                soup = BeautifulSoup(response.text, 'html.parser')
                return soup
                
            except requests.RequestException as e:
                print(f"请求失败 (尝试 {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    print(f"无法获取页面内容: {url}")
                    return None
                    
    def extract_article_content(self, soup: BeautifulSoup) -> Dict[str, str]:
        """提取文章内容"""
        content = {
            'title': '',
            'content': '',
            'category': '',
            'tags': []
        }
        
        # 提取标题
        title_selectors = [
            'h1.article-title',
            'h1',
            '.article-header h1',
            '.content-title',
            'title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                content['title'] = title_elem.get_text().strip()
                break
                
        # 提取主要内容
        content_selectors = [
            '.article-content',
            '.content-body',
            '.main-content',
            '.article-body',
            'main',
            '.content'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 移除不需要的元素
                for unwanted in content_elem.select('script, style, nav, footer, .sidebar, .advertisement'):
                    unwanted.decompose()
                    
                content['content'] = content_elem.get_text().strip()
                break
                
        # 如果没有找到特定的内容区域，使用整个body
        if not content['content']:
            body = soup.find('body')
            if body:
                for unwanted in body.select('script, style, nav, footer, .sidebar, .advertisement, header'):
                    unwanted.decompose()
                content['content'] = body.get_text().strip()
                
        # 提取分类信息
        category_selectors = [
            '.breadcrumb',
            '.category',
            '.nav-breadcrumb'
        ]
        
        for selector in category_selectors:
            category_elem = soup.select_one(selector)
            if category_elem:
                content['category'] = category_elem.get_text().strip()
                break
                
        return content
        
    def get_category_links(self, category_url: str) -> List[str]:
        """获取分类页面中的所有文章链接"""
        soup = self.get_page_content(category_url)
        if not soup:
            return []
            
        links = []
        
        # 查找文章链接的选择器
        link_selectors = [
            'a[href*="/articles/"]',
            'a[href*="/help/"]',
            'a[href*="/support/"]',
            '.article-link a',
            '.help-item a',
            '.content a'
        ]
        
        for selector in link_selectors:
            for link in soup.select(selector):
                href = link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in self.crawled_urls:
                        links.append(full_url)
                        
        return list(set(links))  # 去重
        
    def detect_language(self, text: str) -> str:
        """检测文本语言"""
        # 简单的语言检测逻辑
        if re.search(r'[\u4e00-\u9fff]', text):  # 包含中文字符
            # 检测繁体中文特征字符
            traditional_chars = ['繁', '體', '資', '訊', '開', '關', '設', '計', '網', '頁']
            if any(char in text for char in traditional_chars):
                return 'zh-hk'
            else:
                return 'zh-cn'
        else:
            return 'en'
            
    def crawl_category(self, category_url: str, max_articles: int = 50):
        """爬取分类页面"""
        print(f"\n开始爬取分类: {category_url}")
        
        # 爬取分类页面本身
        soup = self.get_page_content(category_url)
        if soup:
            content = self.extract_article_content(soup)
            if content['title'] and content['content']:
                lang = self.detect_language(content['content'])
                self.docs_data[lang][category_url] = content
                self.crawled_urls.add(category_url)
                
        # 获取分类下的文章链接
        article_links = self.get_category_links(category_url)
        print(f"找到 {len(article_links)} 个文章链接")
        
        # 爬取文章
        crawled_count = 0
        for link in article_links[:max_articles]:
            if crawled_count >= max_articles:
                break
                
            soup = self.get_page_content(link)
            if soup:
                content = self.extract_article_content(soup)
                if content['title'] and content['content']:
                    lang = self.detect_language(content['content'])
                    self.docs_data[lang][link] = content
                    self.crawled_urls.add(link)
                    crawled_count += 1
                    print(f"已爬取文章: {content['title'][:50]}...")
                    
            time.sleep(1)  # 避免请求过于频繁
            
    def save_docs(self, output_dir: str = 'docs'):
        """保存文档"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for lang, docs in self.docs_data.items():
            if not docs:
                continue
                
            lang_dir = os.path.join(output_dir, lang)
            if not os.path.exists(lang_dir):
                os.makedirs(lang_dir)
                
            # 保存JSON格式
            json_file = os.path.join(lang_dir, f'futu_docs_{timestamp}.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(docs, f, ensure_ascii=False, indent=2)
                
            # 保存Markdown格式
            md_file = os.path.join(lang_dir, f'futu_docs_{timestamp}.md')
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(f"# 富途牛牛帮助中心文档 - {lang.upper()}\n\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for url, content in docs.items():
                    f.write(f"## {content['title']}\n\n")
                    f.write(f"**来源**: {url}\n\n")
                    if content['category']:
                        f.write(f"**分类**: {content['category']}\n\n")
                    f.write(f"{content['content']}\n\n")
                    f.write("---\n\n")
                    
            print(f"已保存 {lang} 文档: {len(docs)} 篇文章")
            print(f"JSON文件: {json_file}")
            print(f"Markdown文件: {md_file}")
            
    def run(self, urls: List[str], max_articles_per_category: int = 30):
        """运行爬虫"""
        print("开始爬取富途牛牛帮助中心文档...")
        print(f"目标URL数量: {len(urls)}")
        
        for url in urls:
            try:
                self.crawl_category(url, max_articles_per_category)
                time.sleep(2)  # 分类间暂停
            except Exception as e:
                print(f"爬取分类失败 {url}: {e}")
                continue
                
        print("\n爬取完成，正在保存文档...")
        self.save_docs()
        
        # 打印统计信息
        total_docs = sum(len(docs) for docs in self.docs_data.values())
        print(f"\n=== 爬取统计 ===")
        print(f"总文档数: {total_docs}")
        for lang, docs in self.docs_data.items():
            print(f"{lang}: {len(docs)} 篇")
            
def main():
    """主函数"""
    # 目标URL列表
    target_urls = [
        'https://support.futunn.com/categories/2186',  # 基础知识入门
        'https://support.futunn.com/categories/2185',  # 市场介绍
    ]
    
    # 创建爬虫实例
    crawler = FutuDocCrawler()
    
    # 运行爬虫
    crawler.run(target_urls, max_articles_per_category=50)
    
if __name__ == '__main__':
    main()