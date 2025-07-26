# 🚀 Crawl4AI 富途文档爬虫

基于 [Crawl4AI](https://docs.crawl4ai.com/) 框架的高性能富途牛牛帮助文档爬虫工具。

## ✨ 主要特性

### 🔥 Crawl4AI 优势
- **🤖 AI 友好**: 专为 LLM 和 AI 应用设计的内容提取
- **⚡ 高性能**: 异步并发爬取，速度提升 10x+
- **🧠 智能提取**: 自动识别和提取结构化内容
- **🌐 多语言**: 自动检测和分类中英文内容
- **📊 结构化输出**: JSON + Markdown 双格式导出

### 🛠️ 技术特性
- **异步爬取**: 基于 `asyncio` 的高并发处理
- **智能重试**: 自动错误恢复和重试机制
- **内容分块**: 使用 `RegexChunking` 优化大文档处理
- **语义提取**: `CosineStrategy` 提取最相关内容
- **实时监控**: 详细的进度跟踪和性能统计

## 📦 安装依赖

```bash
# 安装 Crawl4AI 和相关依赖
pip install crawl4ai>=0.7.0 aiohttp>=3.8.0 aiofiles>=23.0.0

# 安装其他依赖
pip install -r requirements.txt
```

## 🚀 快速开始

### 1. 基础演示

```bash
# 运行基础演示
python demo_crawl4ai.py
```

### 2. 自定义爬取

```bash
# 指定自定义URL
python demo_crawl4ai.py --urls https://support.futunn.com/categories/2186

# 高并发模式
python demo_crawl4ai.py --max-concurrent 10 --max-depth 3

# 多语言爬取
python demo_crawl4ai.py --urls \
  https://support.futunn.com/categories/2186 \
  https://support.futunn.com/en/categories/2186
```

### 3. GUI 界面

```bash
# 启动 Crawl4AI GUI
python main_crawl4ai.py

# 或使用原版GUI
python main.py
```

## 📋 使用方式对比

| 特性 | 原版爬虫 | Crawl4AI 爬虫 |
|------|----------|---------------|
| **性能** | 同步，较慢 | 异步，10x+ 速度提升 |
| **内容质量** | 基础HTML解析 | AI优化的智能提取 |
| **并发处理** | 线程池 | 原生异步协程 |
| **错误处理** | 基础重试 | 智能恢复机制 |
| **输出格式** | JSON | JSON + Markdown |
| **语言支持** | 手动分类 | 自动检测分类 |
| **内存使用** | 较高 | 优化的流式处理 |

## ⚙️ 配置参数

### Crawl4AI 设置

```python
from src.core.crawl4ai_crawler import Crawl4AISettings

settings = Crawl4AISettings(
    max_concurrent=5,        # 最大并发数
    delay_range=(1.0, 2.0),  # 请求延迟范围(秒)
    timeout=30,              # 请求超时时间
    output_dir='output',     # 输出目录
    headless=True,           # 无头浏览器模式
    enable_js=True,          # 启用JavaScript
    screenshot=False,        # 是否截图
    wait_for_images=False    # 是否等待图片加载
)
```

### 爬取参数

```python
results, info = await run_crawl4ai_crawler(
    urls=['https://support.futunn.com/categories/2186'],
    max_depth=2,             # 最大爬取深度
    settings=settings
)
```

## 📊 输出格式

### JSON 格式
```json
{
  "url": "https://support.futunn.com/articles/123",
  "title": "如何开户",
  "content": "详细的开户流程...",
  "language": "zh",
  "links": ["https://..."],
  "crawl_time": "2024-01-01T12:00:00",
  "success": true
}
```

### Markdown 格式
```markdown
# 如何开户

**URL**: https://support.futunn.com/articles/123  
**语言**: 中文  
**爬取时间**: 2024-01-01 12:00:00

## 内容

详细的开户流程...

## 相关链接
- [链接1](https://...)
- [链接2](https://...)
```

## 🔧 API 使用

### 基础用法

```python
import asyncio
from src.core.crawl4ai_crawler import run_crawl4ai_crawler, Crawl4AISettings

async def main():
    # 配置设置
    settings = Crawl4AISettings(
        max_concurrent=3,
        output_dir='my_output'
    )
    
    # 运行爬取
    results, info = await run_crawl4ai_crawler(
        urls=['https://support.futunn.com/categories/2186'],
        max_depth=2,
        settings=settings
    )
    
    # 处理结果
    for result in results:
        if result.success:
            print(f"成功爬取: {result.title}")
            print(f"内容长度: {len(result.content)}")
        else:
            print(f"爬取失败: {result.url} - {result.error}")
    
    # 查看统计信息
    stats = info['stats']
    print(f"总共处理: {stats['total_processed']} 页面")
    print(f"成功爬取: {stats['successful_crawls']} 页面")

# 运行
asyncio.run(main())
```

### 高级用法

```python
from src.core.crawl4ai_crawler import Crawl4AIFutuCrawler, Crawl4AISettings

async def advanced_crawl():
    # 创建爬虫实例
    settings = Crawl4AISettings(
        max_concurrent=10,
        delay_range=(0.5, 1.0),
        enable_js=True,
        screenshot=True  # 启用截图
    )
    
    crawler = Crawl4AIFutuCrawler(settings)
    
    # 单页面爬取
    result = await crawler.crawl_single_page(
        "https://support.futunn.com/articles/123"
    )
    
    if result.success:
        print(f"标题: {result.title}")
        print(f"语言: {result.language}")
        print(f"链接数: {len(result.links)}")
    
    # 批量爬取
    urls = [
        "https://support.futunn.com/categories/2186",
        "https://support.futunn.com/categories/2187"
    ]
    
    all_results = await crawler.crawl_batch_urls(
        urls, max_depth=3
    )
    
    # 保存结果
    saved_files = await crawler.save_results(
        all_results, output_dir="advanced_output"
    )
    
    print(f"保存的文件: {saved_files}")

asyncio.run(advanced_crawl())
```

## 📈 性能优化

### 1. 并发调优
```python
# 高性能设置（适合服务器环境）
settings = Crawl4AISettings(
    max_concurrent=20,       # 高并发
    delay_range=(0.1, 0.5), # 短延迟
    timeout=60,              # 长超时
    headless=True,           # 无头模式
    wait_for_images=False    # 跳过图片
)

# 稳定设置（适合个人电脑）
settings = Crawl4AISettings(
    max_concurrent=5,        # 中等并发
    delay_range=(1.0, 2.0), # 适中延迟
    timeout=30,              # 标准超时
    headless=True,
    enable_js=True
)
```

### 2. 内存优化
```python
# 大规模爬取时的内存优化
settings = Crawl4AISettings(
    max_concurrent=3,        # 降低并发
    screenshot=False,        # 禁用截图
    wait_for_images=False,   # 跳过图片
    # 使用流式处理
)

# 分批处理大量URL
urls = [...]  # 大量URL列表
batch_size = 50

for i in range(0, len(urls), batch_size):
    batch_urls = urls[i:i+batch_size]
    results, _ = await run_crawl4ai_crawler(
        urls=batch_urls,
        max_depth=1,
        settings=settings
    )
    # 处理当前批次结果
    process_batch_results(results)
```

## 🐛 故障排除

### 常见问题

1. **安装问题**
```bash
# 如果 crawl4ai 安装失败
pip install --upgrade pip
pip install crawl4ai --no-cache-dir

# 或使用conda
conda install -c conda-forge crawl4ai
```

2. **浏览器问题**
```python
# 如果浏览器启动失败，尝试禁用JS
settings = Crawl4AISettings(
    enable_js=False,
    headless=True
)
```

3. **内存不足**
```python
# 降低并发数和启用流式处理
settings = Crawl4AISettings(
    max_concurrent=2,
    screenshot=False,
    wait_for_images=False
)
```

4. **网络超时**
```python
# 增加超时时间和重试
settings = Crawl4AISettings(
    timeout=60,
    delay_range=(2.0, 5.0)
)
```

### 调试模式

```python
import logging

# 启用详细日志
logging.basicConfig(level=logging.DEBUG)

# 或在代码中设置
crawler = Crawl4AIFutuCrawler(settings)
crawler.logger.setLevel(logging.DEBUG)
```

## 📝 更新日志

### v2.0.0 (Crawl4AI版本)
- ✅ 集成 Crawl4AI 框架
- ✅ 异步并发爬取
- ✅ AI 优化的内容提取
- ✅ 自动语言检测
- ✅ 结构化输出格式
- ✅ 实时进度监控
- ✅ 智能错误恢复

### v1.0.0 (原版)
- ✅ 基础HTML解析
- ✅ 多线程爬取
- ✅ GUI界面
- ✅ JSON输出

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🔗 相关链接

- [Crawl4AI 官方文档](https://docs.crawl4ai.com/)
- [富途牛牛帮助中心](https://support.futunn.com/)
- [项目仓库](https://github.com/your-repo/fetchFutuDoc)