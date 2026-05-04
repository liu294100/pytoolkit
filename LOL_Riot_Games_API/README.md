# LoL 战绩 / 观战 Python 小工具（桌面版）

功能：
- 输入 `Riot ID`（例如 `Faker#KR1`）搜索玩家
- 拉取最近对局战绩（Match-V5）
- 查看单局详细数据
- 获取进行中对局并尝试“一键观战”（需要本地安装英雄联盟客户端）

## 1. 准备
1. 你需要一个 Riot Developer API Key
2. 仅支持 Riot 官方区服（NA/EUW/KR/JP/SEA 等）。腾讯服不在 Riot 官方 API 覆盖范围内，本工具不以腾讯服为目标。

官方接口文档入口：[https://developer.riotgames.com/apis](https://developer.riotgames.com/apis)

https://developer.riotgames.com/

## 2. 安装依赖
建议使用 Python 3.10+。

```bash
pip install -r requirements.txt
```

## 3. 配置
编辑同目录下的 `config.json`：
- `api_key`: 填入你的 Riot API Key
- `default_platform`: 默认平台（如 `NA1`/`EUW1`/`KR`/`OC1` 等）
- `match_count`: 拉取最近对局数量（1-100）
- `league_client_path`: 本地客户端可执行文件路径（也可以在 GUI 里选择）

## 4. 启动
```bash
python riot_lol_tool.py
```

## 5. 观战说明（重要）
本工具使用 `spectator-v5` 拿到当前对局的 `gameId/platformId/encryptionKey` 后，尝试用命令行方式拉起本地客户端：

```
LeagueClient.exe spectator spectator.{platform}.lol.riotgames.com:80 {encryptionKey} {gameId} {platformId}
```

注意：
- 需要你本地已经安装对应区服的英雄联盟客户端
- 路径不对、区服不匹配、客户端版本问题，都可能导致观战失败
- 这是“尽力而为”的拉起方式；不同安装包/启动器可能存在差异

