# PlayOldGame ROM 下载器

通过 Playwright 抓包下载 playoldgame.com 在线模拟器的 ROM 文件。

## 安装依赖

```bash
# 安装 Python 包
pip install -r requirements.txt

# 安装 Playwright 浏览器（需要代理可设置环境变量）
# set HTTPS_PROXY=
python -m playwright install chromium
```

## 使用方法

### 命令行版

```bash
# 基本用法
python rom_downloader.py "游戏页面URL"

# 使用代理
python rom_downloader.py "URL" --proxy http://1.1.1.1:1234

# 指定输出目录
python rom_downloader.py "URL" -o ./roms

# 无头模式（不弹出浏览器）
python rom_downloader.py "URL" --headless
```

### GUI 版

```bash
python rom_downloader_gui.py
# 或
pythonw rom_downloader_gui.py  # 隐藏控制台
```

## 工作原理

1. 使用 Playwright 启动浏览器访问游戏页面
2. 监听所有网络响应，捕获 ROM 文件下载请求
3. 保存 ROM 文件并自动解压

## 文件说明

- `rom_downloader.py` - 命令行版本
- `rom_downloader_gui.py` - GUI 图形界面版本
- `requirements.txt` - 依赖列表
