# 富途牛牛帮助中心深度文档爬虫

## 项目简介

这是一个专门用于深度爬取富途牛牛帮助中心文档的Python工具，支持多语言文档生成和图形界面操作，包括：
- 简体中文 (zh-cn)
- 繁体中文香港 (zh-hk) 
- 英语 (en)

## 功能特性

- 🌐 **多语言支持**：自动检测并分类中文简体、繁体（香港）和英语内容
- 🔍 **深度爬取**：递归爬取分类下的所有子分类和文章链接
- 📚 **智能内容提取**：优先提取`content-box`区域内容，自动识别文章标题、正文
- 🖥️ **图形界面**：提供友好的GUI界面，支持参数配置和实时日志显示
- 🔄 **自动重试机制**：网络请求失败时自动重试，提高爬取成功率
- 📁 **多格式输出**：同时生成JSON和Markdown格式的文档
- ⚡ **并发控制**：支持多线程并发爬取，可配置线程数和延迟范围
- 🎯 **智能去重**：自动去除重复的URL和内容
- ⚙️ **配置管理**：支持配置文件管理和预设配置模板

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 快速开始

#### 1. GUI模式（推荐）

```bash
# 启动图形界面
python main.py
```

#### 2. 命令行模式

```bash
# 使用默认参数
python main.py --cli

# 自定义参数
python main.py --cli --max-depth 2 --max-articles 30 --max-workers 5

# 指定特定URL
python main.py --cli --urls https://support.futunn.com/categories/2186
```

### GUI界面使用

1. **配置目标URL**：在URL配置区域输入要爬取的分类URL
2. **设置爬取参数**：
   - 最大深度：递归爬取的层级深度（1-5）
   - 每分类最大文章数：限制每个分类爬取的文章数量
   - 并发线程数：同时运行的爬取线程数
   - 延迟范围：请求间隔时间范围
   - 输出目录：文档保存位置
3. **开始爬取**：点击"开始深度爬取"按钮
4. **监控进度**：实时查看爬取日志和进度

### 编程接口使用

```python
from src.core.deep_crawler import DeepFutuDocCrawler

# 创建深度爬虫实例
crawler = DeepFutuDocCrawler(
    max_workers=3,
    delay_range=(1.0, 3.0)
)

# 自定义目标URL
target_urls = [
    'https://support.futunn.com/categories/2186',  # 基础知识入门
    'https://support.futunn.com/categories/2185',  # 市场介绍
    'https://support.futunn.com/hant/categories/2186',  # 繁体版本
    'https://support.futunn.com/en/categories/2186',  # 英语版本
]

# 运行深度爬取
docs_data, stats = crawler.run_deep_crawl(
    urls=target_urls,
    max_depth=3,
    max_articles_per_category=50
)

print(f"爬取完成！总文档数: {sum(len(docs) for docs in docs_data.values())}")
```

### 配置文件使用

```python
from src.utils.config import CrawlerConfig, ConfigManager

# 创建配置管理器
config_manager = ConfigManager()

# 创建自定义配置
config = CrawlerConfig(
    max_depth=4,
    max_articles_per_category=100,
    max_workers=2,
    delay_min=2.0,
    delay_max=5.0
)

# 保存配置
config_manager.save_config(config, "my_config.json")

# 加载配置
loaded_config = config_manager.load_config("my_config.json")
```

## 项目结构

```
fetchFutuDoc/
├── main.py                 # 主启动脚本
├── requirements.txt        # 依赖包列表
├── README.md              # 项目说明文档
├── config.json            # 基础配置文件
├── src/                   # 源代码目录
│   ├── __init__.py
│   ├── core/              # 核心爬虫模块
│   │   ├── __init__.py
│   │   └── deep_crawler.py # 深度爬虫实现
│   ├── gui/               # 图形界面模块
│   │   ├── __init__.py
│   │   └── main_window.py  # 主窗口界面
│   └── utils/             # 工具模块
│       ├── __init__.py
│       └── config.py       # 配置管理
├── config/                # 配置文件目录
│   ├── crawler_config.json
│   ├── preset_quick.json
│   ├── preset_standard.json
│   ├── preset_deep.json
│   └── preset_comprehensive.json
├── docs_deep/             # 深度爬取输出目录
│   ├── zh-cn/
│   ├── zh-hk/
│   └── en/
└── legacy/                # 旧版本文件
    ├── futu_doc_crawler.py
    ├── enhanced_crawler.py
    ├── multilang_crawler.py
    └── test_multilang_crawler.py
```

