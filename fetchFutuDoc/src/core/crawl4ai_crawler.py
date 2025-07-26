#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 Crawl4AI 的富途牛牛帮助中心优化爬虫
Optimized Futu Help Center Crawler using Crawl4AI Framework

特性:
- 使用 Crawl4AI 的异步爬取能力
- AI 友好的内容提取
- 智能适应性爬取
- 高性能并发处理
- 结构化数据提取
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
import logging
import hashlib
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field

try:
    from crawl4ai import AsyncWebCrawler
    from crawl4ai.extraction_strategy import LLMExtractionStrategy, CosineStrategy
    from crawl4ai.chunking_strategy import RegexChunking
except ImportError:
    print("请安装 Crawl4AI: pip install crawl4ai")
    raise

@dataclass
class Crawl4AISettings:
    """Crawl4AI 爬虫配置设置"""
    max_concurrent: int = 5
    delay_range: Tuple[float, float] = (1.0, 2.0)
    timeout: int = 30
    retries: int = 3
    output_dir: str = 'docs_crawl4ai'
    headless: bool = True
    user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    enable_js: bool = True
    wait_for_images: bool = False
    screenshot: bool = False
    
@dataclass
class CrawlResult:
    """爬取结果数据结构"""
    url: str
    title: str
    content: str
    markdown: str
    links: List[str]
    images: List[str]
    metadata: Dict
    language: str
    success: bool
    error: Optional[str] = None
    crawl_time: str = field(default_factory=lambda: datetime.now().isoformat())
    content_hash: str = field(default='')
    
    def __post_init__(self):
        if self.content:
            self.content_hash = hashlib.md5(self.content.encode()).hexdigest()

