"""
LoL 战绩 / 观战工具 v2.0
- 现代化深色主题 UI (CustomTkinter)
- 并发 API 请求优化
- 本地缓存 + 搜索历史
"""

import json
import os
import base64
import subprocess
import sys
import threading
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable
from functools import lru_cache

import requests

# CustomTkinter for modern UI
try:
    import customtkinter as ctk
    from customtkinter import CTkImage
except ImportError:
    print("请先安装 customtkinter: pip install customtkinter")
    sys.exit(1)

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None
    ImageDraw = None

# ============================================================================
# 配置常量
# ============================================================================

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
CACHE_PATH = APP_DIR / "cache.json"
HISTORY_PATH = APP_DIR / "search_history.json"
DEFAULT_TIMEOUT = 15

# 颜色主题 - 深色电竞风格
COLORS = {
    "bg_dark": "#0a0a0f",
    "bg_card": "#12121a",
    "bg_hover": "#1a1a25",
    "accent": "#00d4ff",
    "accent_dark": "#0099cc",
    "accent_glow": "#00d4ff40",
    "win": "#00ff88",
    "win_bg": "#00ff8820",
    "lose": "#ff4466",
    "lose_bg": "#ff446620",
    "text": "#ffffff",
    "text_dim": "#888899",
    "text_muted": "#555566",
    "border": "#2a2a3a",
    "gold": "#ffd700",
    "purple": "#aa66ff",
}

PLATFORM_TO_REGIONAL = {
    "BR1": "americas", "LA1": "americas", "LA2": "americas", "NA1": "americas",
    "KR": "asia", "JP1": "asia",
    "EUN1": "europe", "EUW1": "europe", "ME1": "europe", "RU": "europe", "TR1": "europe",
    "OC1": "sea", "SG2": "sea", "TW2": "sea", "VN2": "sea",
}

DEFAULT_CONFIG = {
    "api_key": "请替换成你的 Riot API Key",
    "default_platform": "NA1",
    "match_count": 10,
    "league_client_path": "",
}

QUEUE_NAMES = {
    400: "匹配模式", 420: "单双排", 430: "盲选", 440: "灵活排位",
    450: "大乱斗", 700: "极限闪击", 830: "人机入门", 840: "人机进阶",
    850: "人机困难", 900: "无限火力", 1020: "单中模式", 1090: "团队激斗",
    1700: "斗魂竞技场",
}

# ============================================================================
# 工具函数
# ============================================================================

def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        data = DEFAULT_CONFIG.copy()
        save_config(data)
    merged = DEFAULT_CONFIG.copy()
    merged.update(data)
    return merged


def save_config(config: Dict[str, Any]) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def split_riot_id(text: str) -> Tuple[str, str]:
    value = text.strip()
    if "#" not in value:
        raise ValueError("请输入完整 Riot ID，格式如：Faker#KR1")
    game_name, tag_line = value.split("#", 1)
    game_name = game_name.strip()
    tag_line = tag_line.strip()
    if not game_name or not tag_line:
        raise ValueError("Riot ID 格式不正确，请使用 `名字#标签`")
    return game_name, tag_line


def format_duration(seconds: int) -> str:
    mins, sec = divmod(max(0, int(seconds)), 60)
    hour, mins = divmod(mins, 60)
    if hour > 0:
        return f"{hour}h {mins}m"
    return f"{mins}m {sec}s"


def safe_get(mapping: Dict[str, Any], *keys: str, default: Any = "-") -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current




# ============================================================================
# 缓存系统 - 减少重复 API 请求
# ============================================================================