## 输出结构

爬取完成后，会在指定输出目录下生成以下结构：

```
docs_deep/
├── zh-cn/          # 简体中文文档
│   ├── futu_docs_deep_20240101_120000.json
│   └── futu_docs_deep_20240101_120000.md
├── zh-hk/          # 繁体中文（香港）文档
│   ├── futu_docs_deep_20240101_120000.json
│   └── futu_docs_deep_20240101_120000.md
└── en/             # 英语文档
    ├── futu_docs_deep_20240101_120000.json
    └── futu_docs_deep_20240101_120000.md
```

## 配置选项

### 主要参数

- `max_depth`: 最大爬取深度（1-5，默认：3）
- `max_articles_per_category`: 每个分类最大爬取文章数（默认：50）
- `max_workers`: 并发线程数（1-20，默认：3）
- `delay_range`: 请求延迟范围，元组格式（默认：(1.0, 3.0)）
- `output_dir`: 输出目录（默认：'docs_deep'）

### 网络配置

- 请求超时：30秒
- 重试次数：3次
- 重试延迟：1秒
- User-Agent：模拟Chrome浏览器

### 内容过滤

- 最小内容长度：100字符
- 最大内容长度：50000字符
- 优先提取区域：`div.content-box`

### 预设配置

- **quick**: 快速爬取（深度2，每分类20篇，5线程）
- **standard**: 标准爬取（深度3，每分类50篇，3线程）
- **deep**: 深度爬取（深度4，每分类100篇，2线程）
- **comprehensive**: 全面爬取（深度5，每分类200篇，1线程）

## 语言检测逻辑

1. **中文检测**：通过Unicode范围 `[\u4e00-\u9fff]` 检测中文字符
2. **繁体中文检测**：检测特定繁体字符如：繁、體、資、訊、開、關等
3. **英语检测**：不包含中文字符的内容默认为英语

## 注意事项

1. **遵守robots.txt**：请确保遵守目标网站的爬虫协议
2. **合理使用**：避免过于频繁的请求，已内置速率限制
3. **网络环境**：确保网络连接稳定，支持HTTPS访问
4. **内容版权**：爬取的内容仅供学习和研究使用

## 故障排除

### 常见问题

1. **网络连接失败**
   - 检查网络连接
   - 确认目标URL可访问
   - 检查防火墙设置

2. **内容提取失败**
   - 网页结构可能已更改
   - 需要更新CSS选择器

3. **编码问题**
   - 确保Python环境支持UTF-8编码
   - 检查系统区域设置

### 调试模式

在代码中添加更多日志输出：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 更新日志

### v2.0.0 (最新)
- 🆕 **深度爬取功能**：支持递归爬取分类下的所有子分类和文章
- 🖥️ **图形界面**：提供完整的GUI界面，支持参数配置和实时监控
- ⚡ **并发优化**：支持多线程并发爬取，大幅提升爬取效率
- 📁 **代码重构**：模块化设计，分离核心、GUI和工具模块
- ⚙️ **配置管理**：支持配置文件和预设模板
- 🎯 **内容优化**：优先提取`content-box`区域，提高内容质量
- 📊 **统计功能**：提供详细的爬取统计信息
- 🔧 **命令行增强**：支持更多命令行参数和选项

### v1.5.0
- 🌐 多语言URL检测优化
- 📚 增强内容提取算法
- 🔄 改进重试机制
- 📝 添加测试脚本

### v1.0.0
- 初始版本发布
- 支持多语言文档爬取
- 智能内容提取和语言检测
- JSON和Markdown格式输出

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 贡献

欢迎提交Issue和Pull Request来改进这个项目！

## 联系方式

如有问题或建议，请通过GitHub Issues联系。