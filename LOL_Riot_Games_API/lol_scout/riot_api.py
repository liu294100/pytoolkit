"""Riot 官方 API 客户端

性能要点：
- requests.Session + 连接池复用 TLS 连接
- 每个路由域独立的滑动窗口限流，429 时读取 Retry-After 自动退避重试
- 对局详情永久缓存（不可变），账号/段位短 TTL 缓存
- 线程池并发拉取对局详情，按完成顺序流式回调，UI 可边拉边渲染
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Sequence
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter

from .config import DEFAULT_TIMEOUT, PLATFORM_TO_REGIONAL, api_key_valid
from .ratelimit import LimiterPool
from .storage import Storage


class RiotAPIError(Exception):
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


class NotFound(RiotAPIError):
    pass


class RiotAPIClient:
    MAX_RETRIES = 3

    def __init__(self, api_key: str, storage: Storage, limits: Sequence[Sequence[int]]):
        self.api_key = (api_key or "").strip()
        self.storage = storage
        self.limiters = LimiterPool(limits)
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=8, pool_maxsize=16, max_retries=0)
        self.session.mount("https://", adapter)
        self.session.headers.update({"X-Riot-Token": self.api_key, "Accept-Encoding": "gzip"})
        self.executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="riot")
        self._inflight: Dict[str, threading.Event] = {}
        self._inflight_lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return api_key_valid(self.api_key)

    # ------------------------------------------------------------------ core
    def _get(self, host: str, path: str, params: Optional[Dict[str, Any]] = None,
             ttl: Optional[float] = 300, cache: bool = True) -> Any:
        if not self.enabled:
            raise RiotAPIError("未配置有效的 Riot API Key（RGAPI-...），可在设置中填写。")
        url = f"https://{host}.api.riotgames.com{path}"
        key = f"riot:{url}:{sorted((params or {}).items())}"
        if cache:
            hit = self.storage.get(key)
            if hit is not None:
                return hit
            # 同一 URL 并发请求合并：后到的线程等待先到的结果
            with self._inflight_lock:
                ev = self._inflight.get(key)
                owner = ev is None
                if owner:
                    ev = self._inflight[key] = threading.Event()
            if not owner:
                ev.wait(timeout=DEFAULT_TIMEOUT * 2)
                hit = self.storage.get(key)
                if hit is not None:
                    return hit
        try:
            data = self._request(host, url, params)
            if cache:
                self.storage.set(key, data, ttl=ttl)
            return data
        finally:
            if cache:
                with self._inflight_lock:
                    ev = self._inflight.pop(key, None)
                if ev:
                    ev.set()

    def _request(self, host: str, url: str, params: Optional[Dict[str, Any]]) -> Any:
        limiter = self.limiters.for_host(host)
        last_err: Optional[Exception] = None
        for attempt in range(self.MAX_RETRIES + 1):
            limiter.acquire()
            try:
                resp = self.session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            except requests.RequestException as exc:
                last_err = exc
                time.sleep(0.5 * (attempt + 1))
                continue
            code = resp.status_code
            if code == 200:
                return resp.json()
            if code == 429:
                retry_after = float(resp.headers.get("Retry-After", "1") or 1)
                limiter.block_for(retry_after)
                last_err = RiotAPIError("触发 Riot API 限流", 429)
                continue
            if code in (500, 502, 503, 504):
                last_err = RiotAPIError(f"Riot 服务器错误 HTTP {code}", code)
                time.sleep(0.6 * (attempt + 1))
                continue
            if code == 404:
                raise NotFound("没有找到数据（玩家不存在或当前不在游戏中）", 404)
            if code == 401:
                raise RiotAPIError("API Key 缺失或无效", 401)
            if code == 403:
                raise RiotAPIError("API Key 已过期或无权访问该接口（开发者 Key 每 24 小时过期）", 403)
            if code == 400:
                raise RiotAPIError("请求参数错误（检查区服与 Riot ID）", 400)
            raise RiotAPIError(f"接口报错：HTTP {code}", code)
        if isinstance(last_err, RiotAPIError):
            raise last_err
        raise RiotAPIError(f"网络请求失败：{last_err}")

    # --------------------------------------------------------------- account
    @staticmethod
    def regional_of(platform: str) -> str:
        return PLATFORM_TO_REGIONAL.get(platform.upper(), "americas")

    def account_by_riot_id(self, platform: str, game_name: str, tag_line: str) -> Dict[str, Any]:
        path = f"/riot/account/v1/accounts/by-riot-id/{quote(game_name)}/{quote(tag_line)}"
        return self._get(self.regional_of(platform), path, ttl=3600)

    def account_by_puuid(self, platform: str, puuid: str) -> Dict[str, Any]:
        return self._get(self.regional_of(platform), f"/riot/account/v1/accounts/by-puuid/{puuid}", ttl=3600)

    def lol_region_of(self, platform: str, puuid: str) -> Optional[str]:
        """查询玩家实际所在 LoL 区服（跨区搜索时自动纠正）"""
        try:
            data = self._get(self.regional_of(platform),
                             f"/riot/account/v1/region/by-game/lol/by-puuid/{puuid}", ttl=86400)
            region = (data or {}).get("region")
            return region.upper() if region else None
        except RiotAPIError:
            return None

    # -------------------------------------------------------------- summoner
    def summoner(self, platform: str, puuid: str) -> Dict[str, Any]:
        return self._get(platform.lower(), f"/lol/summoner/v4/summoners/by-puuid/{puuid}", ttl=600)

    def league_entries(self, platform: str, puuid: str) -> List[Dict[str, Any]]:
        return self._get(platform.lower(), f"/lol/league/v4/entries/by-puuid/{puuid}", ttl=300)

    def top_mastery(self, platform: str, puuid: str, count: int = 6) -> List[Dict[str, Any]]:
        return self._get(platform.lower(),
                         f"/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top",
                         params={"count": count}, ttl=3600)

    # ----------------------------------------------------------------- match
    def match_ids(self, platform: str, puuid: str, count: int = 20, start: int = 0,
                  queue: Optional[int] = None) -> List[str]:
        params: Dict[str, Any] = {"start": start, "count": max(1, min(100, count))}
        if queue:
            params["queue"] = queue
        return self._get(self.regional_of(platform), f"/lol/match/v5/matches/by-puuid/{puuid}/ids",
                         params=params, ttl=60)

    def match(self, platform: str, match_id: str) -> Dict[str, Any]:
        # 对局结束后数据不会再变，永久缓存
        return self._get(self.regional_of(platform), f"/lol/match/v5/matches/{match_id}", ttl=None)

    def matches_stream(self, platform: str, match_ids: List[str],
                       on_item: Callable[[str, Optional[Dict[str, Any]], int, int], None]) -> None:
        """并发拉取对局详情，每完成一场回调一次 (match_id, detail|None, done, total)"""
        total = len(match_ids)
        futures = {self.executor.submit(self._safe_match, platform, mid): mid for mid in match_ids}
        done = 0
        for fut in as_completed(futures):
            done += 1
            on_item(futures[fut], fut.result(), done, total)

    def _safe_match(self, platform: str, match_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self.match(platform, match_id)
        except RiotAPIError:
            return None

    # ------------------------------------------------------------- spectator
    def active_game(self, platform: str, puuid: str) -> Dict[str, Any]:
        return self._get(platform.lower(), f"/lol/spectator/v5/active-games/by-summoner/{puuid}", cache=False)

    def featured_games(self, platform: str) -> Dict[str, Any]:
        return self._get(platform.lower(), "/lol/spectator/v5/featured-games", ttl=60)

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)
