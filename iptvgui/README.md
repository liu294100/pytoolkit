# IPTV Player

一个基于 PySide6 + MPV 的桌面 IPTV 播放器，支持 H.265/HEVC 硬解、M3U 直播源加载、EPG 节目单查询。

![IPTV Player](resources/icon.png)

## 功能特性

- **高清播放** - 基于 MPV 播放器，支持 H.265/HEVC 硬件解码
- **多源支持** - 支持预设源、手动输入 M3U 链接、粘贴 M3U 文本导入
- **EPG 节目单** - 自动加载节目单，高亮当前播放节目
- **多信号源** - 同一频道支持多个信号源切换
- **全屏播放** - 支持全屏，控制栏自动隐藏
- **本地缓存** - 频道列表和 EPG 数据本地缓存，启动快速
- **代理支持** - 支持 HTTP 代理设置

## 快速开始

### 环境要求

- Python 3.10+
- Windows 10/11

### 安装依赖

```bash
cd iptvgui
pip install -r requirements.txt
```

或运行安装脚本：

```bash
install.bat
```

### 下载 MPV 播放器

首次运行前需要下载 MPV 库：

```bash
python download_mpv.py
```

这会下载 `libmpv-2.dll` 到 `mpv/` 目录。

### 运行

```bash
python main.py
```

或运行启动脚本：

```bash
run.bat
```

## 使用说明

### 加载直播源

1. 点击菜单 **文件 → 加载源**
2. 选择加载方式：
   - **预设源** - 从 `iptv-sources.json` 配置的源列表选择
   - **手动输入** - 输入 M3U 链接地址
   - **文本导入** - 粘贴 M3U 文本内容

### 播放频道

- 左侧频道列表选择频道
- 支持按分组筛选
- 支持关键词搜索
- 同一频道有多个信号源时，可在播放器下方切换

### 查看 EPG 节目单

- 切换频道时自动加载 EPG（优先缓存）
- 右侧面板显示当前频道节目单
- 当前播放节目红色高亮
- 点击「完整」按钮查看完整节目单（按日期分页）

### 全屏播放

- 双击视频区域进入/退出全屏
- 按 `F11` 切换全屏
- 按 `ESC` 退出全屏
- 全屏时鼠标移动显示控制栏，3 秒后自动隐藏

### 代理设置

点击菜单 **设置 → 代理设置**，可配置 HTTP 代理。

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `F11` | 切换全屏 |
| `ESC` | 退出全屏 |
| `Space` | 暂停/播放 |
| `↑` | 增加音量 |
| `↓` | 减少音量 |
| `←` | 上一个信号源 |
| `→` | 下一个信号源 |

## 打包发布

### 生成可执行文件

```bash
cd iptvgui
build.bat
```

打包完成后，输出目录为 `dist/IPTV Player/`。

### 打包内容

```
dist/IPTV Player/
├── IPTV Player.exe    # 主程序
├── cache/             # 缓存目录
├── _internal/         # Python 运行时
└── ...
```

## 项目结构

```
iptvgui/
├── main.py                 # 入口文件
├── requirements.txt        # 依赖列表
├── models/                 # 数据模型
│   ├── channel.py          # 频道、频道组
│   └── source.py           # 源配置
├── services/               # 业务服务
│   ├── http_service.py     # HTTP 请求
│   ├── m3u_service.py      # M3U 解析
│   ├── epg_service.py      # EPG 解析
│   ├── source_service.py   # 源配置加载
│   └── cache_manager.py    # 本地缓存
├── ui/                     # 界面组件
│   ├── main_window.py      # 主窗口
│   ├── player_widget.py    # 播放器组件
│   ├── channel_list.py     # 频道列表
│   ├── epg_panel.py        # EPG 面板
│   ├── epg_dialog.py       # EPG 弹窗
│   ├── source_dialog.py    # 源加载对话框
│   └── proxy_dialog.py     # 代理设置对话框
├── resources/              # 资源文件
│   ├── style.qss           # 样式表
│   ├── icon.ico            # 应用图标
│   └── iptv-sources.json   # 预设源配置
├── mpv/                    # MPV 播放器库
│   └── libmpv-2.dll
├── cache/                  # 缓存目录
│   ├── channels.json       # 频道缓存
│   └── epg.json            # EPG 缓存
├── build.bat               # 打包脚本
├── run.bat                 # 启动脚本
├── install.bat             # 安装依赖脚本
└── clean.bat               # 清理脚本
```

## 源配置格式

`resources/iptv-sources.json` 配置文件格式：

```json
{
  "sources": [
    {
      "name": "源名称",
      "type": "m3u",
      "url": "https://example.com/live.m3u",
      "group": "分组名",
      "epg": "https://example.com/epg.xml.gz",
      "note": "备注"
    }
  ],
  "epgSources": [
    {
      "name": "EPG 名称",
      "url": "https://example.com/epg.xml.gz"
    }
  ]
}
```

## 技术栈

- **GUI 框架**: PySide6 (Qt for Python)
- **播放器**: MPV (libmpv)
- **网络请求**: requests
- **编码处理**: 自动检测中文编码 (UTF-8/GBK/GB2312)

## 常见问题

### 播放器黑屏或报错

1. 确认 `mpv/libmpv-2.dll` 文件存在
2. 运行 `python download_mpv.py` 重新下载
3. 尝试切换其他信号源

### EPG 加载失败

1. 检查 EPG 源地址是否可访问
2. 尝试切换其他 EPG 源
3. 部分频道可能没有匹配的 EPG 数据

### 任务栏图标不显示

重启应用程序，Windows 需要刷新图标缓存。

## 许可证

MIT License
