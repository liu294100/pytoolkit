#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
富途牛牛帮助中心增强版文档爬虫
Enhanced Futu Help Center Documentation Crawler
深度爬取具体文章内容，支持多语言文档生成
Deep crawling of specific article content with multi-language support
"""

import requests
import json
import os
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime
from typing import Dict, List, Optional, Set
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancedFutuDocCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
        self.base_url = 'https://support.futunn.com'
        self.crawled_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.docs_data = {
            'zh-cn': {},  # 简体中文
            'zh-hk': {},  # 繁体中文（香港）
            'en': {}      # 英语
        }
        
        # 爬取配置
        self.config = {
            'max_workers': 3,  # 并发线程数
            'request_timeout': 30,
            'retry_count': 3,
            'delay_range': (1, 3),  # 随机延迟范围
            'min_content_length': 50
        }
        
    def get_page_content(self, url: str, retries: int = None) -> Optional[BeautifulSoup]:
        """获取页面内容，支持重试和随机延迟"""
        if retries is None:
            retries = self.config['retry_count']
            
        for attempt in range(retries):
            try:
                # 随机延迟
                delay = random.uniform(*self.config['delay_range'])
                time.sleep(delay)
                
                logger.info(f"正在爬取: {url} (尝试 {attempt + 1}/{retries})")
                
                response = self.session.get(url, timeout=self.config['request_timeout'])
                response.raise_for_status()
                
                # 检测编码
                if response.encoding.lower() in ['iso-8859-1', 'windows-1252']:
                    response.encoding = 'utf-8'
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                return soup
                
            except requests.RequestException as e:
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    logger.error(f"无法获取页面内容: {url}")
                    self.failed_urls.add(url)
                    return None
                    
    def extract_article_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """从页面中提取文章链接"""
        links = []
        
        # 更全面的链接选择器
        link_selectors = [
            'a[href*="/articles/"]',
            'a[href*="/help/"]',
            'a[href*="/support/"]',
            'a[href*="/kb/"]',
            'a[href*="/faq/"]',
            '.article-link a',
            '.help-item a',
            '.content a',
            '.list-item a',
            '.category-item a',
            'ul li a',
            '.nav-item a'
        ]
        
        for selector in link_selectors:
            for link in soup.select(selector):
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    # 过滤有效的文章链接
                    if self.is_valid_article_url(full_url):
                        links.append(full_url)
                        
        # 查找分页链接
        pagination_selectors = [
            'a[href*="page="]',
            '.pagination a',
            '.pager a',
            'a[rel="next"]'
        ]
        
        for selector in pagination_selectors:
            for link in soup.select(selector):
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if self.is_valid_category_url(full_url):
                        links.append(full_url)
                        
        return list(set(links))  # 去重
        
    def is_valid_article_url(self, url: str) -> bool:
        """判断是否为有效的文章URL"""
        if url in self.crawled_urls or url in self.failed_urls:
            return False
            
        # 排除不需要的URL
        exclude_patterns = [
            r'/login',
            r'/register',
            r'/logout',
            r'/search',
            r'/contact',
            r'/about',
            r'\.(jpg|jpeg|png|gif|pdf|doc|docx|xls|xlsx)$',
            r'#',
            r'javascript:',
            r'mailto:'
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
                
        return True
        
    def is_valid_category_url(self, url: str) -> bool:
        """判断是否为有效的分类URL"""
        return ('/categories/' in url or '/page=' in url) and url not in self.crawled_urls
        
    def extract_article_content(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """提取文章内容，使用更智能的选择器，优先使用content-box"""
        content = {
            'title': '',
            'content': '',
            'category': '',
            'tags': [],
            'url': url,
            'crawl_time': datetime.now().isoformat()
        }
        
        # 提取标题 - 更全面的选择器
        title_selectors = [
            'h1.article-title',
            'h1.title',
            'h1',
            '.article-header h1',
            '.content-title',
            '.page-title',
            'title',
            '.main-title',
            '.entry-title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.get_text().strip():
                content['title'] = title_elem.get_text().strip()
                break
                
        # 提取主要内容 - 优先使用用户指定的content-box
        content_selectors = [
            'div.content-box',  # 用户指定的主要内容区域
            '.content-box',
            '.article-content',
            '.content-body',
            '.main-content',
            '.article-body',
            '.entry-content',
            '.post-content',
            'main .content',
            '.help-content',
            '.kb-content',
            'article',
            '.article'
        ]
        
        content_text = ''
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 移除不需要的元素
                for unwanted in content_elem.select(
                    'script, style, nav, footer, .sidebar, .advertisement, '
                    '.social-share, .comments, .related-articles, .breadcrumb'
                ):
                    unwanted.decompose()
                    
                content_text = content_elem.get_text().strip()
                if len(content_text) > self.config['min_content_length']:
                    break
                    
        # 如果没有找到特定的内容区域，尝试从body提取
        if not content_text or len(content_text) < self.config['min_content_length']:
            body = soup.find('body')
            if body:
                for unwanted in body.select(
                    'script, style, nav, footer, .sidebar, .advertisement, '
                    'header, .header, .navigation, .menu'
                ):
                    unwanted.decompose()
                content_text = body.get_text().strip()
                
        content['content'] = self.clean_text(content_text)
        
        # 提取分类信息
        category_selectors = [
            '.breadcrumb',
            '.category',
            '.nav-breadcrumb',
            '.page-category',
            '.article-category'
        ]
        
        for selector in category_selectors:
            category_elem = soup.select_one(selector)
            if category_elem:
                content['category'] = category_elem.get_text().strip()
                break
                
        # 提取标签
        tag_selectors = [
            '.tags a',
            '.article-tags a',
            '.tag-list a',
            '.labels a'
        ]
        
        for selector in tag_selectors:
            for tag_elem in soup.select(selector):
                tag_text = tag_elem.get_text().strip()
                if tag_text:
                    content['tags'].append(tag_text)
                    
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
        
    def detect_language(self, text: str, url: str = '') -> str:
        """检测文本语言，优先根据URL路径判断，改进的检测逻辑"""
        # 首先根据URL路径判断语言
        if '/en/' in url:
            return 'en'
        elif '/hant/' in url:
            return 'zh-hk'
        elif '/categories/' in url and '/en/' not in url and '/hant/' not in url:
            return 'zh-cn'
            
        # 如果URL无法判断，则使用文本内容检测
        if not text:
            return 'en'
            
        # 计算中文字符比例
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text)
        
        if total_chars == 0:
            return 'en'
            
        chinese_ratio = chinese_chars / total_chars
        
        if chinese_ratio < 0.1:  # 中文字符少于10%，认为是英文
            return 'en'
        elif chinese_ratio >= 0.1:  # 包含中文字符
            # 检测繁体中文特征字符
            traditional_chars = ['繁', '體', '資', '訊', '開', '關', '設', '計', '網', '頁', 
                               '個', '們', '來', '時', '會', '過', '還', '這', '對', '現',
                               '應', '經', '業', '產', '務', '員', '際', '術', '據', '題']
            traditional_count = sum(1 for char in traditional_chars if char in text)
            
            # 如果繁体字符较多，判断为繁体中文
            if traditional_count >= 3:
                return 'zh-hk'
            else:
                return 'zh-cn'
        else:
            return 'en'
            
    def crawl_article(self, url: str) -> Optional[Dict]:
        """爬取单篇文章"""
        if url in self.crawled_urls:
            return None
            
        soup = self.get_page_content(url)
        if not soup:
            return None
            
        content = self.extract_article_content(soup, url)
        
        # 验证内容质量
        if (content['title'] and 
            content['content'] and 
            len(content['content']) >= self.config['min_content_length']):
            
            self.crawled_urls.add(url)
            logger.info(f"成功爬取文章: {content['title'][:50]}...")
            return content
        else:
            logger.warning(f"文章内容质量不足，跳过: {url}")
            return None
            
    def crawl_category_deep(self, category_url: str, max_articles: int = 50) -> List[Dict]:
        """深度爬取分类页面及其文章"""
        logger.info(f"开始深度爬取分类: {category_url}")
        
        articles = []
        urls_to_crawl = [category_url]
        processed_urls = set()
        
        while urls_to_crawl and len(articles) < max_articles:
            current_url = urls_to_crawl.pop(0)
            
            if current_url in processed_urls:
                continue
                
            processed_urls.add(current_url)
            
            soup = self.get_page_content(current_url)
            if not soup:
                continue
                
            # 如果是文章页面，直接提取内容
            if '/articles/' in current_url or '/help/' in current_url:
                article = self.crawl_article(current_url)
                if article:
                    articles.append(article)
                continue
                
            # 如果是分类页面，提取链接
            links = self.extract_article_links(soup, self.base_url)
            logger.info(f"从 {current_url} 找到 {len(links)} 个链接")
            
            # 添加新链接到待爬取列表
            for link in links:
                if (link not in processed_urls and 
                    link not in urls_to_crawl and 
                    len(articles) < max_articles):
                    urls_to_crawl.append(link)
                    
        logger.info(f"分类 {category_url} 爬取完成，共获得 {len(articles)} 篇文章")
        return articles
        
    def save_docs_enhanced(self, output_dir: str = 'docs_enhanced'):
        """保存文档，增强版格式"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存统计信息
        stats = {
            'crawl_time': datetime.now().isoformat(),
            'total_urls_crawled': len(self.crawled_urls),
            'failed_urls': len(self.failed_urls),
            'languages': {}
        }
        
        for lang, docs in self.docs_data.items():
            if not docs:
                continue
                
            lang_dir = os.path.join(output_dir, lang)
            if not os.path.exists(lang_dir):
                os.makedirs(lang_dir)
                
            stats['languages'][lang] = len(docs)
            
            # 保存详细JSON格式
            json_file = os.path.join(lang_dir, f'futu_docs_enhanced_{timestamp}.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(docs, f, ensure_ascii=False, indent=2)
                
            # 保存结构化Markdown格式
            md_file = os.path.join(lang_dir, f'futu_docs_enhanced_{timestamp}.md')
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(f"# 富途牛牛帮助中心文档 - {lang.upper()}\n\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"文档数量: {len(docs)}\n\n")
                f.write("---\n\n")
                
                for url, content in docs.items():
                    f.write(f"## {content['title']}\n\n")
                    f.write(f"**来源**: {content['url']}\n\n")
                    f.write(f"**爬取时间**: {content.get('crawl_time', 'N/A')}\n\n")
                    
                    if content.get('category'):
                        f.write(f"**分类**: {content['category']}\n\n")
                        
                    if content.get('tags'):
                        f.write(f"**标签**: {', '.join(content['tags'])}\n\n")
                        
                    f.write(f"{content['content']}\n\n")
                    f.write("---\n\n")
                    
            logger.info(f"已保存 {lang} 文档: {len(docs)} 篇文章")
            logger.info(f"JSON文件: {json_file}")
            logger.info(f"Markdown文件: {md_file}")
            
        # 保存统计信息
        stats_file = os.path.join(output_dir, f'crawl_stats_{timestamp}.json')
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
            
        # 保存失败的URL
        if self.failed_urls:
            failed_file = os.path.join(output_dir, f'failed_urls_{timestamp}.txt')
            with open(failed_file, 'w', encoding='utf-8') as f:
                for url in self.failed_urls:
                    f.write(f"{url}\n")
                    
    def run_enhanced(self, urls: List[str], max_articles_per_category: int = 50):
        """运行增强版爬虫"""
        logger.info("开始运行增强版富途牛牛帮助中心文档爬虫...")
        logger.info(f"目标URL数量: {len(urls)}")
        logger.info(f"每个分类最大文章数: {max_articles_per_category}")
        
        all_articles = []
        
        for url in urls:
            try:
                articles = self.crawl_category_deep(url, max_articles_per_category)
                all_articles.extend(articles)
                
                # 分类间暂停
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                logger.error(f"爬取分类失败 {url}: {e}")
                continue
                
        # 按语言分类文章
        for article in all_articles:
            if article['content']:
                lang = self.detect_language(article['content'], article['url'])
                self.docs_data[lang][article['url']] = article
                
        logger.info("爬取完成，正在保存文档...")
        self.save_docs_enhanced()
        
        # 打印统计信息
        total_docs = sum(len(docs) for docs in self.docs_data.values())
        logger.info(f"\n=== 增强版爬取统计 ===")
        logger.info(f"总文档数: {total_docs}")
        logger.info(f"成功爬取URL: {len(self.crawled_urls)}")
        logger.info(f"失败URL: {len(self.failed_urls)}")
        
        for lang, docs in self.docs_data.items():
            logger.info(f"{lang}: {len(docs)} 篇")
            
def main():
    """主函数"""
    # 目标URL列表 - 支持多语言版本
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
    
    # 创建增强版爬虫实例
    crawler = EnhancedFutuDocCrawler()
    
    # 运行爬虫
    crawler.run_enhanced(target_urls, max_articles_per_category=50)
    
if __name__ == '__main__':
    main()