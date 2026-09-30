"""配置、常量与通用工具函数"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, Tuple

APP_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = APP_DIR / "config.json"
DATA_DIR = APP_DIR / ".lol_scout_data"
DB_PATH = DATA_DIR / "scout.db"
IMG_CACHE_DIR = DATA_DIR / "img"
LEGACY_HISTORY_PATH = APP_DIR / "search_history.json"

DEFAULT_TIMEOUT = 12

DEFAULT_CONFIG: Dict[str, Any] = {
    "api_key": "请替换成你的 Riot API Key",
    "default_platform": "KR",
    "match_count": 20,
    "league_client_path": "",   # Game/League of Legends.exe 路径，可留空自动探测
    "locale": "zh_CN",          # Data Dragon / 观战客户端语言
    "opgg_enabled": True,
    "auto_connect_lcu": True,
    # Riot 开发者 Key 默认限流：20 次/1 秒，100 次/2 分钟
    "rate_limits": [[20, 1], [100, 120]],
}

# 平台 -> 大区路由
PLATFORM_TO_REGIONAL = {
    "BR1": "americas", "LA1": "americas", "LA2": "americas", "NA1": "americas",
    "KR": "asia", "JP1": "asia",
    "EUN1": "europe", "EUW1": "europe", "ME1": "europe", "RU": "europe", "TR1": "europe",
    "OC1": "sea", "SG2": "sea", "TW2": "sea", "VN2": "sea",
}

# 平台 -> OP.GG 区服代码（网页用小写，MCP 用大写）
PLATFORM_TO_OPGG = {
    "NA1": "na", "EUW1": "euw", "EUN1": "eune", "KR": "kr", "JP1": "jp",
    "BR1": "br", "LA1": "lan", "LA2": "las", "OC1": "oce", "TR1": "tr",
    "RU": "ru", "SG2": "sg", "TW2": "tw", "VN2": "vn", "ME1": "me",
}

# 平台 -> Porofessor / League of Graphs 区服代码
PLATFORM_TO_PORO = {
    "NA1": "na", "EUW1": "euw", "EUN1": "eune", "KR": "kr", "JP1": "jp",
    "BR1": "br", "LA1": "lan", "LA2": "las", "OC1": "oce", "TR1": "tr",
    "RU": "ru", "SG2": "sg", "TW2": "tw", "VN2": "vn", "ME1": "me",
}

# 常见区服默认 Tag，用于只输入名字时的候选猜测
PLATFORM_DEFAULT_TAGS = {
    "KR": ["KR1", "KR"], "NA1": ["NA1", "NA"], "EUW1": ["EUW", "EUW1"],
    "EUN1": ["EUNE", "EUN1"], "JP1": ["JP1", "JP"], "BR1": ["BR1", "BR"],
    "LA1": ["LAN", "LA1"], "LA2": ["LAS", "LA2"], "OC1": ["OCE", "OC1"],
    "TR1": ["TR1", "TR"], "RU": ["RU1", "RU"], "SG2": ["SG2", "SG"],
    "TW2": ["TW2", "TW"], "VN2": ["VN2", "VN"], "ME1": ["ME1", "ME"],
}

QUEUE_NAMES = {
    0: "自定义", 400: "匹配模式", 420: "单双排", 430: "盲选", 440: "灵活排位",
    450: "大乱斗", 480: "快速匹配", 490: "快速匹配", 700: "冠军杯", 720: "大乱斗冠军杯",
    830: "人机入门", 840: "人机进阶", 850: "人机困难", 870: "人机", 880: "人机", 890: "人机",
    900: "无限火力", 1020: "克隆模式", 1090: "云顶之弈", 1100: "云顶排位",
    1300: "极限闪击", 1400: "终极魔典", 1700: "斗魂竞技场", 1710: "斗魂竞技场",
    1900: "无限乱斗", 2300: "神木之门",
}

TIER_CN = {
    "IRON": "坚韧黑铁", "BRONZE": "英勇黄铜", "SILVER": "不屈白银", "GOLD": "荣耀黄金",
    "PLATINUM": "华贵铂金", "EMERALD": "流光翡翠", "DIAMOND": "璀璨钻石",
    "MASTER": "超凡大师", "GRANDMASTER": "傲世宗师", "CHALLENGER": "最强王者",
}

POSITION_CN = {
    "TOP": "上单", "JUNGLE": "打野", "MIDDLE": "中单", "MID": "中单",
    "BOTTOM": "下路", "ADC": "下路", "UTILITY": "辅助", "SUPPORT": "辅助",
}

COLORS = {
    "bg_dark": "#0b0d12",
    "bg_card": "#141821",
    "bg_card2": "#1b2130",
    "bg_hover": "#222a3b",
    "accent": "#3fa9f5",
    "accent_dark": "#2b7fc0",
    "win": "#3ddc97",
    "win_bg": "#15332a",
    "lose": "#ff5d73",
    "lose_bg": "#3a1a22",
    "text": "#eef2f7",
    "text_dim": "#9aa4b5",
    "text_muted": "#5e6779",
    "border": "#2a3244",
    "gold": "#f5c451",
    "purple": "#a98bff",
    "opgg": "#5383e8",
}

_config_lock = threading.Lock()


def load_config() -> Dict[str, Any]:
    with _config_lock:
        data: Dict[str, Any] = {}
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}
        merged = DEFAULT_CONFIG.copy()
        merged.update(data)
        return merged


def save_config(config: Dict[str, Any]) -> None:
    with _config_lock:
        CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def api_key_valid(key: str) -> bool:
    key = (key or "").strip()
    return bool(key) and "请替换" not in key and key.startswith("RGAPI-")


def parse_riot_id(text: str) -> Tuple[str, str]:
    """解析 `名字#标签`，没有标签时返回 (name, "")"""
    value = (text or "").strip().replace("＃", "#")
    if "#" in value:
        name, tag = value.split("#", 1)
        return name.strip(), tag.strip()
    return value, ""


def format_duration(seconds: int) -> str:
    mins, sec = divmod(max(0, int(seconds or 0)), 60)
    hour, mins = divmod(mins, 60)
    return f"{hour}:{mins:02d}:{sec:02d}" if hour else f"{mins}:{sec:02d}"


def kda_ratio(k: int, d: int, a: int) -> float:
    return (k + a) / max(1, d)
