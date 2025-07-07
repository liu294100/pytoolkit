#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
富途牛牛帮助中心深度爬虫核心模块
Futu Help Center Deep Crawler Core Module
支持深度递归爬取分类下的所有文章链接

优化特性:
- 增强的HTML解析精度
- 智能内容质量检测
- 改进的错误处理和重试机制
- 优化的并发控制
- 灵活的配置管理
"""

import requests
import json
import os
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Union
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
from dataclasses import dataclass, field
from pathlib import Path
import hashlib

@dataclass
class CrawlerSettings:
    """爬虫配置设置"""
    max_workers: int = 3
    delay_range: Tuple[float, float] = (1.0, 3.0)
    timeout: int = 30
    retries: int = 3
    max_content_length: int = 1000000  # 1MB
    min_content_length: int = 100
    output_dir: str = 'docs_deep'
    user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
@dataclass
class ContentQuality:
    """内容质量评估结果"""
    is_valid: bool
    score: float
    issues: List[str] = field(default_factory=list)
    
class ContentQualityChecker:
    """内容质量检测器"""
    
    @staticmethod
    def check_content_quality(content: Dict[str, str]) -> ContentQuality:
        """检查内容质量"""
        issues = []
        score = 100.0
        
        # 检查标题
        if not content.get('title') or len(content['title'].strip()) < 5:
            issues.append('标题过短或缺失')
            score -= 30
            
        # 检查内容长度
        content_text = content.get('content', '')
        if len(content_text) < 100:
            issues.append('内容过短')
            score -= 40
        elif len(content_text) > 100000:
            issues.append('内容过长，可能包含噪音')
            score -= 20
            
        # 检查内容质量
        if content_text:
            # 检查重复内容
            lines = content_text.split('\n')
            unique_lines = set(line.strip() for line in lines if line.strip())
            if len(lines) > 10 and len(unique_lines) / len(lines) < 0.7:
                issues.append('内容重复度过高')
                score -= 15
                
            # 检查是否包含有意义的内容
            meaningful_chars = re.sub(r'[\s\n\r\t]+', '', content_text)
            if len(meaningful_chars) < 50:
                issues.append('有效内容过少')
                score -= 25
                
        # 检查URL有效性
        url = content.get('url', '')
        if not url or not url.startswith('http'):
            issues.append('URL无效')
            score -= 10
            
        is_valid = score >= 60 and len(issues) <= 2
        return ContentQuality(is_valid=is_valid, score=score, issues=issues)

class DeepFutuDocCrawler:
    def __init__(self, settings: Optional[CrawlerSettings] = None):
        """
        初始化深度爬虫
        
        Args:
            settings: 爬虫配置设置，如果为None则使用默认配置
        """
        self.settings = settings or CrawlerSettings()
        self.quality_checker = ContentQualityChecker()
        
        # 初始化HTTP会话
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.settings.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Referer': 'https://support.futunn.com/'
        })
        
        # URL管理
        self.visited_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.url_cache: Dict[str, str] = {}  # URL内容缓存
        
        # 文档数据存储
        self.docs_data = {
            'zh-cn': {},  # 简体中文
            'zh-hk': {},  # 繁体中文（香港）
            'en': {}      # 英语
        }
        
        # 增强的统计信息
        self.stats = {
            'total_processed': 0,
            'successful_crawls': 0,
            'failed_crawls': 0,
            'categories_found': 0,
            'articles_found': 0,
            'quality_passed': 0,
            'quality_failed': 0,
            'cache_hits': 0,
            'start_time': None,
            'end_time': None
        }
        
        # 设置日志
        self.setup_logging()
        
    def setup_logging(self):
        """设置日志配置"""
        self.logger = logging.getLogger('DeepFutuCrawler')
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            # 文件处理器
            file_handler = logging.FileHandler('deep_crawler.log', encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # 格式化器
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def get_page_content(self, url: str, use_cache: bool = True) -> Optional[BeautifulSoup]:
        """获取页面内容，支持缓存和重试机制"""
        # 检查缓存
        url_hash = hashlib.md5(url.encode()).hexdigest()
        if use_cache and url_hash in self.url_cache:
            self.stats['cache_hits'] += 1
            self.logger.debug(f"使用缓存内容: {url}")
            return BeautifulSoup(self.url_cache[url_hash], 'html.parser')
            
        for attempt in range(self.settings.retries):
            try:
                self.logger.info(f"正在爬取 (尝试 {attempt + 1}/{self.settings.retries}): {url}")
                
                # 智能延迟策略
                if attempt > 0:
                    # 失败重试时使用指数退避
                    delay = min(2 ** attempt, 10)
                else:
                    # 正常请求使用随机延迟
                    delay = random.uniform(*self.settings.delay_range)
                time.sleep(delay)
                
                response = self.session.get(url, timeout=self.settings.timeout)
                response.raise_for_status()
                
                # 检查响应大小
                if len(response.content) > self.settings.max_content_length:
                    self.logger.warning(f"响应内容过大，跳过: {url} ({len(response.content)} bytes)")
                    return None
                    
                # 智能编码检测
                if response.encoding.lower() in ['iso-8859-1', 'windows-1252'] or not response.encoding:
                    response.encoding = 'utf-8'
                    
                # 验证内容类型
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' not in content_type:
                    self.logger.warning(f"非HTML内容，跳过: {url} (Content-Type: {content_type})")
                    return None
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 缓存内容
                if use_cache:
                    self.url_cache[url_hash] = response.text
                    
                self.stats['successful_crawls'] += 1
                return soup
                
            except requests.Timeout:
                self.logger.warning(f"请求超时 (尝试 {attempt + 1}/{self.settings.retries}) {url}")
            except requests.ConnectionError:
                self.logger.warning(f"连接错误 (尝试 {attempt + 1}/{self.settings.retries}) {url}")
            except requests.HTTPError as e:
                if e.response.status_code == 404:
                    self.logger.warning(f"页面不存在: {url}")
                    break  # 404错误不重试
                elif e.response.status_code in [429, 503]:
                    self.logger.warning(f"服务器限流 (尝试 {attempt + 1}/{self.settings.retries}) {url}")
                    time.sleep(5 * (attempt + 1))  # 限流时等待更长时间
                else:
                    self.logger.warning(f"HTTP错误 {e.response.status_code} (尝试 {attempt + 1}/{self.settings.retries}) {url}")
            except Exception as e:
                self.logger.warning(f"未知错误 (尝试 {attempt + 1}/{self.settings.retries}) {url}: {e}")
                
        # 所有重试都失败
        self.logger.error(f"最终爬取失败: {url}")
        self.failed_urls.add(url)
        self.stats['failed_crawls'] += 1
        return None
    
    def extract_content_from_page(self, soup: BeautifulSoup, url: str) -> Dict[str, Union[str, List[str]]]:
        """从页面提取内容，增强的HTML解析精度"""
        content = {
            'title': '',
            'content': '',
            'category': '',
            'tags': [],
            'url': url,
            'crawl_time': datetime.now().isoformat(),
            'language': self.detect_language_from_url(url),
            'meta_description': '',
            'content_hash': '',
            'word_count': 0
        }
        
        # 移除噪音元素
        self._remove_noise_elements(soup)
        
        # 提取标题 - 增强的选择器
        content['title'] = self._extract_title(soup)
        
        # 提取主要内容 - 智能内容提取
        content_text = self._extract_main_content(soup, url)
        content['content'] = self.clean_text(content_text)
        content['word_count'] = len(content['content'].split())
        
        # 生成内容哈希用于去重
        content['content_hash'] = hashlib.md5(content['content'].encode()).hexdigest()
        
        # 提取元数据
        content['meta_description'] = self._extract_meta_description(soup)
        content['category'] = self._extract_category(soup)
        content['tags'] = self._extract_tags(soup)
        
        return content
    
    def _remove_noise_elements(self, soup: BeautifulSoup) -> None:
        """移除页面中的噪音元素"""
        noise_selectors = [
            'script', 'style', 'nav', 'footer', 'header',
            '.advertisement', '.ads', '.sidebar', '.navigation',
            '.feedback-box', '.helpful-box', '.cai-box',
            '.social-share', '.related-articles', '.comments',
            '[data-seo-nofollow="1"]', '.breadcrumb-nav'
        ]
        
        for selector in noise_selectors:
            for element in soup.select(selector):
                element.decompose()
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """提取页面标题"""
        title_selectors = [
            'h1.topic-title',  # 富途特定的标题选择器
            'h1.page-title',
            '.topic-title',
            'h1',
            '.page-title',
            '.content-title',
            '.article-title',
            'title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.get_text().strip():
                title = self.clean_text(title_elem.get_text())
                if len(title) > 3:  # 确保标题有意义
                    self.logger.debug(f"使用选择器 '{selector}' 提取标题: {title[:50]}...")
                    return title
        
        return ''
    
    def _extract_main_content(self, soup: BeautifulSoup, url: str) -> str:
        """智能提取主要内容"""
        # 富途帮助中心特定的内容选择器
        futu_selectors = [
            '.right-topic .futu-richTextContent',
            '.topic-preview .futu-richTextContent',
            '.futu-richTextContent',
            '.right-topic',
            '.topic-preview'
        ]
        
        # 通用内容选择器
        general_selectors = [
            'div.content-box',
            '.content-box',
            '.article-content',
            '.main-content',
            '.content-body',
            '.help-content',
            'main .content',
            'article',
            'main'
        ]
        
        all_selectors = futu_selectors + general_selectors
        
        for selector in all_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 进一步清理内容
                self._clean_content_element(content_elem)
                
                content_text = content_elem.get_text().strip()
                if len(content_text) > self.settings.min_content_length:
                    self.logger.debug(f"使用选择器 '{selector}' 提取内容 ({len(content_text)} 字符)")
                    return content_text
        
        # 如果没有找到合适的内容，尝试提取body中的文本
        body = soup.find('body')
        if body:
            self._clean_content_element(body)
            content_text = body.get_text().strip()
            if len(content_text) > self.settings.min_content_length:
                self.logger.debug(f"使用body标签提取内容 ({len(content_text)} 字符)")
                return content_text
        
        return ''
    
    def _clean_content_element(self, element) -> None:
        """清理内容元素"""
        # 移除不需要的子元素
        unwanted_selectors = [
            'script', 'style', 'nav', 'footer', 'header',
            '.advertisement', '.ads', '.sidebar', '.navigation',
            '.feedback-box', '.helpful-box', '.social-share',
            'button', '.btn', 'input', 'form'
        ]
        
        for selector in unwanted_selectors:
            for unwanted in element.select(selector):
                unwanted.decompose()
    
    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """提取页面描述"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return self.clean_text(meta_desc['content'])
        return ''
    
    def _extract_category(self, soup: BeautifulSoup) -> str:
        """提取分类信息"""
        breadcrumb_selectors = [
            '.breadcrumb',
            '.breadcrumbs', 
            '.nav-breadcrumb',
            '.category-path'
        ]
        
        for selector in breadcrumb_selectors:
            breadcrumb = soup.select_one(selector)
            if breadcrumb:
                return self.clean_text(breadcrumb.get_text())
        
        return ''
    
    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """提取标签"""
        tag_selectors = [
            '.tags a',
            '.tag',
            '.article-tags a',
            '.keywords'
        ]
        
        for selector in tag_selectors:
            tags = soup.select(selector)
            if tags:
                tag_list = [self.clean_text(tag.get_text()) for tag in tags]
                return [tag for tag in tag_list if tag]  # 过滤空标签
        
        return []
    
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
    
    def extract_all_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, List[str]]:
        """提取页面中的所有相关链接"""
        links = {
            'categories': [],
            'articles': [],
            'subcategories': []
        }
        
        base_domain = 'https://support.futunn.com'
        
        for link in soup.select('a[href]'):
            href = link.get('href')
            if not href:
                continue
                
            full_url = urljoin(base_url, href)
            
            # 只处理富途帮助中心的链接
            if not full_url.startswith(base_domain):
                continue
                
            # 分类链接
            if '/categories/' in full_url:
                links['categories'].append(full_url)
                self.stats['categories_found'] += 1
            
            # 文章链接
            elif any(pattern in full_url for pattern in ['/articles/', '/help/', '/learn/']):
                links['articles'].append(full_url)
                self.stats['articles_found'] += 1
            
            # 子分类链接
            elif '/subcategories/' in full_url:
                links['subcategories'].append(full_url)
        
        # 去重
        for key in links:
            links[key] = list(set(links[key]))
            
        return links
    
    def crawl_single_page(self, url: str) -> Optional[Dict]:
        """爬取单个页面，集成质量检测和去重"""
        if url in self.visited_urls:
            self.logger.debug(f"URL已访问，跳过: {url}")
            return None
            
        self.visited_urls.add(url)
        self.stats['total_processed'] += 1
        
        soup = self.get_page_content(url)
        if not soup:
            return None
            
        content = self.extract_content_from_page(soup, url)
        
        # 使用质量检测器验证内容
        quality = self.quality_checker.check_content_quality(content)
        
        if not quality.is_valid:
            self.logger.warning(f"内容质量不足 (评分: {quality.score:.1f}): {url}")
            self.logger.debug(f"质量问题: {', '.join(quality.issues)}")
            self.stats['quality_failed'] += 1
            return None
        
        # 检查内容去重
        content_hash = content.get('content_hash', '')
        if self._is_duplicate_content(content_hash):
            self.logger.warning(f"发现重复内容，跳过: {url}")
            return None
            
        self.stats['quality_passed'] += 1
        self.logger.info(f"成功爬取 (质量评分: {quality.score:.1f}): {content['title'][:50]}...")
        return content
    
    def _is_duplicate_content(self, content_hash: str) -> bool:
        """检查内容是否重复"""
        if not content_hash:
            return False
            
        # 检查所有语言版本中是否已存在相同内容
        for lang_docs in self.docs_data.values():
            for doc in lang_docs.values():
                if doc.get('content_hash') == content_hash:
                    return True
        return False
    
    def deep_crawl_category(self, category_url: str, max_depth: int = 3, max_articles: int = 50) -> List[Dict]:
        """深度爬取分类页面及其所有子页面，优化并发控制和错误处理"""
        self.logger.info(f"开始深度爬取分类: {category_url} (最大深度: {max_depth}, 最大文章数: {max_articles})")
        
        all_content = []
        urls_to_process = [category_url]
        processed_count = 0
        batch_size = min(self.settings.max_workers * 2, 20)  # 限制批次大小
        
        for depth in range(max_depth):
            if not urls_to_process or processed_count >= max_articles:
                break
                
            self.logger.info(f"处理深度 {depth + 1}, 待处理URL数: {len(urls_to_process)}")
            
            current_urls = urls_to_process[:]
            urls_to_process = []
            
            # 分批处理URL，避免过载
            for i in range(0, len(current_urls), batch_size):
                if processed_count >= max_articles:
                    break
                    
                batch_urls = current_urls[i:i + batch_size]
                self.logger.debug(f"处理批次 {i//batch_size + 1}/{(len(current_urls)-1)//batch_size + 1} ({len(batch_urls)} 个URL)")
                
                # 使用线程池并发处理
                with ThreadPoolExecutor(max_workers=self.settings.max_workers) as executor:
                    future_to_url = {executor.submit(self.crawl_single_page, url): url for url in batch_urls}
                    
                    for future in as_completed(future_to_url, timeout=300):  # 5分钟超时
                        if processed_count >= max_articles:
                            break
                            
                        url = future_to_url[future]
                        try:
                            content = future.result(timeout=60)  # 单个任务1分钟超时
                            if content:
                                all_content.append(content)
                                processed_count += 1
                                self.logger.debug(f"成功爬取内容: {content['title'][:30]}...")
                                
                                # 如果是分类页面，提取更多链接
                                if depth < max_depth - 1:
                                    soup = self.get_page_content(url)
                                    if soup:
                                        links = self.extract_all_links(soup, url)
                                        # 添加新发现的链接到下一轮处理
                                        for link_list in links.values():
                                            for link in link_list:
                                                if link not in self.visited_urls:
                                                    urls_to_process.append(link)
                            
                            # 动态延迟控制
                            delay = random.uniform(*self.settings.delay_range)
                            if processed_count % 10 == 0:  # 每10个内容稍作休息
                                delay *= 1.5
                            time.sleep(delay)
                                                
                        except TimeoutError:
                            self.logger.warning(f"处理URL超时: {url}")
                            self.stats['timeout_errors'] = self.stats.get('timeout_errors', 0) + 1
                        except Exception as e:
                            self.logger.error(f"处理URL时出错 {url}: {e}")
                            self.stats['crawl_errors'] = self.stats.get('crawl_errors', 0) + 1
                
                # 批次间休息
                if i + batch_size < len(current_urls) and processed_count < max_articles:
                    batch_delay = random.uniform(2, 5)
                    self.logger.debug(f"批次间休息 {batch_delay:.1f} 秒")
                    time.sleep(batch_delay)
            
            # 去重下一轮要处理的URL
            urls_to_process = list(dict.fromkeys(urls_to_process))  # 保持顺序的去重
            
        self.logger.info(f"分类 {category_url} 深度爬取完成，共获得 {len(all_content)} 篇文档")
        return all_content
    
    def save_documents(self, output_dir: str = 'docs_deep'):
        """保存文档，增强文件保存功能和错误处理"""
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
            json_file = os.path.join(lang_dir, f'futu_docs_deep_{timestamp}.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(docs, f, ensure_ascii=False, indent=2)
                
            # 保存Markdown格式
            md_file = os.path.join(lang_dir, f'futu_docs_deep_{timestamp}.md')
            with open(md_file, 'w', encoding='utf-8') as f:
                lang_names = {
                    'zh-cn': '简体中文',
                    'zh-hk': '繁体中文（香港）',
                    'en': 'English'
                }
                
                f.write(f"# 富途牛牛帮助中心深度爬取文档 - {lang_names.get(lang, lang.upper())}\n\n")
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
                    
            # 保存单个文档文件
            for url, content in docs.items():
                self.save_to_file(content, lang)
                    
            self.logger.info(f"已保存 {lang} 文档: {len(docs)} 篇")
            self.logger.info(f"JSON文件: {json_file}")
            self.logger.info(f"Markdown文件: {md_file}")
    
    def save_to_file(self, content: Dict, language: str = 'zh') -> bool:
        """保存内容到文件，支持多种格式和增强错误处理"""
        try:
            # 创建输出目录
            output_dir = Path(self.settings.output_dir) / f"docs_{language}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成安全的文件名
            title = content.get('title', '未知标题')
            safe_title = self._generate_safe_filename(title)
            
            # 检查文件是否已存在（避免重复保存）
            base_filename = f"{safe_title[:50]}"
            filepath = self._get_unique_filepath(output_dir, base_filename, '.txt')
            
            # 准备文件内容
            file_content = self._format_content_for_file(content)
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(file_content)
                
            # 验证文件写入
            if filepath.exists() and filepath.stat().st_size > 0:
                self.logger.info(f"内容已保存到: {filepath} ({filepath.stat().st_size} 字节)")
                self.stats['files_saved'] = self.stats.get('files_saved', 0) + 1
                return True
            else:
                self.logger.error(f"文件保存失败或文件为空: {filepath}")
                return False
                
        except PermissionError:
            self.logger.error(f"没有权限写入文件: {filepath}")
            return False
        except OSError as e:
            self.logger.error(f"文件系统错误: {e}")
            return False
        except Exception as e:
            self.logger.error(f"保存文件时出错: {e}")
            return False
    
    def _generate_safe_filename(self, title: str) -> str:
        """生成安全的文件名"""
        # 移除或替换非法字符
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        safe_title = re.sub(r'[\s]+', '_', safe_title)  # 多个空格替换为单个下划线
        safe_title = safe_title.strip('._')  # 移除开头和结尾的点和下划线
        
        # 确保文件名不为空
        if not safe_title:
            safe_title = f"document_{int(time.time())}"
            
        return safe_title
    
    def _get_unique_filepath(self, directory: Path, base_name: str, extension: str) -> Path:
        """获取唯一的文件路径，避免覆盖"""
        filepath = directory / f"{base_name}{extension}"
        counter = 1
        
        while filepath.exists():
            filepath = directory / f"{base_name}_{counter}{extension}"
            counter += 1
            
        return filepath
    
    def _format_content_for_file(self, content: Dict) -> str:
        """格式化内容用于文件保存"""
        lines = []
        
        # 基本信息
        lines.append(f"标题: {content.get('title', '未知标题')}")
        lines.append(f"URL: {content.get('url', '')}")
        lines.append(f"分类: {content.get('category', '未知')}")
        
        # 标签
        tags = content.get('tags', [])
        if tags:
            lines.append(f"标签: {', '.join(tags)}")
        
        # 元数据
        if content.get('meta_description'):
            lines.append(f"描述: {content['meta_description']}")
        
        lines.append(f"字数: {content.get('word_count', 0)}")
        lines.append(f"内容哈希: {content.get('content_hash', '')}")
        lines.append(f"爬取时间: {content.get('crawl_time', '')}")
        
        # 分隔线
        lines.append("\n" + "="*80 + "\n")
        
        # 主要内容
        main_content = content.get('content', '')
        if isinstance(main_content, list):
            main_content = '\n\n'.join(main_content)
        
        lines.append(main_content)
        
        return '\n'.join(lines)
    
    def run_deep_crawl(self, urls: List[str], max_depth: int = 3, max_articles_per_category: int = 50):
        """运行深度爬虫，增加统计信息和性能监控"""
        self.stats['start_time'] = time.time()
        self.logger.info("开始运行深度富途牛牛帮助中心文档爬虫...")
        self.logger.info(f"目标URL数量: {len(urls)}")
        self.logger.info(f"最大深度: {max_depth}")
        self.logger.info(f"每个分类最大文章数: {max_articles_per_category}")
        self.logger.info(f"并发设置: 最大工作线程={self.settings.max_workers}, 延迟范围={self.settings.delay_range}")
        
        successful_categories = 0
        failed_categories = 0
        
        for i, url in enumerate(urls, 1):
            category_start_time = time.time()
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"处理第 {i}/{len(urls)} 个分类: {url}")
            
            try:
                # 检测语言
                lang = self.detect_language_from_url(url)
                self.logger.info(f"检测到语言: {lang}")
                
                # 深度爬取分类和文章
                articles = self.deep_crawl_category(url, max_depth, max_articles_per_category)
                
                if articles:
                    successful_categories += 1
                    category_time = time.time() - category_start_time
                    self.logger.info(f"分类 {i} 完成，耗时 {category_time:.1f}秒，获得 {len(articles)} 篇文章")
                    
                    # 保存到对应语言的数据中
                    for article in articles:
                        self.docs_data[lang][article['url']] = article
                        
                    # 实时统计更新
                    self.stats['categories_processed'] = successful_categories
                    self.stats['total_articles'] = sum(len(docs) for docs in self.docs_data.values())
                    
                else:
                    failed_categories += 1
                    self.logger.warning(f"分类 {i} 未获取到任何文章")
                    
            except KeyboardInterrupt:
                self.logger.info("用户中断爬取过程")
                break
            except Exception as e:
                failed_categories += 1
                self.logger.error(f"深度爬取失败 {url}: {e}")
                self.stats['category_errors'] = self.stats.get('category_errors', 0) + 1
                
            # 分类间休息
            if i < len(urls):
                inter_category_delay = random.uniform(3, 8)
                self.logger.info(f"分类间休息 {inter_category_delay:.1f} 秒")
                time.sleep(inter_category_delay)
        
        # 记录结束时间
        self.stats['end_time'] = time.time()
        total_time = self.stats['end_time'] - self.stats['start_time']
        
        # 保存文档
        self.logger.info(f"\n{'='*60}")
        self.logger.info("开始保存文档...")
        try:
            self.save_documents()
            self.logger.info("文档保存完成")
        except Exception as e:
            self.logger.error(f"保存文档时出错: {e}")
        
        # 输出详细统计信息
        self._print_final_statistics(successful_categories, failed_categories, total_time)
        
        return self.docs_data, self.stats
    
    def _print_final_statistics(self, successful_categories: int, failed_categories: int, total_time: float):
        """打印最终统计信息"""
        total_docs = sum(len(docs) for docs in self.docs_data.values())
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info("🎉 深度爬取完成！")
        self.logger.info(f"\n📊 总体统计:")
        self.logger.info(f"  ⏱️  总耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")
        self.logger.info(f"  📁 成功分类: {successful_categories}")
        self.logger.info(f"  ❌ 失败分类: {failed_categories}")
        self.logger.info(f"  📄 总文档数: {total_docs} 篇")
        
        if total_docs > 0:
            avg_time_per_doc = total_time / total_docs
            self.logger.info(f"  ⚡ 平均每篇: {avg_time_per_doc:.1f} 秒")
        
        self.logger.info(f"\n🌍 语言分布:")
        lang_names = {
            'zh-cn': '简体中文',
            'zh-hk': '繁体中文（香港）',
            'en': 'English'
        }
        for lang, docs in self.docs_data.items():
            percentage = (len(docs) / total_docs * 100) if total_docs > 0 else 0
            lang_display = lang_names.get(lang, lang)
            self.logger.info(f"  {lang_display}: {len(docs)} 篇 ({percentage:.1f}%)")
        
        self.logger.info(f"\n🔧 性能统计:")
        self.logger.info(f"  📊 总处理数: {self.stats.get('total_processed', 0)}")
        self.logger.info(f"  ✅ 成功爬取: {self.stats.get('successful_crawls', 0)}")
        self.logger.info(f"  ❌ 失败爬取: {self.stats.get('failed_crawls', 0)}")
        self.logger.info(f"  ✅ 质量通过: {self.stats.get('quality_passed', 0)}")
        self.logger.info(f"  ❌ 质量失败: {self.stats.get('quality_failed', 0)}")
        self.logger.info(f"  💾 缓存命中: {self.stats.get('cache_hits', 0)}")
        self.logger.info(f"  💾 文件保存: {self.stats.get('files_saved', 0)}")
        self.logger.info(f"  🔍 发现分类: {self.stats.get('categories_found', 0)}")
        self.logger.info(f"  📰 发现文章: {self.stats.get('articles_found', 0)}")
        
        if self.stats.get('crawl_errors', 0) > 0:
            self.logger.info(f"  ⚠️  爬取错误: {self.stats.get('crawl_errors', 0)}")
        if self.stats.get('timeout_errors', 0) > 0:
            self.logger.info(f"  ⏰ 超时错误: {self.stats.get('timeout_errors', 0)}")
        if self.stats.get('category_errors', 0) > 0:
            self.logger.info(f"  📁 分类错误: {self.stats.get('category_errors', 0)}")
        
        self.logger.info(f"\n📁 输出目录: docs_deep/")
        self.logger.info(f"{'='*60}")