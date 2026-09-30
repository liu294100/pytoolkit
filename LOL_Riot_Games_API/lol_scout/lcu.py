"""LCU（League Client Update）本地客户端 API + Live Client Data API

- 通过进程命令行（--app-port / --remoting-auth-token）或 lockfile 自动发现客户端
- 支持：当前账号、游戏状态、选人阶段队友、战绩（腾讯服也可用）、好友、客户端内观战
- Live Client Data（127.0.0.1:2999）：游戏进行中实时数据
"""

from __future__ import annotations

import base64
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

RIOT_METADATA = Path("C:/ProgramData/Riot Games/Metadata/league_of_legends.live/"
                     "league_of_legends.live.product_settings.yaml")


class LCUError(Exception):
    pass


def detect_install_dir(client_path: str = "") -> Optional[Path]:
    """返回 League of Legends 安装根目录（包含 LeagueClient.exe 与 Game/）"""
    if client_path:
        p = Path(client_path)
        for parent in [p.parent, *p.parents][:4]:
            if (parent / "Game").is_dir() or (parent / "LeagueClient.exe").exists():
                return parent
    if RIOT_METADATA.exists():
        try:
            text = RIOT_METADATA.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r'product_install_full_path:\s*"([^"]+)"', text)
            if m:
                p = Path(m.group(1).replace("\\\\", "\\"))
                if p.exists():
                    return p
        except OSError:
            pass
    for drive in "CDEFGH":
        for sub in ("Riot Games/League of Legends", "Games/Riot Games/League of Legends"):
            p = Path(f"{drive}:/{sub}")
            if p.exists():
                return p
    return None


def detect_game_exe(client_path: str = "") -> Optional[Path]:
    if client_path and Path(client_path).name.lower() == "league of legends.exe" and Path(client_path).exists():
        return Path(client_path)
    root = detect_install_dir(client_path)
    if root:
        exe = root / "Game" / "League of Legends.exe"
        if exe.exists():
            return exe
    return None


class LCUClient:
    def __init__(self, client_path: str = ""):
        self.client_path = client_path
        self.session = requests.Session()
        self.session.verify = False
        self._creds: Optional[Tuple[int, str]] = None
        self._lock = threading.Lock()
        self.me: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------ discovery
    def _from_process(self) -> Optional[Tuple[int, str]]:
        if psutil is None:
            return None
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                if (proc.info["name"] or "").lower() not in ("leagueclientux.exe", "leagueclientux"):
                    continue
                cmd = " ".join(proc.info["cmdline"] or [])
            except (psutil.Error, OSError):
                continue
            port = re.search(r"--app-port=(\d+)", cmd)
            token = re.search(r"--remoting-auth-token=([\w-]+)", cmd)
            if port and token:
                return int(port.group(1)), token.group(1)
        return None

    def _from_lockfile(self) -> Optional[Tuple[int, str]]:
        root = detect_install_dir(self.client_path)
        candidates = [root / "lockfile"] if root else []
        for lf in candidates:
            try:
                parts = lf.read_text(encoding="utf-8").strip().split(":")
                if len(parts) >= 5:
                    return int(parts[2]), parts[3]
            except OSError:
                continue
        return None

    def connect(self) -> bool:
        with self._lock:
            creds = self._from_process() or self._from_lockfile()
            self._creds = creds
            if not creds:
                self.me = None
                return False
            port, token = creds
            auth = base64.b64encode(f"riot:{token}".encode()).decode()
            self.session.headers.update({"Authorization": f"Basic {auth}", "Accept": "application/json"})
        try:
            self.me = self.get("/lol-summoner/v1/current-summoner")
            return True
        except LCUError:
            self._creds = None
            self.me = None
            return False

    @property
    def connected(self) -> bool:
        return self._creds is not None

    # ---------------------------------------------------------------- http
    def request(self, method: str, path: str, json_body: Any = None, timeout: float = 6) -> requests.Response:
        if not self._creds:
            raise LCUError("未连接到英雄联盟客户端，请先启动并登录客户端。")
        url = f"https://127.0.0.1:{self._creds[0]}{path}"
        try:
            return self.session.request(method, url, json=json_body, timeout=timeout)
        except requests.RequestException as exc:
            self._creds = None
            raise LCUError(f"客户端连接断开：{exc}") from exc

    def get(self, path: str) -> Any:
        resp = self.request("GET", path)
        if resp.status_code >= 400:
            raise LCUError(f"LCU {path} -> HTTP {resp.status_code}")
        return resp.json() if resp.content else None

    # ------------------------------------------------------------- queries
    def gameflow_phase(self) -> str:
        try:
            return self.get("/lol-gameflow/v1/gameflow-phase") or "None"
        except LCUError:
            return "None"

    def gameflow_session(self) -> Dict[str, Any]:
        return self.get("/lol-gameflow/v1/session") or {}

    def champ_select(self) -> Dict[str, Any]:
        return self.get("/lol-champ-select/v1/session") or {}

    def region(self) -> Dict[str, Any]:
        try:
            return self.get("/riotclient/region-locale") or {}
        except LCUError:
            return {}

    def summoner_by_puuid(self, puuid: str) -> Dict[str, Any]:
        return self.get(f"/lol-summoner/v2/summoners/puuid/{puuid}") or {}

    def summoner_by_id(self, summoner_id: int) -> Dict[str, Any]:
        return self.get(f"/lol-summoner/v1/summoners/{summoner_id}") or {}

    def summoner_by_riot_id(self, game_name: str, tag_line: str) -> Dict[str, Any]:
        return self.get(f"/lol-summoner/v1/summoners?name={quote(f'{game_name}#{tag_line}')}") or {}

    def ranked_stats(self, puuid: str) -> Dict[str, Any]:
        return self.get(f"/lol-ranked/v1/ranked-stats/{puuid}") or {}

    def match_history(self, puuid: str, count: int = 20) -> List[Dict[str, Any]]:
        data = self.get(f"/lol-match-history/v1/products/lol/{puuid}/matches"
                        f"?begIndex=0&endIndex={max(1, count) - 1}") or {}
        return (data.get("games") or {}).get("games") or []

    def game_detail(self, game_id: int) -> Dict[str, Any]:
        return self.get(f"/lol-match-history/v1/games/{game_id}") or {}

    def friends(self) -> List[Dict[str, Any]]:
        try:
            return self.get("/lol-chat/v1/friends") or []
        except LCUError:
            return []

    # ------------------------------------------------------------ spectate
    def spectate(self, game_name: str, tag_line: str, puuid: str) -> None:
        """在客户端内发起观战（仅限与客户端同区服的玩家）"""
        payload = {
            "allowObserveMode": "ALL",
            "dropInSpectateGameId": f"{game_name}#{tag_line}" if tag_line else game_name,
            "gameQueueType": "",
            "puuid": puuid,
        }
        resp = self.request("POST", "/lol-spectator/v1/spectate/launch", json_body=payload)
        if resp.status_code not in (200, 201, 202, 204):
            detail = ""
            try:
                detail = resp.json().get("message", "")
            except ValueError:
                pass
            raise LCUError(f"客户端观战失败：HTTP {resp.status_code} {detail}".strip())


class LiveClient:
    """游戏内 Live Client Data API（无需鉴权，仅游戏进行中可用）"""

    BASE = "https://127.0.0.1:2999/liveclientdata"

    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False

    def all_data(self) -> Optional[Dict[str, Any]]:
        try:
            resp = self.session.get(f"{self.BASE}/allgamedata", timeout=2)
            if resp.status_code == 200:
                return resp.json()
        except requests.RequestException:
            pass
        return None
