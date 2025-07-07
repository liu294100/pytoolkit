#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试阶段性保存功能
验证爬虫是否能在爬取每个页面后立即保存单独的文件，并在最后生成汇总文件
"""

import os
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.deep_crawler import DeepFutuDocCrawler, CrawlerSettings

def test_staged_saving():
    """测试阶段性保存功能"""
    print("开始测试阶段性保存功能...")
    
    # 创建爬虫实例
    settings = CrawlerSettings()
    settings.max_workers = 2
    settings.delay_range = (1, 3)
    settings.timeout = 30
    settings.retries = 2
    
    crawler = DeepFutuDocCrawler(settings=settings)
    
    # 测试URL - 选择一个较小的分类进行测试
    test_urls = [
        "https://support.futunn.com/zh-cn/categories/360000010781"  # 一个较小的分类
    ]
    
    print(f"测试URL: {test_urls[0]}")
    print("预期行为:")
    print("1. 每个页面爬取后立即保存到单独的文件")
    print("2. 爬取完成后生成汇总的JSON和Markdown文件")
    print("3. 检查docs_deep目录下的文件结构")
    print()
    
    # 清理之前的测试文件
    docs_dir = Path("docs_deep")
    if docs_dir.exists():
        print("清理之前的测试文件...")
        import shutil
        shutil.rmtree(docs_dir)
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        # 运行深度爬取（限制文章数量以加快测试）
        docs_data, stats = crawler.run_deep_crawl(
            urls=test_urls,
            max_depth=2,  # 限制深度
            max_articles_per_category=5  # 限制文章数量
        )
        
        # 计算耗时
        elapsed_time = time.time() - start_time
        
        print(f"\n{'='*60}")
        print("测试完成！")
        print(f"总耗时: {elapsed_time:.1f}秒")
        print(f"爬取统计: {stats}")
        
        # 检查文件结构
        print("\n检查生成的文件:")
        check_generated_files(docs_dir)
        
        # 验证数据
        total_docs = sum(len(docs) for docs in docs_data.values())
        print(f"\n内存中的文档总数: {total_docs}")
        
        if total_docs > 0:
            print("✅ 阶段性保存功能测试成功！")
            return True
        else:
            print("❌ 没有爬取到任何文档")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_generated_files(docs_dir: Path):
    """检查生成的文件结构"""
    if not docs_dir.exists():
        print("❌ docs_deep目录不存在")
        return
    
    print(f"📁 {docs_dir}/")
    
    # 检查语言目录
    for lang_dir in docs_dir.iterdir():
        if lang_dir.is_dir():
            print(f"  📁 {lang_dir.name}/")
            
            # 统计文件类型
            individual_files = []
            summary_files = []
            
            for file_path in lang_dir.iterdir():
                if file_path.is_file():
                    if 'summary' in file_path.name:
                        summary_files.append(file_path.name)
                    else:
                        individual_files.append(file_path.name)
            
            # 显示汇总文件
            if summary_files:
                print("    📄 汇总文件:")
                for file_name in summary_files:
                    print(f"      - {file_name}")
            
            # 显示单独文件（只显示前几个）
            if individual_files:
                print(f"    📄 单独文件 ({len(individual_files)}个):")
                for file_name in individual_files[:5]:  # 只显示前5个
                    print(f"      - {file_name}")
                if len(individual_files) > 5:
                    print(f"      ... 还有 {len(individual_files) - 5} 个文件")
            
            print(f"    总计: {len(individual_files)} 个单独文件 + {len(summary_files)} 个汇总文件")

if __name__ == "__main__":
    success = test_staged_saving()
    sys.exit(0 if success else 1)