class CacheManager:
    """本地缓存管理，减少 API 请求"""
    
    def __init__(self, cache_file: Path, ttl_minutes: int = 30):
        self.cache_file = cache_file
        self.ttl = timedelta(minutes=ttl_minutes)
        self.data: Dict[str, Any] = self._load()
    
    def _load(self) -> Dict[str, Any]:
        if not self.cache_file.exists():
            return {"entries": {}, "version": 1}
        try:
            with self.cache_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"entries": {}, "version": 1}
    
    def _save(self) -> None:
        try:
            with self.cache_file.open("w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False)
        except:
            pass
    
    def _make_key(self, prefix: str, *args) -> str:
        raw = f"{prefix}:{':'.join(str(a) for a in args)}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]
    
    def get(self, prefix: str, *args) -> Optional[Any]:
        key = self._make_key(prefix, *args)
        entry = self.data.get("entries", {}).get(key)
        if not entry:
            return None
        cached_time = datetime.fromisoformat(entry["time"])
        if datetime.now() - cached_time > self.ttl:
            return None
        return entry["value"]
    
    def set(self, prefix: str, *args, value: Any) -> None:
        key = self._make_key(prefix, *args)
        self.data.setdefault("entries", {})[key] = {
            "time": datetime.now().isoformat(),
            "value": value
        }
        self._save()
    
    def clear(self) -> None:
        self.data = {"entries": {}, "version": 1}
        self._save()


# ============================================================================
# 搜索历史管理
# ============================================================================

class SearchHistory:
    """搜索历史管理，支持自动补全"""
    
    MAX_HISTORY = 50
    
    def __init__(self, history_file: Path):
        self.history_file = history_file
        self.entries: List[Dict[str, Any]] = self._load()
    
    def _load(self) -> List[Dict[str, Any]]:
        if not self.history_file.exists():
            return []
        try:
            with self.history_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("entries", [])
        except:
            return []
    
    def _save(self) -> None:
        try:
            with self.history_file.open("w", encoding="utf-8") as f:
                json.dump({"entries": self.entries}, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def add(self, riot_id: str, platform: str, puuid: str) -> None:
        # 移除重复项
        self.entries = [e for e in self.entries if e.get("riot_id", "").lower() != riot_id.lower()]
        # 添加到开头
        self.entries.insert(0, {
            "riot_id": riot_id,
            "platform": platform,
            "puuid": puuid,
            "time": datetime.now().isoformat()
        })
        # 限制数量
        self.entries = self.entries[:self.MAX_HISTORY]
        self._save()
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """模糊匹配搜索历史"""
        if not query:
            return self.entries[:10]
        query_lower = query.lower()
        return [e for e in self.entries if query_lower in e.get("riot_id", "").lower()][:10]
    
    def get_all(self) -> List[Dict[str, Any]]:
        return self.entries[:10]




# ============================================================================
# 异常类
# ============================================================================

class RiotAPIError(Exception):
    pass


class LCUError(Exception):
    pass


# ============================================================================
# 数据类
# ============================================================================

@dataclass
class SummonerProfile:
    puuid: str
    riot_id: str
    platform: str
    regional: str


# ============================================================================
# Riot API 客户端 - 支持并发请求
# ============================================================================

class RiotAPIClient:
    def __init__(self, api_key: str, cache: CacheManager):
        self.api_key = api_key.strip()
        self.cache = cache
        self.session = requests.Session()
        self.session.headers.update({"X-Riot-Token": self.api_key})
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    def _get(self, url: str, params: Optional[Dict[str, Any]] = None, use_cache: bool = True) -> Any:
        if not self.api_key or "请替换" in self.api_key:
            raise RiotAPIError("请先在 config.json 中填写有效的 Riot API Key。")
        
        # 尝试从缓存获取
        if use_cache:
            cached = self.cache.get("api", url, str(params))
            if cached is not None:
                return cached
        
        try:
            response = self.session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        except requests.RequestException as exc:
            raise RiotAPIError(f"请求失败：{exc}") from exc
        
        if response.status_code == 200:
            data = response.json()
            if use_cache:
                self.cache.set("api", url, str(params), value=data)
            return data
        if response.status_code == 401:
            raise RiotAPIError("API Key 无效或已过期。")
        if response.status_code == 403:
            raise RiotAPIError("API Key 没有权限访问该接口。")
        if response.status_code == 404:
            raise RiotAPIError("没有找到该召唤师或当前没有可用数据。")
        if response.status_code == 429:
            raise RiotAPIError("请求过快，触发了 Riot API 限流，请稍后再试。")
        raise RiotAPIError(f"接口报错：HTTP {response.status_code}")
    
    def get_account_by_riot_id(self, regional: str, game_name: str, tag_line: str) -> Dict[str, Any]:
        url = f"https://{regional}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        return self._get(url)
    
    def get_active_shard(self, regional: str, puuid: str) -> Dict[str, Any]:
        url = f"https://{regional}.api.riotgames.com/riot/account/v1/active-shards/by-game/lol/by-puuid/{puuid}"
        return self._get(url)
    
    def get_match_ids(self, regional: str, puuid: str, count: int = 10) -> List[str]:
        url = f"https://{regional}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {"start": 0, "count": max(1, min(100, count))}
        return self._get(url, params=params, use_cache=False)  # 不缓存对局列表
    
    def get_match_detail(self, regional: str, match_id: str) -> Dict[str, Any]:
        url = f"https://{regional}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        return self._get(url)
    
    def get_match_details_concurrent(self, regional: str, match_ids: List[str], 
                                      progress_callback: Optional[Callable[[int, int], None]] = None) -> List[Tuple[str, Dict[str, Any]]]:
        """并发获取多个对局详情"""
        results = []
        total = len(match_ids)
        completed = 0
        
        def fetch_one(match_id: str) -> Tuple[str, Optional[Dict[str, Any]]]:
            try:
                return match_id, self.get_match_detail(regional, match_id)
            except Exception:
                return match_id, None
        
        futures = {self.executor.submit(fetch_one, mid): mid for mid in match_ids}
        
        for future in as_completed(futures):
            match_id, detail = future.result()
            if detail:
                results.append((match_id, detail))
            completed += 1
            if progress_callback:
                progress_callback(completed, total)
        
        # 按原顺序排序
        order = {mid: i for i, mid in enumerate(match_ids)}
        results.sort(key=lambda x: order.get(x[0], 999))
        return results
    
    def get_current_game(self, platform: str, puuid: str) -> Dict[str, Any]:
        url = f"https://{platform.lower()}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
        return self._get(url, use_cache=False)


# ============================================================================
# LCU 客户端 - 本地客户端通信
# ============================================================================

class LCUClient:
    def __init__(self, league_client_path: str = ""):
        self.league_client_path = league_client_path.strip()
    
    def _candidate_lockfiles(self) -> List[Path]:
        candidates: List[Path] = []
        if self.league_client_path:
            client_file = Path(self.league_client_path)
            for parent in [client_file.parent, client_file.parent.parent, client_file.parent.parent.parent]:
                if parent and str(parent) not in {"", "."}:
                    candidates.append(parent / "lockfile")
        
        common_roots = [
            Path(f"{d}:/Riot Games/League of Legends") for d in "CDEFG"
        ]
        for root in common_roots:
            candidates.append(root / "lockfile")
        
        return list(dict.fromkeys(candidates))  # 去重保持顺序
    
    def _read_lockfile(self) -> Tuple[int, str]:
        for lockfile in self._candidate_lockfiles():
            if not lockfile.exists():
                continue
            try:
                content = lockfile.read_text(encoding="utf-8").strip()
                parts = content.split(":")
                if len(parts) >= 5:
                    return int(parts[2]), parts[3]
            except:
                continue
        raise LCUError("没有找到客户端 lockfile。请先打开并登录英雄联盟客户端。")
    
    def _request(self, method: str, path: str, json_body: Optional[Dict[str, Any]] = None) -> requests.Response:
        port, token = self._read_lockfile()
        auth = base64.b64encode(f"riot:{token}".encode()).decode()
        headers = {"Authorization": f"Basic {auth}"}
        url = f"https://127.0.0.1:{port}{path}"
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        return requests.request(method.upper(), url, headers=headers, json=json_body, timeout=DEFAULT_TIMEOUT, verify=False)
    
    def spectate_by_puuid(self, riot_id: str, puuid: str) -> None:
        payload = {
            "allowObserveMode": "ALL",
            "dropInSpectateGameId": riot_id,
            "gameQueueType": "",
            "puuid": puuid,
        }
        response = self._request("POST", "/lol-spectator/v1/spectate/launch", json_body=payload)
        if response.status_code not in {200, 201, 202, 204}:
            raise LCUError(f"客户端观战发起失败：HTTP {response.status_code}")




# ============================================================================
# 自定义 UI 组件
# ============================================================================

class AnimatedButton(ctk.CTkButton):
    """带悬停动画效果的按钮"""
    
    def __init__(self, master, **kwargs):
        self.original_fg = kwargs.get("fg_color", COLORS["accent"])
        self.hover_fg = kwargs.get("hover_color", COLORS["accent_dark"])
        super().__init__(master, **kwargs)


class LoadingSpinner(ctk.CTkFrame):
    """加载动画指示器"""
    
    def __init__(self, master, size: int = 40, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        
        self.size = size
        self.angle = 0
        self.running = False
        
        self.canvas = ctk.CTkCanvas(
            self, width=size, height=size,
            bg=COLORS["bg_card"], highlightthickness=0
        )
        self.canvas.pack()
        
    def start(self):
        self.running = True
        self._animate()
    
    def stop(self):
        self.running = False
        self.canvas.delete("all")
    
    def _animate(self):
        if not self.running:
            return
        self.canvas.delete("all")
        
        # 画圆弧
        padding = 4
        self.canvas.create_arc(
            padding, padding, self.size - padding, self.size - padding,
            start=self.angle, extent=270,
            outline=COLORS["accent"], width=3, style="arc"
        )
        self.angle = (self.angle + 15) % 360
        self.after(50, self._animate)


class MatchCard(ctk.CTkFrame):
    """单场对局卡片"""
    
    def __init__(self, master, match_data: Dict[str, Any], on_click: Callable, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_card"], corner_radius=12, **kwargs)
        
        self.match_data = match_data
        self.on_click = on_click
        self.is_hovered = False
        
        # 绑定点击和悬停事件
        self.bind("<Button-1>", self._handle_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        
        self._build_ui()
    
    def _build_ui(self):
        # 根据胜负设置边框颜色
        is_win = self.match_data.get("win", False)
        border_color = COLORS["win"] if is_win else COLORS["lose"]
        result_bg = COLORS["win_bg"] if is_win else COLORS["lose_bg"]
        
        # 左侧胜负条
        indicator = ctk.CTkFrame(self, width=4, fg_color=border_color, corner_radius=2)
        indicator.pack(side="left", fill="y", padx=(8, 0), pady=8)
        
        # 主内容区
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=12, pady=8)
        
        # 第一行：英雄 + KDA
        row1 = ctk.CTkFrame(content, fg_color="transparent")
        row1.pack(fill="x")
        
        champ_name = self.match_data.get("champion", "Unknown")
        ctk.CTkLabel(
            row1, text=champ_name,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"]
        ).pack(side="left")
        
        kda = self.match_data.get("kda", "0/0/0")
        kda_color = COLORS["gold"] if self._is_good_kda(kda) else COLORS["text"]
        ctk.CTkLabel(
            row1, text=kda,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=kda_color
        ).pack(side="right")
        
        # 第二行：模式 + 时间
        row2 = ctk.CTkFrame(content, fg_color="transparent")
        row2.pack(fill="x", pady=(4, 0))
        
        queue_name = self.match_data.get("queue", "")
        ctk.CTkLabel(
            row2, text=queue_name,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_dim"]
        ).pack(side="left")
        
        duration = self.match_data.get("duration", "")
        ctk.CTkLabel(
            row2, text=duration,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"]
        ).pack(side="right")
        
        # 右侧胜负标签
        result_frame = ctk.CTkFrame(self, fg_color=result_bg, corner_radius=8)
        result_frame.pack(side="right", padx=12, pady=8)
        
        result_text = "胜" if is_win else "败"
        ctk.CTkLabel(
            result_frame, text=result_text,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=border_color,
            width=36, height=36
        ).pack(padx=4, pady=4)
        
        # 让所有子组件也响应点击
        for widget in self.winfo_children():
            widget.bind("<Button-1>", self._handle_click)
            self._bind_children(widget)
    
    def _bind_children(self, widget):
        for child in widget.winfo_children():
            child.bind("<Button-1>", self._handle_click)
            self._bind_children(child)
    
    def _is_good_kda(self, kda: str) -> bool:
        try:
            parts = kda.split("/")
            k, d, a = int(parts[0]), int(parts[1]), int(parts[2])
            return (k + a) / max(1, d) >= 3
        except:
            return False
    
    def _handle_click(self, event=None):
        self.on_click(self.match_data.get("match_id"))
    
    def _on_enter(self, event=None):
        self.configure(fg_color=COLORS["bg_hover"])
    
    def _on_leave(self, event=None):
        self.configure(fg_color=COLORS["bg_card"])


class StatusBar(ctk.CTkFrame):
    """底部状态栏"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_card"], height=36, **kwargs)
        
        self.status_label = ctk.CTkLabel(
            self, text="就绪",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_dim"]
        )
        self.status_label.pack(side="left", padx=16, pady=8)
        
        self.spinner = LoadingSpinner(self, size=20)
        self.spinner.pack(side="right", padx=16)
        self.spinner.pack_forget()  # 默认隐藏
    
    def set_status(self, text: str, loading: bool = False):
        self.status_label.configure(text=text)
        if loading:
            self.spinner.pack(side="right", padx=16)
            self.spinner.start()
        else:
            self.spinner.stop()
            self.spinner.pack_forget()




# ============================================================================
# 主应用
# ============================================================================

class LoLScoutApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # 基础设置
        self.title("⚔️ LoL Scout Pro")
        self.geometry("1280x820")
        self.minsize(1000, 700)
        
        # 设置深色主题
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=COLORS["bg_dark"])
        
        # 加载配置和初始化
        self.config = load_config()
        self.cache = CacheManager(CACHE_PATH, ttl_minutes=60)
        self.history = SearchHistory(HISTORY_PATH)
        self.api = RiotAPIClient(self.config["api_key"], self.cache)
        self.lcu = LCUClient(self.config.get("league_client_path", ""))
        
        # 状态
        self.profile: Optional[SummonerProfile] = None
        self.match_details_by_id: Dict[str, Dict[str, Any]] = {}
        self.current_game_data: Optional[Dict[str, Any]] = None
        self.match_cards: List[MatchCard] = []
        
        # 构建 UI
        self._build_ui()
    
    def _build_ui(self):
        # 主布局：左侧边栏 + 右侧内容
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # 左侧边栏
        self._build_sidebar()
        
        # 右侧内容区
        self.content_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=1)
        
        # 顶部标题栏
        self._build_header()
        
        # TabView
        self._build_tabs()
        
        # 底部状态栏
        self.status_bar = StatusBar(self.content_frame)
        self.status_bar.grid(row=2, column=0, sticky="ew")
    
    def _build_sidebar(self):
        """构建左侧边栏"""
        sidebar = ctk.CTkFrame(self, width=280, fg_color=COLORS["bg_card"], corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        
        # Logo
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=20, pady=(24, 16))
        
        ctk.CTkLabel(
            logo_frame, text="⚔️ LoL Scout",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            logo_frame, text="战绩查询 · 实时观战",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_dim"]
        ).pack(anchor="w", pady=(4, 0))
        
        # 分隔线
        ctk.CTkFrame(sidebar, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=20, pady=8)
        
        # 搜索区域
        search_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=8)
        
        ctk.CTkLabel(
            search_frame, text="Riot ID",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w", pady=(0, 6))
        
        self.riot_id_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="例如: Faker#KR1",
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS["bg_dark"],
            border_color=COLORS["border"],
            text_color=COLORS["text"]
        )
        self.riot_id_entry.pack(fill="x")
        self.riot_id_entry.bind("<Return>", lambda e: self.search_profile())
        self.riot_id_entry.bind("<KeyRelease>", self._on_search_input)
        
        # 搜索历史下拉
        self.history_listbox = ctk.CTkScrollableFrame(
            search_frame, height=0, fg_color=COLORS["bg_dark"]
        )
        self.history_visible = False
        
        # 平台选择
        platform_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        platform_frame.pack(fill="x", padx=20, pady=8)
        
        ctk.CTkLabel(
            platform_frame, text="平台",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w", pady=(0, 6))
        
        self.platform_var = ctk.StringVar(value=self.config["default_platform"])
        self.platform_menu = ctk.CTkOptionMenu(
            platform_frame,
            variable=self.platform_var,
            values=sorted(PLATFORM_TO_REGIONAL.keys()),
            height=36,
            fg_color=COLORS["bg_dark"],
            button_color=COLORS["accent_dark"],
            button_hover_color=COLORS["accent"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_hover_color=COLORS["bg_hover"]
        )
        self.platform_menu.pack(fill="x")
        
        # 搜索按钮
        self.search_btn = ctk.CTkButton(
            sidebar, text="🔍 搜索玩家",
            height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dark"],
            command=self.search_profile
        )
        self.search_btn.pack(fill="x", padx=20, pady=(16, 8))
        
        # 快捷操作按钮
        btn_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=8)
        
        ctk.CTkButton(
            btn_frame, text="🔄 刷新战绩",
            height=36,
            fg_color=COLORS["bg_dark"],
            hover_color=COLORS["bg_hover"],
            border_width=1,
            border_color=COLORS["border"],
            command=self.refresh_matches
        ).pack(fill="x", pady=2)
        
        ctk.CTkButton(
            btn_frame, text="🎮 查看当前对局",
            height=36,
            fg_color=COLORS["bg_dark"],
            hover_color=COLORS["bg_hover"],
            border_width=1,
            border_color=COLORS["border"],
            command=self.refresh_current_game
        ).pack(fill="x", pady=2)
        
        # 清除缓存按钮
        ctk.CTkButton(
            btn_frame, text="🗑️ 清除缓存",
            height=36,
            fg_color=COLORS["bg_dark"],
            hover_color=COLORS["bg_hover"],
            border_width=1,
            border_color=COLORS["border"],
            command=self._clear_cache
        ).pack(fill="x", pady=2)
        
        # 分隔线
        ctk.CTkFrame(sidebar, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=20, pady=16)
        
        # 搜索历史
        history_label = ctk.CTkFrame(sidebar, fg_color="transparent")
        history_label.pack(fill="x", padx=20)
        
        ctk.CTkLabel(
            history_label, text="最近搜索",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text"]
        ).pack(side="left")
        
        ctk.CTkButton(
            history_label, text="清除",
            width=50, height=24,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_dim"],
            command=self._clear_history
        ).pack(side="right")
        
        self.history_frame = ctk.CTkScrollableFrame(
            sidebar, fg_color="transparent", height=200
        )
        self.history_frame.pack(fill="x", padx=20, pady=8)
        
        self._render_history()
        
        # 底部配置区
        config_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        config_frame.pack(side="bottom", fill="x", padx=20, pady=16)
        
        ctk.CTkButton(
            config_frame, text="⚙️ 设置客户端路径",
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_dim"],
            command=self._open_settings
        ).pack(fill="x")



    def _build_header(self):
        """构建顶部标题栏"""
        header = ctk.CTkFrame(self.content_frame, fg_color="transparent", height=60)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(16, 8))
        
        self.header_title = ctk.CTkLabel(
            header, text="欢迎使用 LoL Scout Pro",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["text"]
        )
        self.header_title.pack(side="left")
        
        self.header_subtitle = ctk.CTkLabel(
            header, text="搜索玩家开始查询",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_dim"]
        )
        self.header_subtitle.pack(side="left", padx=(12, 0))
    
    def _build_tabs(self):
        """构建 Tab 页面"""
        self.tabview = ctk.CTkTabview(
            self.content_frame,
            fg_color=COLORS["bg_dark"],
            segmented_button_fg_color=COLORS["bg_card"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_unselected_color=COLORS["bg_card"],
            segmented_button_selected_hover_color=COLORS["accent_dark"],
            text_color=COLORS["text"]
        )
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=24, pady=8)
        
        # 创建标签页
        self.tab_matches = self.tabview.add("📊 战绩列表")
        self.tab_detail = self.tabview.add("📋 对局详情")
        self.tab_spectate = self.tabview.add("👁️ 观战")
        
        self._build_matches_tab()
        self._build_detail_tab()
        self._build_spectate_tab()
    
    def _build_matches_tab(self):
        """构建战绩列表标签页"""
        self.tab_matches.grid_columnconfigure(0, weight=1)
        self.tab_matches.grid_rowconfigure(0, weight=1)
        
        # 滚动区域
        self.matches_scroll = ctk.CTkScrollableFrame(
            self.tab_matches,
            fg_color="transparent"
        )
        self.matches_scroll.grid(row=0, column=0, sticky="nsew")
        
        # 空状态提示
        self.empty_label = ctk.CTkLabel(
            self.matches_scroll,
            text="🎮 搜索玩家查看战绩",
            font=ctk.CTkFont(size=16),
            text_color=COLORS["text_dim"]
        )
        self.empty_label.pack(pady=100)
    
    def _build_detail_tab(self):
        """构建对局详情标签页"""
        self.tab_detail.grid_columnconfigure(0, weight=1)
        self.tab_detail.grid_rowconfigure(0, weight=1)
        
        self.detail_scroll = ctk.CTkScrollableFrame(
            self.tab_detail,
            fg_color="transparent"
        )
        self.detail_scroll.grid(row=0, column=0, sticky="nsew")
        self.detail_scroll.grid_columnconfigure(0, weight=1)
    
    def _build_spectate_tab(self):
        """构建观战标签页"""
        self.tab_spectate.grid_columnconfigure(0, weight=1)
        self.tab_spectate.grid_rowconfigure(1, weight=1)
        
        # 操作按钮区
        btn_frame = ctk.CTkFrame(self.tab_spectate, fg_color="transparent")
        btn_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        
        ctk.CTkButton(
            btn_frame, text="🔄 刷新对局",
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dark"],
            command=self.refresh_current_game
        ).pack(side="left", padx=(0, 8))
        
        ctk.CTkButton(
            btn_frame, text="🎬 一键观战",
            fg_color=COLORS["purple"],
            hover_color="#8844dd",
            command=self.launch_spectator
        ).pack(side="left", padx=(0, 8))
        
        ctk.CTkButton(
            btn_frame, text="📋 复制观战参数",
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["bg_hover"],
            command=self.copy_spectate_params
        ).pack(side="left")
        
        # 观战信息区
        self.spectate_frame = ctk.CTkFrame(
            self.tab_spectate, fg_color=COLORS["bg_card"], corner_radius=12
        )
        self.spectate_frame.grid(row=1, column=0, sticky="nsew")
        
        self.spectate_label = ctk.CTkLabel(
            self.spectate_frame,
            text="🎮 搜索玩家后，点击「查看当前对局」检测是否在游戏中",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_dim"],
            wraplength=600
        )
        self.spectate_label.pack(expand=True)



    # ========================================================================
    # 搜索历史相关
    # ========================================================================
    
    def _render_history(self):
        """渲染搜索历史列表"""
        for widget in self.history_frame.winfo_children():
            widget.destroy()
        
        entries = self.history.get_all()
        if not entries:
            ctk.CTkLabel(
                self.history_frame,
                text="暂无搜索记录",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_muted"]
            ).pack(pady=8)
            return
        
        for entry in entries:
            btn = ctk.CTkButton(
                self.history_frame,
                text=f"{entry['riot_id']}  ({entry['platform']})",
                font=ctk.CTkFont(size=12),
                fg_color="transparent",
                hover_color=COLORS["bg_hover"],
                text_color=COLORS["text_dim"],
                anchor="w",
                height=32,
                command=lambda e=entry: self._load_from_history(e)
            )
            btn.pack(fill="x", pady=1)
    
    def _load_from_history(self, entry: Dict[str, Any]):
        """从历史记录加载"""
        self.riot_id_entry.delete(0, "end")
        self.riot_id_entry.insert(0, entry["riot_id"])
        self.platform_var.set(entry["platform"])
        self.search_profile()
    
    def _clear_history(self):
        """清除搜索历史"""
        self.history.entries = []
        self.history._save()
        self._render_history()
        self.status_bar.set_status("搜索历史已清除")
    
    def _clear_cache(self):
        """清除缓存"""
        self.cache.clear()
        self.status_bar.set_status("缓存已清除")
    
    def _on_search_input(self, event=None):
        """搜索输入时的自动补全"""
        query = self.riot_id_entry.get()
        matches = self.history.search(query)
        # 简化处理：只在侧边栏显示历史，不做浮动下拉
    
    # ========================================================================
    # 核心功能：搜索玩家
    # ========================================================================
    
    def search_profile(self):
        """搜索玩家"""
        # 先检查输入
        riot_id_input = self.riot_id_entry.get().strip()
        if not riot_id_input:
            self._show_error("请输入 Riot ID")
            return
        
        def task():
            try:
                game_name, tag_line = split_riot_id(riot_id_input)
            except ValueError as e:
                self.after(0, lambda: self._show_error(str(e)))
                self.after(0, lambda: self.status_bar.set_status("搜索失败"))
                return
            
            fallback_platform = self.platform_var.get().strip() or "NA1"
            fallback_regional = PLATFORM_TO_REGIONAL.get(fallback_platform, "americas")
            
            try:
                account = self.api.get_account_by_riot_id(fallback_regional, game_name, tag_line)
            except RiotAPIError as e:
                self.after(0, lambda: self._show_error(str(e)))
                self.after(0, lambda: self.status_bar.set_status("搜索失败"))
                return
            except Exception as e:
                self.after(0, lambda: self._show_error(f"未知错误: {e}"))
                self.after(0, lambda: self.status_bar.set_status("搜索失败"))
                return
            
            puuid = account["puuid"]
            detected_platform = fallback_platform
            detected_regional = fallback_regional
            
            try:
                shard = self.api.get_active_shard(fallback_regional, puuid)
                if shard.get("activeShard"):
                    detected_platform = shard["activeShard"].upper()
                    detected_regional = PLATFORM_TO_REGIONAL.get(detected_platform, fallback_regional)
            except:
                pass
            
            riot_id = f"{account.get('gameName', game_name)}#{account.get('tagLine', tag_line)}"
            
            self.profile = SummonerProfile(
                puuid=puuid,
                riot_id=riot_id,
                platform=detected_platform,
                regional=detected_regional
            )
            
            # 保存到历史
            self.history.add(riot_id, detected_platform, puuid)
            
            self.after(0, self._on_profile_loaded)
        
        self.status_bar.set_status("正在搜索玩家...", loading=True)
        threading.Thread(target=task, daemon=True).start()
    
    def _on_profile_loaded(self):
        """玩家加载完成"""
        if not self.profile:
            return
        
        self.platform_var.set(self.profile.platform)
        self.header_title.configure(text=self.profile.riot_id)
        self.header_subtitle.configure(text=f"平台: {self.profile.platform}")
        self.status_bar.set_status(f"已加载 {self.profile.riot_id}")
        
        self._render_history()
        self.refresh_matches()
    
    # ========================================================================
    # 核心功能：刷新战绩
    # ========================================================================
    
    def refresh_matches(self):
        """刷新战绩列表"""
        if not self.profile:
            self._show_error("请先搜索玩家")
            return
        
        def task():
            try:
                match_ids = self.api.get_match_ids(
                    self.profile.regional,
                    self.profile.puuid,
                    self.config.get("match_count", 10)
                )
            except RiotAPIError as e:
                self.after(0, lambda: self._show_error(str(e)))
                return
            
            def progress(done, total):
                self.after(0, lambda: self.status_bar.set_status(
                    f"加载对局 {done}/{total}...", loading=True
                ))
            
            # 并发获取对局详情
            details = self.api.get_match_details_concurrent(
                self.profile.regional, match_ids, progress
            )
            
            self.match_details_by_id = {mid: detail for mid, detail in details}
            self.after(0, lambda: self._render_matches(details))
        
        self.status_bar.set_status("正在获取战绩...", loading=True)
        threading.Thread(target=task, daemon=True).start()
    
    def _render_matches(self, details: List[Tuple[str, Dict[str, Any]]]):
        """渲染战绩卡片"""
        # 清除旧卡片
        for card in self.match_cards:
            try:
                card.destroy()
            except:
                pass
        self.match_cards.clear()
        
        # 清除空状态标签
        if hasattr(self, 'empty_label') and self.empty_label.winfo_exists():
            try:
                self.empty_label.destroy()
            except:
                pass
        
        # 清除滚动区域所有子组件
        for widget in self.matches_scroll.winfo_children():
            try:
                widget.destroy()
            except:
                pass
        
        if not details:
            self.empty_label = ctk.CTkLabel(
                self.matches_scroll,
                text="暂无战绩记录",
                font=ctk.CTkFont(size=16),
                text_color=COLORS["text_dim"]
            )
            self.empty_label.pack(pady=100)
            self.status_bar.set_status("没有找到战绩")
            return
        
        # 使用 pack 而不是 grid 来布局卡片
        for i, (match_id, detail) in enumerate(details):
            try:
                match_data = self._extract_match_data(match_id, detail)
                card = MatchCard(
                    self.matches_scroll,
                    match_data,
                    on_click=self.show_match_detail
                )
                card.pack(fill="x", pady=4, padx=4)
                self.match_cards.append(card)
            except Exception as e:
                print(f"渲染卡片出错: {e}")
        
        self.status_bar.set_status(f"已加载 {len(details)} 场对局")
        
        # 自动显示第一场详情
        if details:
            self.show_match_detail(details[0][0])
    
    def _extract_match_data(self, match_id: str, detail: Dict[str, Any]) -> Dict[str, Any]:
        """提取对局数据用于卡片显示"""
        info = detail.get("info", {})
        participant = self._find_my_participant(detail)
        
        queue_id = info.get("queueId", 0)
        duration_sec = self._resolve_duration_seconds(info)
        
        start_ts = info.get("gameStartTimestamp") or info.get("gameCreation") or 0
        date_text = ""
        if start_ts:
            date_text = datetime.fromtimestamp(start_ts / 1000).strftime("%m-%d %H:%M")
        
        return {
            "match_id": match_id,
            "champion": participant.get("championName", "Unknown"),
            "kda": f"{participant.get('kills', 0)}/{participant.get('deaths', 0)}/{participant.get('assists', 0)}",
            "win": participant.get("win", False),
            "queue": QUEUE_NAMES.get(queue_id, str(queue_id)),
            "duration": format_duration(duration_sec),
            "date": date_text
        }
    
    def _find_my_participant(self, detail: Dict[str, Any]) -> Dict[str, Any]:
        """找到当前玩家的数据"""
        participants = safe_get(detail, "info", "participants", default=[])
        if self.profile:
            for p in participants:
                if p.get("puuid") == self.profile.puuid:
                    return p
        return participants[0] if participants else {}
    
    def _resolve_duration_seconds(self, info: Dict[str, Any]) -> int:
        """解析对局时长"""
        duration = int(info.get("gameDuration", 0) or 0)
        if info.get("gameEndTimestamp"):
            return duration
        if duration > 100000:
            return duration // 1000
        return duration



    # ========================================================================
    # 对局详情
    # ========================================================================
    
    def show_match_detail(self, match_id: str):
        """显示对局详情"""
        detail = self.match_details_by_id.get(match_id)
        if not detail:
            return
        
        # 清除旧内容
        for widget in self.detail_scroll.winfo_children():
            widget.destroy()
        
        info = detail.get("info", {})
        me = self._find_my_participant(detail)
        
        # 头部信息卡
        header_card = ctk.CTkFrame(self.detail_scroll, fg_color=COLORS["bg_card"], corner_radius=12)
        header_card.grid(row=0, column=0, sticky="ew", pady=4, padx=4)
        header_card.grid_columnconfigure(1, weight=1)
        
        # 胜负指示
        is_win = me.get("win", False)
        result_color = COLORS["win"] if is_win else COLORS["lose"]
        result_text = "胜利" if is_win else "失败"
        
        ctk.CTkLabel(
            header_card, text=result_text,
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=result_color
        ).grid(row=0, column=0, padx=20, pady=16, sticky="w")
        
        # 基本信息
        info_frame = ctk.CTkFrame(header_card, fg_color="transparent")
        info_frame.grid(row=0, column=1, padx=12, pady=16, sticky="ew")
        
        queue_name = QUEUE_NAMES.get(info.get("queueId", 0), str(info.get("queueId", "-")))
        ctk.CTkLabel(
            info_frame, text=f"{queue_name}  ·  {format_duration(self._resolve_duration_seconds(info))}",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_dim"]
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            info_frame, text=f"对局 ID: {match_id}",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w", pady=(4, 0))
        
        # 我的数据卡
        my_card = ctk.CTkFrame(self.detail_scroll, fg_color=COLORS["bg_card"], corner_radius=12)
        my_card.grid(row=1, column=0, sticky="ew", pady=4, padx=4)
        
        ctk.CTkLabel(
            my_card, text="📊 我的数据",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w", padx=16, pady=(12, 8))
        
        stats_frame = ctk.CTkFrame(my_card, fg_color="transparent")
        stats_frame.pack(fill="x", padx=16, pady=(0, 12))
        
        stats = [
            ("英雄", me.get("championName", "-")),
            ("KDA", f"{me.get('kills', 0)}/{me.get('deaths', 0)}/{me.get('assists', 0)}"),
            ("位置", me.get("teamPosition") or me.get("individualPosition") or "-"),
            ("补刀", str(int(me.get("totalMinionsKilled", 0)) + int(me.get("neutralMinionsKilled", 0)))),
            ("经济", f"{me.get('goldEarned', 0):,}"),
            ("伤害", f"{me.get('totalDamageDealtToChampions', 0):,}"),
            ("承伤", f"{me.get('totalDamageTaken', 0):,}"),
            ("视野", str(me.get("visionScore", 0))),
        ]
        
        for i, (label, value) in enumerate(stats):
            col = i % 4
            row = i // 4
            stat_box = ctk.CTkFrame(stats_frame, fg_color=COLORS["bg_dark"], corner_radius=8)
            stat_box.grid(row=row, column=col, padx=4, pady=4, sticky="ew")
            stats_frame.grid_columnconfigure(col, weight=1)
            
            ctk.CTkLabel(
                stat_box, text=label,
                font=ctk.CTkFont(size=11),
                text_color=COLORS["text_muted"]
            ).pack(pady=(8, 2))
            
            ctk.CTkLabel(
                stat_box, text=value,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=COLORS["text"]
            ).pack(pady=(0, 8))
        
        # 全场玩家
        players_card = ctk.CTkFrame(self.detail_scroll, fg_color=COLORS["bg_card"], corner_radius=12)
        players_card.grid(row=2, column=0, sticky="ew", pady=4, padx=4)
        
        ctk.CTkLabel(
            players_card, text="👥 全场玩家",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w", padx=16, pady=(12, 8))
        
        participants = info.get("participants", [])
        
        # 按队伍分组
        team1 = [p for p in participants if p.get("teamId") == 100]
        team2 = [p for p in participants if p.get("teamId") == 200]
        
        for team_label, team_players in [("蓝色方", team1), ("红色方", team2)]:
            team_frame = ctk.CTkFrame(players_card, fg_color=COLORS["bg_dark"], corner_radius=8)
            team_frame.pack(fill="x", padx=16, pady=4)
            
            ctk.CTkLabel(
                team_frame, text=team_label,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["accent"] if team_label == "蓝色方" else COLORS["lose"]
            ).pack(anchor="w", padx=12, pady=(8, 4))
            
            for p in team_players:
                player_row = ctk.CTkFrame(team_frame, fg_color="transparent")
                player_row.pack(fill="x", padx=12, pady=2)
                
                riot_name = p.get("riotIdGameName") or p.get("summonerName") or "Unknown"
                tag = p.get("riotIdTagline", "")
                if tag:
                    riot_name = f"{riot_name}#{tag}"
                
                win_indicator = "W" if p.get("win") else "L"
                win_color = COLORS["win"] if p.get("win") else COLORS["lose"]
                
                ctk.CTkLabel(
                    player_row, text=win_indicator,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=win_color, width=20
                ).pack(side="left")
                
                ctk.CTkLabel(
                    player_row, text=p.get("championName", "-"),
                    font=ctk.CTkFont(size=12),
                    text_color=COLORS["text"], width=100, anchor="w"
                ).pack(side="left", padx=(8, 0))
                
                kda_text = f"{p.get('kills', 0)}/{p.get('deaths', 0)}/{p.get('assists', 0)}"
                ctk.CTkLabel(
                    player_row, text=kda_text,
                    font=ctk.CTkFont(size=12),
                    text_color=COLORS["gold"], width=70
                ).pack(side="left", padx=(8, 0))
                
                ctk.CTkLabel(
                    player_row, text=riot_name,
                    font=ctk.CTkFont(size=11),
                    text_color=COLORS["text_dim"]
                ).pack(side="left", padx=(12, 0))
            
            # 队伍末尾间距
            ctk.CTkFrame(team_frame, height=8, fg_color="transparent").pack()
        
        ctk.CTkFrame(players_card, height=12, fg_color="transparent").pack()
        
        # 切换到详情 Tab
        self.tabview.set("📋 对局详情")
    
    # ========================================================================
    # 观战功能
    # ========================================================================
    
    def refresh_current_game(self):
        """刷新当前对局"""
        if not self.profile:
            self._show_error("请先搜索玩家")
            return
        
        def task():
            try:
                current = self.api.get_current_game(self.profile.platform, self.profile.puuid)
                self.current_game_data = current
                self.after(0, self._render_current_game)
            except RiotAPIError as e:
                self.current_game_data = None
                self.after(0, lambda: self._render_no_game(str(e)))
        
        self.status_bar.set_status("检测当前对局...", loading=True)
        threading.Thread(target=task, daemon=True).start()
    
    def _render_current_game(self):
        """渲染当前对局信息"""
        data = self.current_game_data
        if not data:
            return
        
        self.spectate_label.configure(
            text=f"🎮 {self.profile.riot_id} 正在游戏中！\n\n"
                 f"模式: {QUEUE_NAMES.get(data.get('gameQueueConfigId', 0), '未知')}\n"
                 f"已进行: {format_duration(int(data.get('gameLength', 0)))}\n"
                 f"Game ID: {data.get('gameId', '-')}\n\n"
                 f"点击「一键观战」即可观看！"
        )
        self.tabview.set("👁️ 观战")
        self.status_bar.set_status("检测到进行中的对局")
    
    def _render_no_game(self, error_msg: str):
        """没有找到对局"""
        self.spectate_label.configure(
            text=f"😴 当前没有进行中的对局\n\n{error_msg}"
        )
        self.status_bar.set_status("当前不在游戏中")
    
    def get_spectate_params(self) -> Dict[str, str]:
        """获取观战参数"""
        data = self.current_game_data or {}
        platform_id = str(data.get("platformId") or "")
        game_id = str(data.get("gameId") or "")
        encryption_key = str(safe_get(data, "observers", "encryptionKey", default="") or "")
        server = f"spectator.{platform_id.lower()}.lol.riotgames.com:80" if platform_id else ""
        
        client_path = self.config.get("league_client_path", "")
        manual_command = ""
        if client_path and server and encryption_key and game_id and platform_id:
            manual_command = f'"{client_path}" spectator {server} {encryption_key} {game_id} {platform_id}'
        
        return {
            "platformId": platform_id,
            "gameId": game_id,
            "encryptionKey": encryption_key,
            "server": server,
            "manual_command": manual_command
        }
    
    def copy_spectate_params(self):
        """复制观战参数"""
        if not self.current_game_data:
            self._show_error("请先获取当前对局")
            return
        
        params = self.get_spectate_params()
        one_line = f"spectator {params['server']} {params['encryptionKey']} {params['gameId']} {params['platformId']}"
        
        self.clipboard_clear()
        self.clipboard_append(one_line)
        self.status_bar.set_status("观战参数已复制到剪贴板")
    
    def launch_spectator(self):
        """启动观战"""
        if not self.current_game_data:
            self._show_error("请先获取当前对局")
            return
        
        client_path = self.config.get("league_client_path", "")
        if not client_path:
            self._show_error("请先在设置中配置客户端路径")
            return
        
        client_file = Path(client_path)
        if not client_file.exists():
            self._show_error("客户端路径不存在")
            return
        
        params = self.get_spectate_params()
        if not all([params["platformId"], params["gameId"], params["encryptionKey"]]):
            self._show_error("对局缺少必要观战参数")
            return
        
        args = ["spectator", params["server"], params["encryptionKey"], params["gameId"], params["platformId"]]
        
        try:
            subprocess.Popen([client_path, *args], cwd=str(client_file.parent))
            self.status_bar.set_status("已尝试启动观战")
        except OSError as e:
            self._show_error(f"启动失败: {e}")



    # ========================================================================
    # 设置和辅助功能
    # ========================================================================
    
    def _open_settings(self):
        """打开设置窗口"""
        settings_window = ctk.CTkToplevel(self)
        settings_window.title("⚙️ 设置")
        settings_window.geometry("500x520")
        settings_window.configure(fg_color=COLORS["bg_dark"])
        settings_window.transient(self)
        settings_window.grab_set()
        
        # 确保窗口在最前
        settings_window.focus_force()
        settings_window.lift()
        
        # 标题
        ctk.CTkLabel(
            settings_window, text="设置",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text"]
        ).pack(pady=(20, 16))
        
        # 客户端路径
        path_frame = ctk.CTkFrame(settings_window, fg_color=COLORS["bg_card"], corner_radius=12)
        path_frame.pack(fill="x", padx=20, pady=8)
        
        ctk.CTkLabel(
            path_frame, text="英雄联盟客户端路径",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w", padx=16, pady=(12, 4))
        
        ctk.CTkLabel(
            path_frame, text="选择 Game/League of Legends.exe",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w", padx=16)
        
        path_entry_frame = ctk.CTkFrame(path_frame, fg_color="transparent")
        path_entry_frame.pack(fill="x", padx=16, pady=(8, 12))
        
        path_var = ctk.StringVar(value=self.config.get("league_client_path", ""))
        path_entry = ctk.CTkEntry(
            path_entry_frame,
            textvariable=path_var,
            fg_color=COLORS["bg_dark"],
            border_color=COLORS["border"]
        )
        path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        def browse_path():
            from tkinter import filedialog
            path = filedialog.askopenfilename(
                title="选择 League of Legends.exe",
                filetypes=[("可执行文件", "*.exe")]
            )
            if path:
                path_var.set(path)
        
        ctk.CTkButton(
            path_entry_frame, text="浏览",
            width=70,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dark"],
            command=browse_path
        ).pack(side="right")
        
        # API Key
        api_frame = ctk.CTkFrame(settings_window, fg_color=COLORS["bg_card"], corner_radius=12)
        api_frame.pack(fill="x", padx=20, pady=8)
        
        ctk.CTkLabel(
            api_frame, text="Riot API Key",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w", padx=16, pady=(12, 4))
        
        api_var = ctk.StringVar(value=self.config.get("api_key", ""))
        api_entry = ctk.CTkEntry(
            api_frame,
            textvariable=api_var,
            fg_color=COLORS["bg_dark"],
            border_color=COLORS["border"],
            show="*"
        )
        api_entry.pack(fill="x", padx=16, pady=(8, 12))
        
        # 对局数量
        count_frame = ctk.CTkFrame(settings_window, fg_color=COLORS["bg_card"], corner_radius=12)
        count_frame.pack(fill="x", padx=20, pady=8)
        
        ctk.CTkLabel(
            count_frame, text="拉取对局数量",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w", padx=16, pady=(12, 4))
        
        count_var = ctk.StringVar(value=str(self.config.get("match_count", 10)))
        count_slider = ctk.CTkSlider(
            count_frame,
            from_=5, to=30,
            number_of_steps=25,
            fg_color=COLORS["bg_dark"],
            progress_color=COLORS["accent"],
            button_color=COLORS["accent"],
            command=lambda v: count_var.set(str(int(v)))
        )
        count_slider.set(int(count_var.get()))
        count_slider.pack(fill="x", padx=16, pady=(8, 4))
        
        count_label = ctk.CTkLabel(
            count_frame, textvariable=count_var,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_dim"]
        )
        count_label.pack(anchor="e", padx=16, pady=(0, 12))
        
        # 保存按钮
        def save_settings():
            self.config["league_client_path"] = path_var.get()
            self.config["api_key"] = api_var.get()
            self.config["match_count"] = int(count_var.get())
            save_config(self.config)
            
            # 更新客户端
            self.api = RiotAPIClient(self.config["api_key"], self.cache)
            self.lcu = LCUClient(self.config.get("league_client_path", ""))
            
            self.status_bar.set_status("设置已保存")
            settings_window.destroy()
        
        ctk.CTkButton(
            settings_window, text="保存设置",
            height=40,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dark"],
            command=save_settings
        ).pack(pady=20)
    
    def _show_error(self, message: str):
        """显示错误提示"""
        self.status_bar.set_status(f"错误: {message}")
        
        # 使用 CTkToplevel 显示错误
        error_window = ctk.CTkToplevel(self)
        error_window.title("错误")
        error_window.geometry("420x120")
        error_window.configure(fg_color=COLORS["bg_card"])
        error_window.transient(self)
        error_window.grab_set()
        
        # 居中显示
        error_window.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 420) // 2
        y = self.winfo_y() + (self.winfo_height() - 120) // 2
        error_window.geometry(f"+{x}+{y}")
        
        # 错误图标和文字
        content = ctk.CTkFrame(error_window, fg_color="transparent")
        content.pack(expand=True, fill="both", padx=20, pady=20)
        
        ctk.CTkLabel(
            content, text=f"❌ {message}",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["lose"],
            wraplength=380
        ).pack(expand=True)
        
        # 关闭按钮
        ctk.CTkButton(
            content, text="确定", width=80,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dark"],
            command=error_window.destroy
        ).pack(pady=(10, 0))
        
        # 5 秒后自动关闭
        error_window.after(5000, lambda: error_window.destroy() if error_window.winfo_exists() else None)


# ============================================================================
# 主入口
# ============================================================================

def main():
    app = LoLScoutApp()
    app.mainloop()


if __name__ == "__main__":
    main()
