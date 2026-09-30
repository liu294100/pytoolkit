"""业务编排层：多数据源自动选择 + 降级

数据源优先级
- 玩家查找：Riot Account API → LCU 客户端 → OP.GG
- 战绩：Riot Match-V5（需 Key）→ LCU（同区服客户端，腾讯服也可）→ OP.GG（无需 Key）
- 实时对局：Riot Spectator-V5 → LCU（本人：选人/游戏中）
- 实时对局段位：OP.GG（并发）→ LCU ranked-stats
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import fuzzy, models
from .config import PLATFORM_DEFAULT_TAGS, api_key_valid, parse_riot_id
from .ddragon import DataDragon
from .lcu import LCUClient, LCUError, LiveClient
from .opgg import OPGGClient, OPGGError
from .riot_api import NotFound, RiotAPIClient, RiotAPIError
from .spectator import SpectateParams, launch as launch_game, write_bat
from .storage import Storage

LCU_REGION_TO_PLATFORM = {
    "NA": "NA1", "EUW": "EUW1", "EUNE": "EUN1", "KR": "KR", "JP": "JP1", "BR": "BR1",
    "LA1": "LA1", "LA2": "LA2", "LAN": "LA1", "LAS": "LA2", "OCE": "OC1", "OC1": "OC1",
    "TR": "TR1", "RU": "RU", "SG": "SG2", "SG2": "SG2", "TW": "TW2", "TW2": "TW2",
    "VN": "VN2", "VN2": "VN2", "ME": "ME1", "ME1": "ME1", "PH": "SG2", "TH": "SG2",
}


class ScoutError(Exception):
    pass


@dataclass
class Profile:
    game_name: str
    tag_line: str
    platform: str
    puuid: str = ""
    level: int = 0
    icon_url: str = ""
    ranks: List[Dict[str, Any]] = field(default_factory=list)   # [{queue,tier,division,lp,win,lose,winrate}]
    top_champs: List[Dict[str, Any]] = field(default_factory=list)
    note: str = ""          # 职业选手信息等
    source: str = ""

    @property
    def riot_id(self) -> str:
        return f"{self.game_name}#{self.tag_line}"


class ScoutService:
    def __init__(self, config: Dict[str, Any], storage: Storage, dd: DataDragon):
        self.config = config
        self.storage = storage
        self.dd = dd
        self.pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="scout")
        self.lcu = LCUClient(config.get("league_client_path", ""))
        self.live_client = LiveClient()
        self.lcu_platform: str = ""
        self._friends: List[Dict[str, Any]] = []
        self.rebuild_clients()

    def rebuild_clients(self) -> None:
        self.riot = RiotAPIClient(self.config.get("api_key", ""), self.storage, self.config.get("rate_limits"))
        self.opgg = OPGGClient(self.storage, lang=self.config.get("locale", "zh_CN"))
        self.lcu.client_path = self.config.get("league_client_path", "")

    @property
    def has_key(self) -> bool:
        return api_key_valid(self.config.get("api_key", ""))

    @property
    def opgg_on(self) -> bool:
        return bool(self.config.get("opgg_enabled", True))

    # ================================================================ LCU
    def connect_lcu(self) -> bool:
        ok = self.lcu.connect()
        if ok:
            self.lcu_platform = self._detect_lcu_platform()
            me = self.lcu.me or {}
            if me.get("gameName"):
                self.storage.touch_player(f"{me['gameName']}#{me.get('tagLine', '')}", self.lcu_platform,
                                          me.get("puuid"), source="lcu")
            self._friends = self.lcu.friends()
            rows = []
            for f in self._friends:
                if f.get("gameName") and f.get("gameTag"):
                    rows.append((f"{f['gameName']}#{f['gameTag']}", self.lcu_platform, f.get("puuid")))
            self.storage.touch_players_bulk(rows, source="friend")
        else:
            self.lcu_platform = ""
        return ok

    def _detect_lcu_platform(self) -> str:
        try:
            me = self.lcu.get("/lol-chat/v1/me") or {}
            if me.get("platformId"):
                return str(me["platformId"]).upper()
        except LCUError:
            pass
        region = (self.lcu.region().get("region") or "").upper()
        return LCU_REGION_TO_PLATFORM.get(region, region)

    def lcu_status(self) -> Dict[str, Any]:
        if not self.lcu.connected and not self.connect_lcu():
            return {"connected": False}
        phase = self.lcu.gameflow_phase()
        if not self.lcu.connected:
            return {"connected": False}
        return {"connected": True, "me": self.lcu.me or {}, "phase": phase, "platform": self.lcu_platform}

    def lcu_same_region(self, platform: str) -> bool:
        return self.lcu.connected and self.lcu_platform.upper() == platform.upper()

    # ========================================================== suggestions
    def suggestions(self, query: str, platform: str, limit: int = 8) -> List[Dict[str, Any]]:
        players = self.storage.all_players()
        if not query.strip():
            return self.storage.recent_players(limit)

        def boost(p: Dict[str, Any]) -> float:
            return fuzzy.player_boost(p) + (3 if p.get("platform") == platform else 0)

        return [p for _, p in fuzzy.fuzzy_filter(query, players, fuzzy.player_keys, limit=limit,
                                                  threshold=50, boost=boost)]

    # =============================================================== resolve
    def resolve(self, query: str, platform: str) -> Profile:
        """把用户输入解析为玩家。缺少 #Tag 时先查本地索引，再尝试区服默认 Tag"""
        name, tag = parse_riot_id(query)
        if not name:
            raise ScoutError("请输入召唤师名，例如 Faker#KR1 或 Hide on bush")
        if tag:
            return self._resolve_exact(name, tag, platform)

        # 1) 本地索引模糊匹配（同名不同 Tag 时取最常用的）
        cands = [p for p in self.storage.all_players() if p["platform"] == platform
                 and p["riot_id"].split("#", 1)[0].lower() == name.lower()]
        cands.sort(key=lambda p: (p.get("favorite", 0), p.get("hits", 0), p.get("seen", 0)), reverse=True)
        tried = set()
        for c in cands[:3]:
            t = c["riot_id"].split("#", 1)[1]
            tried.add(t.lower())
            try:
                return self._resolve_exact(name, t, platform)
            except ScoutError:
                continue
        # 2) 区服默认 Tag
        for t in PLATFORM_DEFAULT_TAGS.get(platform, []):
            if t.lower() in tried:
                continue
            try:
                return self._resolve_exact(name, t, platform)
            except ScoutError:
                continue
        raise ScoutError(f"没找到「{name}」，请补全 #Tag（例如 {name}#{PLATFORM_DEFAULT_TAGS.get(platform, ['TAG'])[0]}）")

    def _resolve_exact(self, name: str, tag: str, platform: str) -> Profile:
        errors: List[str] = []
        prof: Optional[Profile] = None
        if self.has_key:
            try:
                acc = self.riot.account_by_riot_id(platform, name, tag)
                real = self.riot.lol_region_of(platform, acc["puuid"])
                if real and real != platform:
                    platform = real  # 自动纠正区服
                prof = Profile(acc.get("gameName", name), acc.get("tagLine", tag), platform, acc["puuid"], source="riot")
            except NotFound:
                raise ScoutError(f"玩家 {name}#{tag} 不存在")
            except RiotAPIError as e:
                errors.append(f"Riot: {e}")
        if prof is None and self.lcu_same_region(platform):
            try:
                s = self.lcu.summoner_by_riot_id(name, tag)
                if s.get("puuid"):
                    prof = Profile(s.get("gameName") or name, s.get("tagLine") or tag, platform, s["puuid"],
                                   level=int(s.get("summonerLevel") or 0), source="lcu")
            except LCUError as e:
                errors.append(f"LCU: {e}")
        if prof is None and self.opgg_on:
            try:
                s = self.opgg.profile(platform, name, tag)
                prof = Profile(s.get("game_name") or name, s.get("tagline") or tag, platform,
                               s.get("puuid") or "", source="opgg")
                self._apply_opgg_profile(prof, s)
            except OPGGError as e:
                errors.append(f"OP.GG: {e}")
        if prof is None:
            raise ScoutError("；".join(errors) or f"没有找到 {name}#{tag}")
        self.storage.touch_player(prof.riot_id, prof.platform, prof.puuid or None, searched=True)
        return prof

    # ============================================================ profile+
    def enrich_profile(self, prof: Profile) -> Profile:
        """补充等级、段位、常用英雄（并发多源，任意失败不影响其它）"""
        jobs = {}
        if self.has_key and prof.puuid:
            jobs["summoner"] = self.pool.submit(self.riot.summoner, prof.platform, prof.puuid)
            jobs["league"] = self.pool.submit(self.riot.league_entries, prof.platform, prof.puuid)
            jobs["mastery"] = self.pool.submit(self.riot.top_mastery, prof.platform, prof.puuid, 5)
        if self.opgg_on and prof.source != "opgg":
            jobs["opgg"] = self.pool.submit(self.opgg.profile, prof.platform, prof.game_name, prof.tag_line)
        if self.lcu_same_region(prof.platform) and prof.puuid and not self.has_key:
            jobs["lcu_rank"] = self.pool.submit(self.lcu.ranked_stats, prof.puuid)
            jobs["lcu_summ"] = self.pool.submit(self.lcu.summoner_by_puuid, prof.puuid)
        res: Dict[str, Any] = {}
        for k, f in jobs.items():
            try:
                res[k] = f.result(timeout=30)
            except Exception:
                res[k] = None
        if res.get("opgg"):
            self._apply_opgg_profile(prof, res["opgg"])
        if res.get("summoner"):
            prof.level = int(res["summoner"].get("summonerLevel") or prof.level)
            prof.icon_url = self.dd.image_url("profileicon", res["summoner"].get("profileIconId")) or prof.icon_url
        if res.get("lcu_summ"):
            prof.level = prof.level or int(res["lcu_summ"].get("summonerLevel") or 0)
            prof.icon_url = prof.icon_url or (self.dd.image_url("profileicon", res["lcu_summ"].get("profileIconId")) or "")
        if res.get("league"):
            qmap = {"RANKED_SOLO_5x5": "SOLORANKED", "RANKED_FLEX_SR": "FLEXRANKED"}
            prof.ranks = [{
                "queue": qmap.get(e.get("queueType"), e.get("queueType")), "tier": e.get("tier"),
                "division": e.get("rank"), "lp": e.get("leaguePoints"),
                "win": e.get("wins", 0), "lose": e.get("losses", 0),
                "winrate": round(e.get("wins", 0) * 100 / max(1, e.get("wins", 0) + e.get("losses", 0))),
            } for e in res["league"] if e.get("queueType") in qmap]
        elif res.get("lcu_rank") and not prof.ranks:
            prof.ranks = self._lcu_ranks(res["lcu_rank"])
        if res.get("mastery") and not prof.top_champs:
            prof.top_champs = [{"champion_id": m.get("championId"), "points": m.get("championPoints"),
                                "level": m.get("championLevel")} for m in res["mastery"]]
        return prof

    @staticmethod
    def _lcu_ranks(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        out = []
        qmap = {"RANKED_SOLO_5x5": "SOLORANKED", "RANKED_FLEX_SR": "FLEXRANKED"}
        for q in data.get("queues") or []:
            if q.get("queueType") in qmap and q.get("tier") and q.get("tier") not in ("NONE", ""):
                w, l = q.get("wins", 0), q.get("losses", 0)
                out.append({"queue": qmap[q["queueType"]], "tier": q["tier"], "division": q.get("division"),
                            "lp": q.get("leaguePoints"), "win": w, "lose": l,
                            "winrate": round(w * 100 / max(1, w + l))})
        return out

    def _apply_opgg_profile(self, prof: Profile, s: Dict[str, Any]) -> None:
        prof.level = prof.level or int(s.get("level") or 0)
        prof.icon_url = prof.icon_url or s.get("profile_image_url") or ""
        prof.puuid = prof.puuid or s.get("puuid") or ""
        if not prof.ranks:
            ranks = []
            for st in s.get("league_stats") or []:
                ti = st.get("tier_info") or {}
                if ti.get("tier") and st.get("game_type") in ("SOLORANKED", "FLEXRANKED"):
                    w, l = st.get("win") or 0, st.get("lose") or 0
                    ranks.append({"queue": st["game_type"], "tier": ti["tier"], "division": ti.get("division"),
                                  "lp": ti.get("lp"), "win": w, "lose": l, "winrate": round(w * 100 / max(1, w + l))})
            prof.ranks = ranks
        mc = ((s.get("most_champions") or {}).get("champion_stats") or [])[:6]
        if mc:
            prof.top_champs = [{"champion_id": c.get("id"), "play": c.get("play"), "win": c.get("win"),
                                "kda": round(((c.get("kill") or 0) + (c.get("assist") or 0)) / max(1, c.get("death") or 0), 2),
                                "name": c.get("champion_name")} for c in mc]
        player = s.get("player") or {}
        if player.get("nickname"):
            team = (((player.get("current_pro_team") or {}).get("pro_team")) or {}).get("short_name") or ""
            prof.note = f"职业选手 {team} {player['nickname']}".replace("  ", " ")

    # =============================================================== matches
    def match_source(self, prof: Profile) -> str:
        if self.has_key and prof.puuid:
            return "riot"
        if self.lcu_same_region(prof.platform) and prof.puuid:
            return "lcu"
        if self.opgg_on:
            return "opgg"
        raise ScoutError("没有可用的数据源：请配置 Riot API Key，或启动同区服客户端，或开启 OP.GG")

    def load_matches(self, prof: Profile, count: int,
                     on_match: Callable[[models.Match, int, int], None]) -> str:
        """流式加载战绩，每解析一场回调一次。返回实际使用的数据源"""
        source = self.match_source(prof)
        seen_rows: List[Tuple[str, str, Optional[str]]] = []

        def emit(m: models.Match, done: int, total: int) -> None:
            for p in m.participants:
                if p.tag_line and p.puuid != prof.puuid:
                    seen_rows.append((p.riot_id, prof.platform, p.puuid or None))
            on_match(m, done, total)

        if source == "riot":
            ids = self.riot.match_ids(prof.platform, prof.puuid, count)

            def on_item(mid: str, detail: Optional[Dict[str, Any]], done: int, total: int) -> None:
                if detail:
                    emit(models.from_riot(detail, prof.platform, prof.puuid, self.dd), done, total)
            self.riot.matches_stream(prof.platform, ids, on_item)
        elif source == "lcu":
            games = self.lcu.match_history(prof.puuid, count)
            total = len(games)
            # 列表里只有本人数据，并发补全 10 人详情
            futs = {self.pool.submit(self._lcu_full, g): g for g in games}
            for i, f in enumerate(as_completed(futs), 1):
                emit(models.from_lcu(f.result(), prof.platform, prof.puuid, self.dd), i, total)
        else:
            games = self.opgg.matches(prof.platform, prof.game_name, prof.tag_line, min(20, count))
            for i, g in enumerate(games, 1):
                emit(models.from_opgg(g, prof.platform, prof.game_name, self.dd), i, len(games))
        try:
            self.storage.touch_players_bulk(seen_rows)
        except Exception:
            pass
        return source

    def _lcu_full(self, game: Dict[str, Any]) -> Dict[str, Any]:
        try:
            full = self.lcu.game_detail(int(game.get("gameId")))
            if full.get("participants"):
                return full
        except (LCUError, TypeError, ValueError):
            pass
        return game

    def complete_match(self, m: models.Match) -> models.Match:
        """OP.GG 战绩列表只含本人，查看详情时补全全场"""
        if m.full:
            return m
        if m.source == "opgg" and m.extra.get("created_at"):
            try:
                detail = self.opgg.game_detail(m.platform, m.match_id, m.extra["created_at"])
                models.from_opgg_detail(detail, m, self.dd)
                rows = [(p.riot_id, m.platform, p.puuid or None) for p in m.participants if p.tag_line]
                self.storage.touch_players_bulk(rows)
            except OPGGError:
                pass
        elif m.source == "lcu" and m.extra.get("game_id"):
            try:
                full = self.lcu.game_detail(int(m.extra["game_id"]))
                nm = models.from_lcu(full, m.platform, m.me_puuid, self.dd)
                m.participants, m.full = nm.participants, True
            except LCUError:
                pass
        return m

    # ============================================================ live game
    def live_game(self, prof: Profile) -> Optional[models.LiveGame]:
        """返回进行中的对局（None 表示不在游戏中）"""
        errors = []
        if self.has_key and prof.puuid:
            try:
                return models.live_from_riot(self.riot.active_game(prof.platform, prof.puuid))
            except NotFound:
                return None
            except RiotAPIError as e:
                errors.append(str(e))
        me = self.lcu.me or {}
        if self.lcu.connected and me.get("puuid") and me.get("puuid") == prof.puuid:
            return self.my_live_game()
        if errors:
            raise ScoutError("；".join(errors))
        raise ScoutError("未配置 Riot API Key，无法查询他人实时对局。")

    def my_live_game(self) -> Optional[models.LiveGame]:
        """客户端本人：选人阶段 / 游戏中"""
        if not self.lcu.connected:
            return None
        phase = self.lcu.gameflow_phase()
        try:
            if phase == "ChampSelect":
                return models.live_from_champ_select(self.lcu.champ_select(), self.lcu_platform)
            if phase in ("InProgress", "GameStart", "Reconnect"):
                return models.live_from_lcu_session(self.lcu.gameflow_session(), self.lcu_platform)
        except LCUError:
            return None
        return None

    def enrich_live(self, game: models.LiveGame,
                    on_player: Callable[[models.LivePlayer], None]) -> None:
        """并发为实时对局 10 名玩家补充段位/常用英雄"""
        def work(p: models.LivePlayer) -> models.LivePlayer:
            if p.bot:
                return p
            # 选人阶段隐藏名字时，通过 LCU 用 puuid 反查
            if not p.game_name and p.puuid and self.lcu.connected:
                try:
                    s = self.lcu.summoner_by_puuid(p.puuid)
                    p.game_name, p.tag_line = s.get("gameName", ""), s.get("tagLine", "")
                except LCUError:
                    pass
            if self.opgg_on and p.game_name and p.tag_line:
                try:
                    s = self.opgg.profile(game.platform, p.game_name, p.tag_line, light=True)
                    p.rank = OPGGClient.solo_rank(s)
                    p.top_champs = ((s.get("most_champions") or {}).get("champion_stats") or [])[:3]
                    nick = (s.get("player") or {}).get("nickname")
                    if nick:
                        p.note = f"职业选手 {nick}"
                    return p
                except OPGGError:
                    pass
            if p.puuid and self.lcu_same_region(game.platform):
                try:
                    ranks = self._lcu_ranks(self.lcu.ranked_stats(p.puuid))
                    p.rank = ranks[0] if ranks else {}
                except LCUError:
                    pass
            elif p.puuid and self.has_key:
                try:
                    entries = self.riot.league_entries(game.platform, p.puuid)
                    for e in entries:
                        if e.get("queueType") == "RANKED_SOLO_5x5":
                            w, l = e.get("wins", 0), e.get("losses", 0)
                            p.rank = {"tier": e["tier"], "division": e.get("rank"), "lp": e.get("leaguePoints"),
                                      "win": w, "lose": l, "winrate": round(w * 100 / max(1, w + l))}
                except RiotAPIError:
                    pass
            return p

        futs = [self.pool.submit(work, p) for p in game.players]
        rows = []
        for f in as_completed(futs):
            try:
                p = f.result()
            except Exception:
                continue
            if p.tag_line:
                rows.append((p.riot_id, game.platform, p.puuid or None))
            on_player(p)
        self.storage.touch_players_bulk(rows)

    # =============================================================== spectate
    def spectate(self, prof: Profile, game: Optional[models.LiveGame]) -> str:
        """尽力观战：优先客户端内观战，其次直接拉起游戏进程"""
        errors = []
        if self.lcu_same_region(prof.platform) and prof.puuid:
            try:
                self.lcu.spectate(prof.game_name, prof.tag_line, prof.puuid)
                return "已通过客户端发起观战，请稍候游戏窗口启动"
            except LCUError as e:
                errors.append(str(e))
        if game and game.source == "riot":
            params = SpectateParams.from_active_game(game.raw, self.config.get("spectator_host", ""))
            if params.valid:
                try:
                    exe = launch_game(params, self.config.get("league_client_path", ""),
                                      self.config.get("locale", "zh_CN"))
                    return f"已拉起观战进程：{exe.name}（观战有约 3 分钟延迟）"
                except (OSError, ValueError) as e:
                    errors.append(str(e))
        if not errors:
            errors.append("需要：同区服客户端已登录，或配置 Riot API Key 获取观战密钥")
        raise ScoutError("；".join(errors))

    def spectate_bat(self, game: models.LiveGame) -> str:
        params = SpectateParams.from_active_game(game.raw, self.config.get("spectator_host", ""))
        if not params.valid:
            raise ScoutError("当前对局没有观战密钥（仅 Riot API 来源的对局可生成）")
        return str(write_bat(params, self.config.get("league_client_path", ""), self.config.get("locale", "zh_CN")))

    def shutdown(self) -> None:
        self.pool.shutdown(wait=False, cancel_futures=True)
        self.riot.shutdown()