class Crawl4AIFutuCrawler:
    """基于 Crawl4AI 的富途文档爬虫"""
    
    def __init__(self, settings: Optional[Crawl4AISettings] = None):
        self.settings = settings or Crawl4AISettings()
        self.visited_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.results: List[CrawlResult] = []
        
        # 统计信息
        self.stats = {
            'total_processed': 0,
            'successful_crawls': 0,
            'failed_crawls': 0,
            'start_time': None,
            'end_time': None,
            'total_content_length': 0,
            'unique_pages': 0
        }
        
        self.setup_logging()
        
    def setup_logging(self):
        """设置日志配置"""
        self.logger = logging.getLogger('Crawl4AIFutuCrawler')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            # 文件处理器
            file_handler = logging.FileHandler('crawl4ai_crawler.log', encoding='utf-8')
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
    
    def detect_language_from_url(self, url: str) -> str:
        """从URL检测语言"""
        if '/hant/' in url or '/zh-hk/' in url:
            return 'zh-hk'
        elif '/en/' in url:
            return 'en'
        else:
            return 'zh-cn'
    
    async def crawl_single_page(self, crawler: AsyncWebCrawler, url: str) -> CrawlResult:
        """爬取单个页面"""
        try:
            self.logger.info(f"正在爬取: {url}")
            
            # 使用 Crawl4AI 进行爬取
            result = await crawler.arun(
                url=url,
                word_count_threshold=10,
                extraction_strategy=CosineStrategy(
                    semantic_filter="帮助文档内容、教程、说明",
                    word_count_threshold=10,
                    max_dist=0.2,
                    linkage_method='ward',
                    top_k=3
                ),
                chunking_strategy=RegexChunking(),
                bypass_cache=False,
                include_raw_html=False,
                screenshot=self.settings.screenshot,
                wait_for_images=self.settings.wait_for_images
            )
            
            if result.success:
                # 提取链接
                links = self._extract_links_from_markdown(result.markdown, url)
                
                # 创建结果对象
                crawl_result = CrawlResult(
                    url=url,
                    title=result.metadata.get('title', ''),
                    content=result.cleaned_html or result.markdown,
                    markdown=result.markdown,
                    links=links,
                    images=result.media.get('images', []) if result.media else [],
                    metadata=result.metadata,
                    language=self.detect_language_from_url(url),
                    success=True
                )
                
                self.stats['successful_crawls'] += 1
                self.stats['total_content_length'] += len(crawl_result.content)
                self.logger.info(f"成功爬取: {url} ({len(crawl_result.content)} 字符)")
                
                return crawl_result
            else:
                error_msg = f"Crawl4AI 爬取失败: {result.error_message if hasattr(result, 'error_message') else '未知错误'}"
                self.logger.error(f"爬取失败 {url}: {error_msg}")
                self.stats['failed_crawls'] += 1
                
                return CrawlResult(
                    url=url,
                    title='',
                    content='',
                    markdown='',
                    links=[],
                    images=[],
                    metadata={},
                    language=self.detect_language_from_url(url),
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            error_msg = f"异常错误: {str(e)}"
            self.logger.error(f"爬取异常 {url}: {error_msg}")
            self.stats['failed_crawls'] += 1
            
            return CrawlResult(
                url=url,
                title='',
                content='',
                markdown='',
                links=[],
                images=[],
                metadata={},
                language=self.detect_language_from_url(url),
                success=False,
                error=error_msg
            )
    
    def _extract_links_from_markdown(self, markdown: str, base_url: str) -> List[str]:
        """从 Markdown 内容中提取链接"""
        import re
        
        # 提取 Markdown 链接
        link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        matches = re.findall(link_pattern, markdown)
        
        links = []
        for text, url in matches:
            # 转换为绝对URL
            absolute_url = urljoin(base_url, url)
            if self._is_valid_futu_url(absolute_url):
                links.append(absolute_url)
        
        return list(set(links))  # 去重
    
    def _is_valid_futu_url(self, url: str) -> bool:
        """检查是否为有效的富途URL"""
        return (
            url.startswith('https://support.futunn.com/') and
            not any(skip in url for skip in ['#', 'javascript:', 'mailto:', '.pdf', '.jpg', '.png'])
        )
    
    async def crawl_urls(self, urls: List[str], max_depth: int = 2) -> List[CrawlResult]:
        """批量爬取URL列表"""
        self.stats['start_time'] = datetime.now()
        
        async with AsyncWebCrawler(
            headless=self.settings.headless,
            verbose=True,
            user_agent=self.settings.user_agent
        ) as crawler:
            
            # 第一轮：爬取初始URL
            self.logger.info(f"开始爬取 {len(urls)} 个初始URL")
            
            semaphore = asyncio.Semaphore(self.settings.max_concurrent)
            
            async def crawl_with_semaphore(url):
                async with semaphore:
                    if url not in self.visited_urls:
                        self.visited_urls.add(url)
                        result = await self.crawl_single_page(crawler, url)
                        self.results.append(result)
                        self.stats['total_processed'] += 1
                        
                        # 添加延迟
                        await asyncio.sleep(
                            __import__('random').uniform(*self.settings.delay_range)
                        )
                        
                        return result
                    return None
            
            # 执行初始URL爬取
            tasks = [crawl_with_semaphore(url) for url in urls]
            initial_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 深度爬取
            current_depth = 1
            while current_depth < max_depth:
                self.logger.info(f"开始第 {current_depth + 1} 层深度爬取")
                
                # 收集新发现的链接
                new_urls = set()
                for result in self.results:
                    if result and result.success:
                        for link in result.links:
                            if link not in self.visited_urls and self._is_valid_futu_url(link):
                                new_urls.add(link)
                
                if not new_urls:
                    self.logger.info("没有发现新的链接，停止深度爬取")
                    break
                
                self.logger.info(f"发现 {len(new_urls)} 个新链接")
                
                # 爬取新链接
                tasks = [crawl_with_semaphore(url) for url in new_urls]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                current_depth += 1
        
        self.stats['end_time'] = datetime.now()
        self.stats['unique_pages'] = len(set(r.url for r in self.results if r.success))
        
        self.logger.info(f"爬取完成！总计处理 {self.stats['total_processed']} 个页面")
        self.logger.info(f"成功: {self.stats['successful_crawls']}, 失败: {self.stats['failed_crawls']}")
        
        return self.results
    
    def save_results(self, output_dir: Optional[str] = None) -> Dict[str, str]:
        """保存爬取结果"""
        output_dir = output_dir or self.settings.output_dir
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 按语言分组保存
        language_groups = {'zh-cn': [], 'zh-hk': [], 'en': []}
        
        for result in self.results:
            if result.success and result.content.strip():
                language_groups[result.language].append(result)
        
        saved_files = {}
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for lang, results in language_groups.items():
            if results:
                # 保存 JSON 格式
                json_filename = f'futu_docs_crawl4ai_{lang}_{timestamp}.json'
                json_path = output_path / json_filename
                
                json_data = {
                    'metadata': {
                        'crawl_time': timestamp,
                        'total_pages': len(results),
                        'language': lang,
                        'crawler': 'Crawl4AI',
                        'stats': self.stats
                    },
                    'documents': []
                }
                
                for result in results:
                    json_data['documents'].append({
                        'url': result.url,
                        'title': result.title,
                        'content': result.content,
                        'markdown': result.markdown,
                        'metadata': result.metadata,
                        'crawl_time': result.crawl_time,
                        'content_hash': result.content_hash,
                        'links_count': len(result.links),
                        'images_count': len(result.images)
                    })
                
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                
                # 保存 Markdown 格式
                md_filename = f'futu_docs_crawl4ai_{lang}_{timestamp}.md'
                md_path = output_path / md_filename
                
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(f"# 富途牛牛帮助文档 ({lang.upper()})\n\n")
                    f.write(f"爬取时间: {timestamp}\n")
                    f.write(f"文档数量: {len(results)}\n")
                    f.write(f"爬虫: Crawl4AI\n\n")
                    f.write("---\n\n")
                    
                    for i, result in enumerate(results, 1):
                        f.write(f"## {i}. {result.title}\n\n")
                        f.write(f"**URL:** {result.url}\n\n")
                        f.write(f"**爬取时间:** {result.crawl_time}\n\n")
                        
                        if result.markdown:
                            f.write(result.markdown)
                        else:
                            f.write(result.content)
                        
                        f.write("\n\n---\n\n")
                
                saved_files[lang] = {
                    'json': str(json_path),
                    'markdown': str(md_path),
                    'count': len(results)
                }
                
                self.logger.info(f"已保存 {lang} 文档: {len(results)} 篇")
        
        # 保存统计信息
        stats_path = output_path / f'crawl_stats_{timestamp}.json'
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2, default=str)
        
        return saved_files
    
    def get_stats(self) -> Dict:
        """获取爬取统计信息"""
        return self.stats.copy()

# 异步运行函数
async def run_crawl4ai_crawler(
    urls: List[str],
    max_depth: int = 2,
    settings: Optional[Crawl4AISettings] = None
) -> Tuple[List[CrawlResult], Dict]:
    """运行 Crawl4AI 爬虫的异步函数"""
    crawler = Crawl4AIFutuCrawler(settings)
    results = await crawler.crawl_urls(urls, max_depth)
    saved_files = crawler.save_results()
    stats = crawler.get_stats()
    
    return results, {'saved_files': saved_files, 'stats': stats}

# 同步包装函数
def run_crawl4ai_sync(
    urls: List[str],
    max_depth: int = 2,
    settings: Optional[Crawl4AISettings] = None
) -> Tuple[List[CrawlResult], Dict]:
    """同步运行 Crawl4AI 爬虫"""
    return asyncio.run(run_crawl4ai_crawler(urls, max_depth, settings))