"""OP.GG 三方数据

1. OP.GG 官方 MCP 服务（https://mcp-api.op.gg/mcp，Streamable HTTP / JSON-RPC，无需 Key）
   返回的是一种紧凑文本格式：
       class Summoner: game_name,tagline,level
       class LeagueStat: game_type,win
       LolGetSummonerProfile(Data(Summoner("Faker","KR1",943,[LeagueStat("SOLORANKED",423)])))
   这里实现了一个小型解析器，把它还原为 dict/list。
2. 网页跳转链接：OP.GG 主页/实时对局、Porofessor 实时对局、DeepLoL、League of Graphs。
"""

from __future__ import annotations

import json
import re
import threading
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

from .config import DEFAULT_TIMEOUT, PLATFORM_TO_OPGG, PLATFORM_TO_PORO
from .storage import Storage

MCP_URL = "https://mcp-api.op.gg/mcp"


class OPGGError(Exception):
    pass


# ============================================================================
# 文本格式解析器
# ============================================================================

_CLASS_RE = re.compile(r"^class\s+(\w+)\s*:\s*(.*)$")


class _Parser:
    def __init__(self, text: str, classes: Dict[str, List[str]]):
        self.s = text
        self.i = 0
        self.classes = classes

    def ws(self) -> None:
        while self.i < len(self.s) and self.s[self.i] in " \t\r\n":
            self.i += 1

    def parse(self) -> Any:
        self.ws()
        if self.i >= len(self.s):
            return None
        ch = self.s[self.i]
        if ch == '"':
            return self._string()
        if ch == "[":
            return self._list()
        if ch == "{":
            return self._json_object()
        if ch == "-" or ch.isdigit():
            return self._number()
        m = re.compile(r"[A-Za-z_]\w*").match(self.s, self.i)
        if not m:
            raise OPGGError(f"解析失败 @ {self.i}: {self.s[self.i:self.i + 30]!r}")
        word = m.group(0)
        self.i = m.end()
        if word == "null":
            return None
        if word == "true":
            return True
        if word == "false":
            return False
        self.ws()
        if self.i < len(self.s) and self.s[self.i] == "(":
            return self._construct(word)
        return word

    def _string(self) -> str:
        j = self.i + 1
        while j < len(self.s):
            c = self.s[j]
            if c == "\\":
                j += 2
                continue
            if c == '"':
                break
            j += 1
        raw = self.s[self.i:j + 1]
        self.i = j + 1
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw.strip('"')

    def _number(self) -> Any:
        m = re.compile(r"-?\d+(\.\d+)?([eE][-+]?\d+)?").match(self.s, self.i)
        self.i = m.end()
        text = m.group(0)
        return float(text) if ("." in text or "e" in text.lower()) else int(text)

    def _items(self, close: str) -> List[Any]:
        self.i += 1
        items: List[Any] = []
        self.ws()
        if self.s[self.i] == close:
            self.i += 1
            return items
        while True:
            items.append(self.parse())
            self.ws()
            c = self.s[self.i]
            self.i += 1
            if c == ",":
                continue
            if c == close:
                return items
            raise OPGGError(f"期望 ',' 或 '{close}' @ {self.i}")

    def _list(self) -> List[Any]:
        return self._items("]")

    def _json_object(self) -> Any:
        decoder = json.JSONDecoder()
        obj, end = decoder.raw_decode(self.s, self.i)
        self.i = end
        return obj

    def _construct(self, name: str) -> Dict[str, Any]:
        args = self._items(")")
        fields = self.classes.get(name)
        if not fields:
            return {"_type": name, "_args": args}
        # 数组字段在声明里可能写成 items[]
        keys = [f.rstrip("[]") for f in fields]
        obj = {k: (args[i] if i < len(args) else None) for i, k in enumerate(keys)}
        return obj


def parse_opgg_text(text: str) -> Any:
    classes: Dict[str, List[str]] = {}
    body_lines: List[str] = []
    for line in text.splitlines():
        m = _CLASS_RE.match(line.strip())
        if m:
            classes[m.group(1)] = [f.strip() for f in m.group(2).split(",") if f.strip()]
        else:
            body_lines.append(line)
    body = "\n".join(body_lines).strip()
    if not body:
        return None
    if body[0] in "{[" and not classes:
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            pass
    return _Parser(body, classes).parse()


# ============================================================================
# MCP 客户端
# ============================================================================

