# LoL Scout：英雄联盟战绩 / 观战桌面工具

| 版本 | 入口 | 说明 |
|------|------|------|
| v1 | `riot_lol_tool.py` | Tkinter 基础版 |
| v2 | `riot_lol_tool_v2.py` | CustomTkinter 深色 UI，并发请求 |
| **v3** | `riot_lol_tool_v3.py` | 多数据源、模糊搜索、客户端联动、OP.GG 数据，本文档介绍这一版 |

```bash
pip install -r requirements.txt
python riot_lol_tool_v3.py
```

## v3 功能

**多数据源，按可用性自动降级**，没有 Riot API Key 也能用：

| 能力 | 优先级 |
|------|--------|
| 查找玩家 | Riot Account API → 本地客户端 LCU → OP.GG |
| 战绩 | Riot Match-V5 → LCU（同区服客户端，腾讯服也可）→ OP.GG（免 Key，最多 20 场） |
| 段位 / 常用英雄 | Riot League / Mastery + OP.GG（并发获取） |
| 实时对局 | Riot Spectator-V5 → LCU（本人选人阶段 / 游戏中） |
| 实时对局双方段位 | OP.GG 并发查询 10 人 → LCU ranked-stats |

**模糊搜索**
- 搜索框边输入边给出候选（↑↓ 选择、回车确认）。候选来自搜索历史、收藏、客户端好友，以及查过的对局里出现过的玩家
- 可以只输名字不带 `#Tag`：先匹配本地索引，再依次尝试区服默认 Tag（如 KR1、EUW）
- 匹配顺序：完全相等、前缀、子串、跳字，最后按编辑距离容错；全角半角和大小写都不区分
- 战绩列表支持模糊筛选英雄、模式、位置、队友名，中英文都能搜，例如 `疾风`、`yasuo`
- 点击对局详情或实时对局里的任意玩家名，直接跳转查询该玩家

**观战**
1. 客户端内观战（推荐）：客户端已登录且和目标同区服时，调用 LCU `/lol-spectator/v1/spectate/launch`
2. 直接拉起游戏：用 Spectator-V5 返回的 encryptionKey 启动 `League of Legends.exe "spectator <host> <key> <gameId> <platform>"`
3. 生成 `.bat` 观战脚本，或复制观战参数自行排查
4. 三方观战页：OP.GG 实时对局、Porofessor 一键跳转

**客户端联动（LCU）**
- 自动发现客户端，读取进程参数或 lockfile，每 5 秒检测一次状态
- 「我自己」一键查看当前登录账号
- 进入选人或游戏时，自动列出双方 10 人的段位、胜率、常用英雄，并标注职业选手
- 游戏进行中读取 Live Client Data（127.0.0.1:2999），显示实时比分、等级、装备

**性能**
- SQLite（WAL）持久缓存加内存 LRU。对局详情不会变化，永久缓存；其余数据按 TTL 过期。v2 每次写缓存都要重写整个 JSON，v3 没有这个开销
- Riot 请求按路由域做滑动窗口限流，遇到 429 读取 `Retry-After` 自动退避重试；同一 URL 的并发请求会合并
- 对局详情用线程池并发拉取，拉到一场就渲染一场
- 英雄、装备图标异步加载，走内存、磁盘、网络三级缓存；同一张图同时只下载一次
- 所有网络请求都在工作线程执行，结果通过队列回到 UI 线程，界面不会卡住

## 配置（`config.json` 或界面里的「⚙ 设置」）

| 字段 | 说明 |
|------|------|
| `api_key` | 可选，`RGAPI-...`，申请地址 https://developer.riotgames.com/ 。开发者 Key 每 24 小时过期 |
| `default_platform` | 默认区服，如 `KR` / `NA1` / `EUW1` / `TW2` |
| `match_count` | 默认拉取场数 |
| `league_client_path` | 可留空。会从 Riot 安装元数据自动探测 `Game/League of Legends.exe` |
| `locale` | 英雄名语言，如 `zh_CN` / `zh_TW` / `en_US` |
| `opgg_enabled` | 是否使用 OP.GG 数据 |
| `auto_connect_lcu` | 是否自动连接本地客户端 |
| `spectator_host` | 可选，自定义观战服务器，默认 `spectator.{区服}.lol.pvp.net:8080` |
| `rate_limits` | 限流窗口，默认 `[[20,1],[100,120]]`（开发者 Key 的额度） |

缓存数据库和图片缓存都在 `.lol_scout_data/` 下，删除不影响使用。第一次启动时会自动导入 v2 的 `search_history.json`。

## 说明与限制
- 不配置 Riot Key 时无法查询**他人**的实时对局（OP.GG 接口不提供这项数据），可以点「OP.GG 实时」或「Porofessor」在网页查看
- OP.GG 数据来自其官方 MCP 接口 `https://mcp-api.op.gg/mcp`。战绩列表只包含本人数据，打开详情时才补全全场 10 人
- 直接拉起游戏观战依赖本地客户端版本和区服，属于尽力而为。客户端内观战只能观看同区服玩家
- 选人阶段排位模式下，对方玩家名可能被隐藏，这时只能显示英雄
- 腾讯服：Riot 官方 API 不覆盖，但登录国服客户端后，可以通过 LCU 查看自己和选人阶段的队友

## 代码结构
```
lol_scout/
  config.py     配置、常量、区服映射
  storage.py    SQLite 缓存 + 玩家索引
  ratelimit.py  滑动窗口限流
  fuzzy.py      模糊匹配打分
  riot_api.py   Riot 官方 API
  ddragon.py    Data Dragon 静态数据与图片缓存
  lcu.py        本地客户端 LCU + Live Client Data
  opgg.py       OP.GG MCP 客户端 + 返回格式解析器 + 三方网页链接
  spectator.py  观战启动 / 生成脚本
  models.py     多数据源归一化模型
  service.py    业务编排、数据源降级
  widgets.py    UI 组件
  app.py        主窗口
```
