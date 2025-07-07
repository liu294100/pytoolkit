#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
富途牛牛帮助中心多语言文档爬虫
Futu Help Center Multi-language Documentation Crawler
专门针对用户指定的多语言URL和content-box内容区域
"""

import requests
import json
import os
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from typing import Dict, List, Optional
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('multilang_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MultiLangFutuDocCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        
        self.docs_data = {
            'zh-cn': {},  # 简体中文
            'zh-hk': {},  # 繁体中文（香港）
            'en': {}      # 英语
        }
        
    def get_page_content(self, url: str, timeout: int = 30) -> Optional[BeautifulSoup]:
        """获取页面内容"""
        try:
            logger.info(f"正在爬取: {url}")
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            # 检测编码
            if response.encoding.lower() in ['iso-8859-1', 'windows-1252']:
                response.encoding = 'utf-8'
                
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup
            
        except requests.RequestException as e:
            logger.error(f"无法获取页面内容 {url}: {e}")
            return None
            
    def extract_content_from_page(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """从页面提取内容，优先使用content-box"""
        content = {
            'title': '',
            'content': '',
            'category': '',
            'url': url,
            'crawl_time': datetime.now().isoformat()
        }
        
        # 提取标题
        title_selectors = [
            'h1',
            '.page-title',
            '.content-title',
            'title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.get_text().strip():
                content['title'] = title_elem.get_text().strip()
                break
                
        # 提取主要内容 - 优先使用用户指定的content-box
        content_text = ''
        
        # 首先尝试用户指定的content-box
        content_box = soup.select_one('div.content-box') or soup.select_one('.content-box')
        if content_box:
            logger.info("✓ 找到content-box内容区域")
            # 移除不需要的元素
            for unwanted in content_box.select('script, style, nav, footer, .advertisement'):
                unwanted.decompose()
            content_text = content_box.get_text().strip()
        else:
            logger.warning("⚠ 未找到content-box，尝试其他选择器")
            # 备用选择器
            backup_selectors = [
                '.main-content',
                '.article-content',
                '.content-body',
                'main',
                'article'
            ]
            
            for selector in backup_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    for unwanted in content_elem.select('script, style, nav, footer, .advertisement'):
                        unwanted.decompose()
                    content_text = content_elem.get_text().strip()
                    if len(content_text) > 100:  # 确保内容足够长
                        break
                        
        content['content'] = self.clean_text(content_text)
        
        # 提取分类信息
        breadcrumb = soup.select_one('.breadcrumb')
        if breadcrumb:
            content['category'] = breadcrumb.get_text().strip()
            
        return content
        
    def clean_text(self, text: str) -> str:
        """清理文本内容"""
        if not text:
            return ''
            
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        # 移除首尾空白
        text = text.strip()
        # 移除特殊字符
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        return text
        
    def detect_language_from_url(self, url: str) -> str:
        """根据URL路径检测语言"""
        if '/en/' in url:
            return 'en'
        elif '/hant/' in url:
            return 'zh-hk'
        else:
            return 'zh-cn'
            
    def extract_article_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """提取页面中的文章链接"""
        links = []
        
        # 查找文章链接
        for link in soup.select('a[href]'):
            href = link.get('href')
            if href:
                full_url = urljoin(base_url, href)
                # 过滤有效的文章链接
                if ('/articles/' in full_url or 
                    '/help/' in full_url or 
                    '/support/' in full_url or
                    '/learn/' in full_url):
                    links.append(full_url)
                    
        return list(set(links))  # 去重
        
    def crawl_category_and_articles(self, category_url: str, max_articles: int = 20) -> List[Dict]:
        """爬取分类页面和相关文章"""
        logger.info(f"开始爬取分类: {category_url}")
        
        articles = []
        
        # 首先爬取分类页面本身
        soup = self.get_page_content(category_url)
        if soup:
            category_content = self.extract_content_from_page(soup, category_url)
            if category_content['content'] and len(category_content['content']) > 100:
                articles.append(category_content)
                logger.info(f"成功爬取分类页面: {category_content['title'][:50]}...")
                
            # 提取文章链接
            article_links = self.extract_article_links(soup, 'https://support.futunn.com')
            logger.info(f"找到 {len(article_links)} 个文章链接")
            
            # 爬取前几篇文章
            for i, link in enumerate(article_links[:max_articles]):
                if i >= max_articles:
                    break
                    
                time.sleep(1)  # 避免请求过快
                
                article_soup = self.get_page_content(link)
                if article_soup:
                    article_content = self.extract_content_from_page(article_soup, link)
                    if article_content['content'] and len(article_content['content']) > 100:
                        articles.append(article_content)
                        logger.info(f"成功爬取文章 {i+1}: {article_content['title'][:50]}...")
                        
        logger.info(f"分类 {category_url} 爬取完成，共获得 {len(articles)} 篇文档")
        return articles
        
    def save_documents(self, output_dir: str = 'docs_multilang'):
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
            json_file = os.path.join(lang_dir, f'futu_docs_multilang_{timestamp}.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(docs, f, ensure_ascii=False, indent=2)
                
            # 保存Markdown格式
            md_file = os.path.join(lang_dir, f'futu_docs_multilang_{timestamp}.md')
            with open(md_file, 'w', encoding='utf-8') as f:
                lang_names = {
                    'zh-cn': '简体中文',
                    'zh-hk': '繁体中文（香港）',
                    'en': 'English'
                }
                
                f.write(f"# 富途牛牛帮助中心文档 - {lang_names.get(lang, lang.upper())}\n\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"文档数量: {len(docs)}\n\n")
                f.write("---\n\n")
                
                for url, content in docs.items():
                    f.write(f"## {content['title']}\n\n")
                    f.write(f"**来源**: {content['url']}\n\n")
                    f.write(f"**爬取时间**: {content.get('crawl_time', 'N/A')}\n\n")
                    
                    if content.get('category'):
                        f.write(f"**分类**: {content['category']}\n\n")
                        
                    f.write(f"{content['content']}\n\n")
                    f.write("---\n\n")
                    
            logger.info(f"已保存 {lang} 文档: {len(docs)} 篇")
            logger.info(f"JSON文件: {json_file}")
            logger.info(f"Markdown文件: {md_file}")
            
    def run(self, urls: List[str], max_articles_per_category: int = 10):
        """运行多语言爬虫"""
        logger.info("开始运行多语言富途牛牛帮助中心文档爬虫...")
        logger.info(f"目标URL数量: {len(urls)}")
        logger.info(f"每个分类最大文章数: {max_articles_per_category}")
        
        for url in urls:
            try:
                # 检测语言
                lang = self.detect_language_from_url(url)
                logger.info(f"\n处理 {lang} 版本: {url}")
                
                # 爬取分类和文章
                articles = self.crawl_category_and_articles(url, max_articles_per_category)
                
                # 保存到对应语言的数据中
                for article in articles:
                    self.docs_data[lang][article['url']] = article
                    
                # 分类间暂停
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"爬取失败 {url}: {e}")
                continue
                
        # 保存文档
        logger.info("\n爬取完成，正在保存文档...")
        self.save_documents()
        
        # 打印统计信息
        total_docs = sum(len(docs) for docs in self.docs_data.values())
        logger.info(f"\n=== 多语言爬取统计 ===")
        logger.info(f"总文档数: {total_docs}")
        
        for lang, docs in self.docs_data.items():
            lang_names = {
                'zh-cn': '简体中文',
                'zh-hk': '繁体中文（香港）',
                'en': 'English'
            }
            logger.info(f"{lang_names.get(lang, lang)}: {len(docs)} 篇")
            
def main():
    """主函数"""
    # 用户指定的多语言URL
    target_urls = [
        # 简体中文版本
        'https://support.futunn.com/categories/2186',  # 基础知识入门
        'https://support.futunn.com/categories/2185',  # 市场介绍
        
        # 繁体中文（香港）版本
        'https://support.futunn.com/hant/categories/2186',  # 基础知识入门
        'https://support.futunn.com/hant/categories/2185',  # 市场介绍
        
        # 英语版本
        'https://support.futunn.com/en/categories/2186',  # 基础知识入门
        'https://support.futunn.com/en/categories/2185',  # 市场介绍
    ]
    
    # 创建爬虫实例
    crawler = MultiLangFutuDocCrawler()
    
    # 运行爬虫
    crawler.run(target_urls, max_articles_per_category=5)
    
if __name__ == '__main__':
    main()