class OPGGClient:
    PROFILE_FIELDS = [
        "data.summoner.{game_name,tagline,level,profile_image_url,puuid,updated_at}",
        "data.summoner.ladder_rank.{rank,total}",
        "data.summoner.league_stats[].{game_type,win,lose,is_hot_streak}",
        "data.summoner.league_stats[].tier_info.{tier,division,lp}",
        "data.summoner.most_champions.champion_stats[].{id,champion_name,play,win,lose,kill,death,assist,op_score}",
        "data.summoner.previous_seasons[].season_id",
        "data.summoner.previous_seasons[].tier_info.{tier,division}",
        "data.summoner.player.{nickname,real_name}",
        "data.summoner.player.current_pro_team.pro_team.{name,short_name}",
    ]
    RANK_FIELDS = [
        "data.summoner.{game_name,tagline,level}",
        "data.summoner.league_stats[].{game_type,win,lose}",
        "data.summoner.league_stats[].tier_info.{tier,division,lp}",
        "data.summoner.most_champions.champion_stats[].{id,champion_name,play,win}",
        "data.summoner.player.{nickname}",
    ]
    MATCH_FIELDS = [
        "data.game_history[].{id,created_at,game_length_second,game_type}",
        "data.game_history[].average_tier_info.{tier,division}",
        "data.game_history[].participants[].{champion_id,champion_name,position,team_key,items[],spells[]}",
        "data.game_history[].participants[].summoner.{game_name,tagline}",
        "data.game_history[].participants[].stats.{kill,death,assist,op_score,op_score_rank,result,"
        "minion_kill,neutral_minion_kill,total_damage_dealt_to_champions}",
    ]

    def __init__(self, storage: Storage, lang: str = "zh_CN"):
        self.storage = storage
        self.lang = lang
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "LoLScout/3.0",
        })
        self._sid: Optional[str] = None
        self._id = 0
        self._lock = threading.Lock()

    # ------------------------------------------------------------ protocol
    @staticmethod
    def _decode(resp: requests.Response) -> Dict[str, Any]:
        ctype = resp.headers.get("Content-Type", "")
        if "event-stream" in ctype:
            for line in resp.text.splitlines():
                if line.startswith("data:"):
                    return json.loads(line[5:].strip())
            raise OPGGError("OP.GG 返回为空")
        return resp.json()

    def _next_id(self) -> int:
        with self._lock:
            self._id += 1
            return self._id

    def _rpc(self, method: str, params: Optional[Dict[str, Any]] = None, notify: bool = False) -> Any:
        body: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            body["params"] = params
        if not notify:
            body["id"] = self._next_id()
        headers = {"mcp-session-id": self._sid} if self._sid else {}
        try:
            resp = self.session.post(MCP_URL, json=body, headers=headers, timeout=DEFAULT_TIMEOUT * 2)
        except requests.RequestException as exc:
            raise OPGGError(f"连接 OP.GG 失败：{exc}") from exc
        if resp.status_code in (400, 404) and self._sid and method != "initialize":
            raise _SessionExpired()
        if notify:
            return None
        if resp.status_code != 200:
            raise OPGGError(f"OP.GG HTTP {resp.status_code}")
        data = self._decode(resp)
        if "error" in data:
            raise OPGGError(data["error"].get("message", "OP.GG 错误"))
        if method == "initialize":
            self._sid = resp.headers.get("mcp-session-id")
        return data.get("result")

    def _ensure_session(self) -> None:
        if self._sid is not None:
            return
        self._rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                 "clientInfo": {"name": "lol-scout", "version": "3.0"}})
        self._rpc("notifications/initialized", notify=True)

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        for _ in range(2):
            try:
                self._ensure_session()
                result = self._rpc("tools/call", {"name": name, "arguments": arguments})
                break
            except _SessionExpired:
                self._sid = None
        else:
            raise OPGGError("OP.GG 会话失效")
        contents = (result or {}).get("content") or []
        text = "".join(c.get("text", "") for c in contents if c.get("type") == "text")
        if (result or {}).get("isError"):
            raise OPGGError(text[:200] or "OP.GG 工具调用失败")
        parsed = parse_opgg_text(text)
        if isinstance(parsed, dict):
            return parsed
        raise OPGGError(text[:200] if text else "OP.GG 无数据")

    # ------------------------------------------------------------ high level
    @staticmethod
    def region_of(platform: str) -> str:
        return PLATFORM_TO_OPGG.get(platform.upper(), platform.lower()).upper()

    def _cached_tool(self, key: str, ttl: float, name: str, args: Dict[str, Any]) -> Any:
        hit = self.storage.get(key)
        if hit is not None:
            return hit
        data = self.call_tool(name, args)
        self.storage.set(key, data, ttl=ttl)
        return data

    def profile(self, platform: str, game_name: str, tag_line: str, light: bool = False) -> Dict[str, Any]:
        fields = self.RANK_FIELDS if light else self.PROFILE_FIELDS
        region = self.region_of(platform)
        key = f"opgg:profile:{'l' if light else 'f'}:{region}:{game_name.lower()}#{tag_line.lower()}"
        data = self._cached_tool(key, 600, "lol_get_summoner_profile", {
            "game_name": game_name, "tag_line": tag_line, "region": region,
            "lang": self.lang, "desired_output_fields": fields,
        })
        summoner = ((data or {}).get("data") or {}).get("summoner")
        if not summoner:
            raise OPGGError("OP.GG 上没有找到该玩家")
        return summoner

    def matches(self, platform: str, game_name: str, tag_line: str, limit: int = 20) -> List[Dict[str, Any]]:
        region = self.region_of(platform)
        key = f"opgg:matches:{region}:{game_name.lower()}#{tag_line.lower()}:{limit}"
        data = self._cached_tool(key, 120, "lol_list_summoner_matches", {
            "game_name": game_name, "tag_line": tag_line, "region": region,
            "lang": self.lang, "limit": max(5, min(20, limit)),
            "desired_output_fields": self.MATCH_FIELDS,
        })
        return ((data or {}).get("data") or {}).get("game_history") or []

    GAME_FIELDS = [
        "data.game_detail.{id,created_at,game_length_second,game_type}",
        "data.game_detail.average_tier_info.{tier,division}",
        "data.game_detail.teams[].key",
        "data.game_detail.teams[].game_stat.{is_win,champion_kill,gold_earned,tower_kill,dragon_kill,baron_kill}",
        "data.game_detail.teams[].participants[].{champion_id,champion_name,position,team_key,items[],spells[],is_target}",
        "data.game_detail.teams[].participants[].summoner.{game_name,tagline,puuid}",
        "data.game_detail.teams[].participants[].stats.{kill,death,assist,op_score,op_score_rank,result,champion_level,"
        "minion_kill,neutral_minion_kill,gold_earned,total_damage_dealt_to_champions,total_damage_taken,ward_place}",
    ]

    def game_detail(self, platform: str, game_id: str, created_at: str) -> Dict[str, Any]:
        region = self.region_of(platform)
        key = f"opgg:game:{region}:{game_id}"
        data = self.storage.get(key)
        if data is None:
            data = self.call_tool("lol_get_summoner_game_detail", {
                "region": region, "game_id": game_id, "created_at": created_at,
                "lang": self.lang, "desired_output_fields": self.GAME_FIELDS,
            })
            self.storage.set(key, data, ttl=None)  # 已结束对局不会变
        detail = ((data or {}).get("data") or {}).get("game_detail")
        if not detail:
            raise OPGGError("OP.GG 没有该对局详情")
        return detail

    # --------------------------------------------------------------- summary
    @staticmethod
    def solo_rank(summoner: Dict[str, Any]) -> Dict[str, Any]:
        """提取单双排（没有则灵活）段位摘要"""
        stats = summoner.get("league_stats") or []
        order = {"SOLORANKED": 0, "FLEXRANKED": 1}
        stats = sorted([s for s in stats if isinstance(s, dict)], key=lambda s: order.get(s.get("game_type"), 9))
        for s in stats:
            tier = (s.get("tier_info") or {}).get("tier")
            if tier:
                win, lose = s.get("win") or 0, s.get("lose") or 0
                return {
                    "queue": s.get("game_type"), "tier": tier,
                    "division": (s.get("tier_info") or {}).get("division"),
                    "lp": (s.get("tier_info") or {}).get("lp"),
                    "win": win, "lose": lose,
                    "winrate": round(win * 100 / max(1, win + lose)),
                }
        return {}


class _SessionExpired(Exception):
    pass


# ============================================================================
# 网页链接
# ============================================================================

def _slug(game_name: str, tag_line: str) -> str:
    return quote(f"{game_name}-{tag_line}")


def web_links(platform: str, game_name: str, tag_line: str) -> Dict[str, str]:
    op = PLATFORM_TO_OPGG.get(platform.upper(), platform.lower())
    poro = PLATFORM_TO_PORO.get(platform.upper(), platform.lower())
    slug = _slug(game_name, tag_line)
    return {
        "OP.GG 主页": f"https://op.gg/lol/summoners/{op}/{slug}",
        "OP.GG 实时对局": f"https://op.gg/lol/summoners/{op}/{slug}/ingame",
        "Porofessor 实时": f"https://porofessor.gg/live/{poro}/{slug}",
        "DeepLoL": f"https://www.deeplol.gg/summoner/{op.upper()}/{slug}",
        "League of Graphs": f"https://www.leagueofgraphs.com/summoner/{poro}/{slug}",
        "U.GG": f"https://u.gg/lol/profile/{platform.lower()}/{slug}/overview",
    }
