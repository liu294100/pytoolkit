# GitLab Code Search

高性能桌面版 GitLab 代码搜索工具。将仓库克隆到本地，使用 ripgrep 进行极速全文搜索。

## 功能特点

- 基于 ripgrep 的高速代码搜索（比 GitLab Web 搜索快数倍）
- 支持按 Group / Project / Branch 筛选
- 支持正则表达式、全词匹配、忽略大小写
- 支持按文件类型过滤（如 `*.java`, `*.py`）
- 多线程并行搜索和仓库同步
- 代码预览面板，语法高亮
- 双击结果直接在浏览器打开 GitLab 对应位置
- 搜索历史自动补全
- 结果导出为 CSV
- 深色/浅色主题切换
- HTTP 代理支持（可开关）

## 快速开始

### 1. 安装依赖

双击运行 `install.bat`，或手动执行：

```bash
pip install -r requirements.txt
```

还需要 [ripgrep](https://github.com/BurntSushi/ripgrep/releases)，将 `rg.exe` 放在项目根目录即可。`install.bat` 会自动下载。

### 2. 配置

编辑 `config.json`：

```json
{
    "gitlab_url": "https://your-gitlab.com",
    "token": "your-personal-access-token",
    "proxy": "http://127.0.0.1:7890",
    "proxy_enabled": false
}
```

或在应用内 File → Settings 中配置。

### 3. 启动

```bash
start.bat
```

或：

```bash
python main.py
```

### 4. 使用流程

1. **连接 GitLab** — File → Connect to GitLab
2. **同步仓库** — 选择 Group/Project 范围，点击 "Sync (filtered)" 克隆到本地
3. **搜索** — 输入关键词，点击 Search

## 打包为 EXE

```bash
build.bat
```

生成的可执行文件在 `dist\GitLabCodeSearch\` 目录下。

## 配置说明

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `gitlab_url` | GitLab 服务器地址 | - |
| `token` | Personal Access Token | - |
| `proxy` | HTTP 代理地址 | - |
| `proxy_enabled` | 是否启用代理 | `false` |
| `clone_folder` | 仓库克隆目录 | `./cache` |
| `thread_count` | 并行线程数 | `8` |
| `search_timeout` | 搜索超时(秒) | `30` |
| `max_results_per_project` | 每项目最大结果数 | `500` |
| `context_lines` | 预览上下文行数 | `10` |
| `rg_path` | ripgrep 路径 | `./rg.exe` |

## 技术栈

- **GUI**: PySide6 (Qt6)
- **搜索引擎**: ripgrep
- **GitLab API**: python-gitlab
- **Git 操作**: GitPython
- **数据库**: SQLite (缓存项目信息和搜索历史)

## 项目结构

```
gitlabCodeSearch/
├── main.py                  # 入口
├── config.json              # 配置文件
├── rg.exe                   # ripgrep 搜索引擎
├── requirements.txt         # Python 依赖
├── install.bat              # 安装脚本
├── start.bat                # 启动脚本
├── build.bat                # 打包脚本
├── cache/                   # 克隆的仓库缓存
├── data/                    # SQLite 数据库和日志
└── gitlab_code_search/      # 源码
    ├── model/               # 数据模型
    ├── service/             # 服务层 (GitLab API, Git, 搜索)
    └── gui/                 # PySide6 界面
```

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+L` | 聚焦搜索框 |
| `Ctrl+E` | 导出结果为 CSV |
| `Ctrl+,` | 打开设置 |
| `Ctrl+Q` | 退出 |
| `Enter` | 执行搜索 |
