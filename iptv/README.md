# IPTV Pro 控制台

一个基于 Flask 的 IPTV 调试与播放面板，提供直播源加载、M3U 文本导入、频道去重聚合、多信号源切换、EPG 节目表查询，以及流地址代理转发能力。

## 功能概览

- 预设直播源加载，配置文件位于 `ref/iptv-sources.json`
- 手动输入 M3U 链接，直接拉取远程频道列表
- 粘贴 M3U 文本，模拟 APTV 风格导入
- 频道按 `tvg-id / 频道名` 去重，同名频道保留多个信号源
- 播放时可在同一频道下切换不同线路
- 支持 HLS 播放与代理后的 `.m3u8` 识别
- 支持 EPG XML / XML.GZ 节目单查询
- 支持代理模式，可配置代理主机与端口
- 对本地源配置、远程 M3U、EPG 文本做常见中文编码兼容处理

## 项目结构

```text
iptv/
├─ app/
│  ├─ routes/
│  │  └─ api.py
│  ├─ services/
│  │  ├─ epg_service.py
│  │  ├─ http_service.py
│  │  ├─ m3u_service.py
│  │  ├─ proxy_service.py
│  │  └─ source_service.py
│  ├─ __init__.py
│  └─ config.py
├─ ref/
│  ├─ iptv-sources.json
│  └─ iptv.html
├─ static/
│  ├─ css/
│  │  └─ style.css
│  └─ js/
│     └─ app.js
├─ templates/
│  └─ index.html
├─ app.py
├─ requirements.txt
├─ run.bat
├─ run.sh
└─ run_picker.ps1
```

## 运行环境

- Python 3.10 或更高版本
- Windows / Linux / macOS
- 能访问前端依赖 CDN
  - `hls.js`
  - `plyr`

## 安装依赖

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

Linux / macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## 启动方式

### 方式一：直接运行

```bash
python app.py
```

默认监听：

- `http://127.0.0.1:5000`
- `http://<你的局域网 IP>:5000`

### 方式二：Windows 启动脚本

```bash
run.bat
```

脚本会调用 `run_picker.ps1`，自动列出本机可用的 Python 解释器并让你选择。

### 方式三：Linux / macOS 启动脚本

```bash
sh run.sh
```

脚本会自动扫描本机 Python，并提示选择解释器启动。

## 使用说明

### 1. 加载直播源

- 在“预设源”中选择 `ref/iptv-sources.json` 里的源
- 点击“加载选中源”
- 或者手动输入 M3U 地址后点击“加载手动链接”
- 也可以在文本框中粘贴完整 M3U 文本并点击“导入文本”

### 2. 频道筛选

- 支持关键词筛选
- 支持按分组筛选
- 相同频道会自动聚合为一个条目
- 右侧会显示该频道拥有多少个信号源

### 3. 切换信号源

- 选择一个频道后
- 在播放器下方“当前信号源”下拉框切换线路
- 切换后会立即使用新线路播放

### 4. 查看 EPG 节目表

- 先选择频道
- 选择 EPG 预设，或者手动输入 EPG 链接
- 点击“加载当前频道节目”
- 支持 XML 与 `.xml.gz`

### 5. 使用代理模式

- 点击右上角“代理设置”
- 可配置：
  - 是否启用代理
  - 代理主机
  - 代理端口
- 默认值为 `127.0.0.1:7890`

代理模式适用于：

- 上游源存在地域限制
- 上游对直连请求限制较多
- 某些 EPG / M3U / 流媒体请求需要走本地代理

## 源配置格式

预设源配置文件为 [iptv-sources.json](file:///f:/Other/Code/dev/iptv/ref/iptv-sources.json)。

### `sources`

```json
{
  "name": "示例直播源",
  "type": "m3u",
  "url": "https://example.com/live.m3u",
  "group": "示例分组",
  "epg": "https://example.com/epg.xml.gz",
  "note": "备注信息"
}
```

字段说明：

- `name`：显示名称
- `type`：通常为 `m3u`
- `url`：源地址
- `group`：源分组
- `epg`：对应 EPG 地址，可选
- `note`：备注，可选
- `disabled`：若为真，则该源不会出现在页面里

### `epgSources`

```json
{
  "name": "示例 EPG",
  "url": "https://example.com/epg.xml.gz"
}
```

## 主要接口

后端接口定义位于 [api.py](file:///f:/Other/Code/dev/iptv/app/routes/api.py)。

- `GET /api/sources`：读取本地预设源配置
- `GET /api/channels?source_url=...&source_name=...`：拉取并解析远程 M3U
- `POST /api/channels-text`：解析文本导入的 M3U
- `GET /api/epg?epg_url=...&channel_name=...&tvg_id=...`：查询节目单
- `GET /api/proxy-text?url=...`：代理获取文本内容
- `GET /api/proxy-stream?url=...`：代理流媒体或 m3u8 请求
- `GET /api/proxy-settings`：读取代理设置
- `POST /api/proxy-settings`：保存代理设置

## 编码兼容说明

项目对乱码做了兼容处理，覆盖以下场景：

- 本地 `iptv-sources.json`
- 远程 M3U 文本
- EPG XML / XML.GZ
- 已经发生过一次错解的常见中文文本

如果某个源仍然乱码，常见原因通常是：

- 上游返回内容本身已经损坏
- 上游混用了多种编码
- M3U / XML 内部字段实际不是合法文本

## 常见问题

### 播放器报错或黑屏

- 尝试切换同频道下的其他信号源
- 检查目标流是否已失效
- 对跨域、鉴权、风控较强的源，尝试开启代理模式
- 某些 HLS 源需要等待几秒完成首段缓冲

### 节目单加载失败

- 检查 EPG 地址能否访问
- 优先尝试 `.xml.gz` 或体积较小的 EPG 源
- 确保当前频道存在 `tvg-id` 或可匹配频道名

### 频道数量和原始 M3U 不一致

- 这是预期行为
- 页面会自动合并重复频道
- 重复频道不会丢失，只是收纳进同一频道的多信号源列表

## 开发说明

- 应用入口：[app.py](file:///f:/Other/Code/dev/iptv/app.py)
- Flask 初始化：[__init__.py](file:///f:/Other/Code/dev/iptv/app/__init__.py)
- 前端逻辑：[app.js](file:///f:/Other/Code/dev/iptv/static/js/app.js)
- 页面模板：[index.html](file:///f:/Other/Code/dev/iptv/templates/index.html)

本项目当前依赖较少，后端仅使用：

- Flask
- requests

## 校验

可执行以下命令确认 Python 文件可以正常编译：

```bash
python -m compileall app.py app
```
