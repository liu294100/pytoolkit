"""统一数据模型：把 Riot Match-V5 / LCU 战绩 / OP.GG 战绩 / 实时对局 归一成同一结构，
UI 只和这里的 dataclass 打交道，不关心数据来源。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import QUEUE_NAMES, kda_ratio

OPGG_GAME_TYPES = {
    "SOLORANKED": (420, "单双排"), "FLEXRANKED": (440, "灵活排位"), "NORMAL": (400, "匹配模式"),
    "QUICKPLAY": (490, "快速匹配"), "ARAM": (450, "大乱斗"), "ARENA": (1700, "斗魂竞技场"),
    "URF": (900, "无限火力"), "BOT": (870, "人机"), "CLASH": (700, "冠军杯"),
    "NEXUS_BLITZ": (1300, "极限闪击"), "ULTBOOK": (1400, "终极魔典"), "SWIFTPLAY": (480, "快速匹配"),
}


@dataclass
class Participant:
    puuid: str = ""
    game_name: str = ""
    tag_line: str = ""
    champ_key: int = 0
    champ_id: str = ""          # Data Dragon id，例如 MonkeyKing
    champ_name: str = ""
    team: int = 100
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    cs: int = 0
    gold: int = 0
    damage: int = 0
    taken: int = 0
    vision: int = 0
    level: int = 0
    items: List[int] = field(default_factory=list)
    spells: List[int] = field(default_factory=list)
    position: str = ""
    win: bool = False
    op_score: Optional[float] = None
    op_rank: Optional[int] = None

    @property
    def riot_id(self) -> str:
        return f"{self.game_name}#{self.tag_line}" if self.tag_line else self.game_name

    @property
    def kda(self) -> float:
        return kda_ratio(self.kills, self.deaths, self.assists)

    @property
    def kda_text(self) -> str:
        return f"{self.kills}/{self.deaths}/{self.assists}"


@dataclass
class Match:
    match_id: str
    platform: str
    source: str                     # riot / lcu / opgg
    queue_id: int = 0
    queue_name: str = ""
    start_ts: int = 0               # 毫秒
    duration: int = 0               # 秒
    participants: List[Participant] = field(default_factory=list)
    me_puuid: str = ""
    me_name: str = ""
    remake: bool = False
    full: bool = True               # participants 是否包含全部 10 人
    avg_tier: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def me(self) -> Participant:
        for p in self.participants:
            if self.me_puuid and p.puuid == self.me_puuid:
                return p
        for p in self.participants:
            if self.me_name and p.game_name.lower() == self.me_name.lower():
                return p
        return self.participants[0] if self.participants else Participant()

    @property
    def date_text(self) -> str:
        if not self.start_ts:
            return ""
        return datetime.fromtimestamp(self.start_ts / 1000).strftime("%m-%d %H:%M")

    def team(self, team_id: int) -> List[Participant]:
        return [p for p in self.participants if p.team == team_id]

    def team_kills(self, team_id: int) -> int:
        return sum(p.kills for p in self.team(team_id))

    def kill_participation(self, p: Participant) -> int:
        total = self.team_kills(p.team)
        return round((p.kills + p.assists) * 100 / total) if total else 0

    def search_text(self) -> List[str]:
        """供模糊筛选使用的文本"""
        me = self.me
        texts = [me.champ_name, me.champ_id, self.queue_name, me.position]
        texts += [p.game_name for p in self.participants if p.game_name]
        texts += [p.champ_name for p in self.participants if p.champ_name]
        return [t for t in texts if t]


# ============================================================================
# Riot Match-V5
# ============================================================================

def _items(d: Dict[str, Any]) -> List[int]:
    return [int(d.get(f"item{i}", 0) or 0) for i in range(7)]


def from_riot(detail: Dict[str, Any], platform: str, me_puuid: str, dd) -> Match:
    info = detail.get("info") or {}
    meta = detail.get("metadata") or {}
    queue_id = int(info.get("queueId") or 0)
    duration = int(info.get("gameDuration") or 0)
    if not info.get("gameEndTimestamp") and duration > 100000:  # 旧版本为毫秒
        duration //= 1000
    parts: List[Participant] = []
    remake = False
    for p in info.get("participants") or []:
        champ = dd.champ(p.get("championId"), p.get("championName", ""))
        remake = remake or bool(p.get("gameEndedInEarlySurrender"))
        parts.append(Participant(
            puuid=p.get("puuid", ""),
            game_name=p.get("riotIdGameName") or p.get("summonerName") or "",
            tag_line=p.get("riotIdTagline") or "",
            champ_key=int(p.get("championId") or 0),
            champ_id=champ.get("id") or p.get("championName", ""),
            champ_name=champ.get("name") or p.get("championName", ""),
            team=int(p.get("teamId") or 100),
            kills=int(p.get("kills") or 0), deaths=int(p.get("deaths") or 0),
            assists=int(p.get("assists") or 0),
            cs=int(p.get("totalMinionsKilled") or 0) + int(p.get("neutralMinionsKilled") or 0),
            gold=int(p.get("goldEarned") or 0),
            damage=int(p.get("totalDamageDealtToChampions") or 0),
            taken=int(p.get("totalDamageTaken") or 0),
            vision=int(p.get("visionScore") or 0),
            level=int(p.get("champLevel") or 0),
            items=_items(p),
            spells=[int(p.get("summoner1Id") or 0), int(p.get("summoner2Id") or 0)],
            position=p.get("teamPosition") or p.get("individualPosition") or "",
            win=bool(p.get("win")),
        ))
    return Match(
        match_id=meta.get("matchId") or f"{info.get('platformId')}_{info.get('gameId')}",
        platform=platform, source="riot", queue_id=queue_id,
        queue_name=QUEUE_NAMES.get(queue_id, info.get("gameMode") or str(queue_id)),
        start_ts=int(info.get("gameStartTimestamp") or info.get("gameCreation") or 0),
        duration=duration, participants=parts, me_puuid=me_puuid, remake=remake,
    )


# ============================================================================
# LCU 战绩（腾讯服 / 任意区服客户端均可用）
# ============================================================================

def from_lcu(game: Dict[str, Any], platform: str, me_puuid: str, dd) -> Match:
    identities = {i.get("participantId"): (i.get("player") or {}) for i in game.get("participantIdentities") or []}
    parts: List[Participant] = []
    for p in game.get("participants") or []:
        s = p.get("stats") or {}
        player = identities.get(p.get("participantId"), {})
        champ = dd.champ(p.get("championId"))
        tl = p.get("timeline") or {}
        lane = tl.get("lane") or ""
        if tl.get("role") == "DUO_SUPPORT":
            lane = "UTILITY"
        parts.append(Participant(
            puuid=player.get("puuid", ""),
            game_name=player.get("gameName") or player.get("summonerName") or "",
            tag_line=player.get("tagLine") or "",
            champ_key=int(p.get("championId") or 0),
            champ_id=champ.get("id", ""), champ_name=champ.get("name", ""),
            team=int(p.get("teamId") or 100),
            kills=int(s.get("kills") or 0), deaths=int(s.get("deaths") or 0), assists=int(s.get("assists") or 0),
            cs=int(s.get("totalMinionsKilled") or 0) + int(s.get("neutralMinionsKilled") or 0),
            gold=int(s.get("goldEarned") or 0),
            damage=int(s.get("totalDamageDealtToChampions") or 0),
            taken=int(s.get("totalDamageTaken") or 0),
            vision=int(s.get("visionScore") or 0),
            level=int(s.get("champLevel") or 0),
            items=_items(s),
            spells=[int(p.get("spell1Id") or 0), int(p.get("spell2Id") or 0)],
            position="" if lane in ("NONE", "") else lane,
            win=bool(s.get("win")),
        ))
    queue_id = int(game.get("queueId") or 0)
    return Match(
        match_id=f"{game.get('platformId') or platform}_{game.get('gameId')}",
        platform=platform, source="lcu", queue_id=queue_id,
        queue_name=QUEUE_NAMES.get(queue_id, game.get("gameMode") or str(queue_id)),
        start_ts=int(game.get("gameCreation") or 0),
        duration=int(game.get("gameDuration") or 0),
        participants=parts, me_puuid=me_puuid,
        full=len(parts) >= 10 or len(parts) == len(identities) > 1,
        extra={"game_id": game.get("gameId")},
    )


# ============================================================================
# OP.GG
# ============================================================================

def _iso_to_ms(text: str) -> int:
    try:
        return int(datetime.fromisoformat(text).timestamp() * 1000)
    except (TypeError, ValueError):
        return 0


def _opgg_participant(p: Dict[str, Any], dd) -> Participant:
    s = p.get("stats") or {}
    summ = p.get("summoner") or {}
    champ = dd.champ(p.get("champion_id"))
    items = [int(i or 0) for i in (p.get("items") or []) if isinstance(i, (int, float))]
    return Participant(
        puuid=summ.get("puuid") or "",
        game_name=summ.get("game_name") or "", tag_line=summ.get("tagline") or "",
        champ_key=int(p.get("champion_id") or 0),
        champ_id=champ.get("id", ""), champ_name=champ.get("name") or p.get("champion_name", ""),
        team=200 if p.get("team_key") == "RED" else 100,
        kills=int(s.get("kill") or 0), deaths=int(s.get("death") or 0), assists=int(s.get("assist") or 0),
        cs=int(s.get("minion_kill") or 0) + int(s.get("neutral_minion_kill") or 0),
        gold=int(s.get("gold_earned") or 0),
        damage=int(s.get("total_damage_dealt_to_champions") or 0),
        taken=int(s.get("total_damage_taken") or 0),
        vision=int(s.get("ward_place") or 0),
        level=int(s.get("champion_level") or 0),
        items=items, spells=[int(x or 0) for x in (p.get("spells") or [])],
        position=p.get("position") or "",
        win=s.get("result") == "WIN",
        op_score=s.get("op_score"), op_rank=s.get("op_score_rank"),
    )


def _avg_tier(info: Optional[Dict[str, Any]]) -> str:
    if not info or not info.get("tier"):
        return ""
    return f"{info['tier']} {info.get('division') or ''}".strip()


def from_opgg(game: Dict[str, Any], platform: str, me_name: str, dd) -> Match:
    gtype = game.get("game_type") or ""
    queue_id, qname = OPGG_GAME_TYPES.get(gtype, (0, gtype))
    parts = [_opgg_participant(p, dd) for p in game.get("participants") or []]
    remake = any((p.get("stats") or {}).get("result") == "UNKNOWN" for p in game.get("participants") or [])
    return Match(
        match_id=str(game.get("id")), platform=platform, source="opgg",
        queue_id=queue_id, queue_name=qname,
        start_ts=_iso_to_ms(game.get("created_at", "")),
        duration=int(game.get("game_length_second") or 0),
        participants=parts, me_name=me_name, remake=remake,
        full=len(parts) >= 10, avg_tier=_avg_tier(game.get("average_tier_info")),
        extra={"created_at": game.get("created_at")},
    )


def from_opgg_detail(detail: Dict[str, Any], base: Match, dd) -> Match:
    parts: List[Participant] = []
    for team in detail.get("teams") or []:
        for p in team.get("participants") or []:
            parts.append(_opgg_participant(p, dd))
    if parts:
        base.participants = parts
        base.full = True
    return base


# ============================================================================
# 实时对局
# ============================================================================

@dataclass
class LivePlayer:
    puuid: str = ""
    game_name: str = ""
    tag_line: str = ""
    champ_key: int = 0
    team: int = 100
    spells: List[int] = field(default_factory=list)
    position: str = ""
    bot: bool = False
    rank: Dict[str, Any] = field(default_factory=dict)       # OP.GG / LCU 段位摘要
    top_champs: List[Dict[str, Any]] = field(default_factory=list)
    note: str = ""                                            # 职业选手等

    @property
    def riot_id(self) -> str:
        return f"{self.game_name}#{self.tag_line}" if self.tag_line else self.game_name


@dataclass
class LiveGame:
    source: str                 # riot / lcu-ingame / lcu-champselect
    platform: str
    game_id: str = ""
    queue_id: int = 0
    queue_name: str = ""
    length: int = 0             # 秒
    start_ts: int = 0
    players: List[LivePlayer] = field(default_factory=list)
    bans: List[int] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    def team(self, team_id: int) -> List[LivePlayer]:
        return [p for p in self.players if p.team == team_id]

    @property
    def elapsed(self) -> int:
        if self.start_ts:
            return max(0, int(datetime.now().timestamp() - self.start_ts / 1000))
        return self.length


def live_from_riot(game: Dict[str, Any]) -> LiveGame:
    players = []
    for p in game.get("participants") or []:
        name, _, tag = (p.get("riotId") or p.get("summonerName") or "").partition("#")
        players.append(LivePlayer(
            puuid=p.get("puuid") or "", game_name=name, tag_line=tag,
            champ_key=int(p.get("championId") or 0), team=int(p.get("teamId") or 100),
            spells=[int(p.get("spell1Id") or 0), int(p.get("spell2Id") or 0)], bot=bool(p.get("bot")),
        ))
    qid = int(game.get("gameQueueConfigId") or 0)
    return LiveGame(
        source="riot", platform=str(game.get("platformId") or "").upper(),
        game_id=str(game.get("gameId") or ""), queue_id=qid,
        queue_name=QUEUE_NAMES.get(qid, game.get("gameMode") or ""),
        length=int(game.get("gameLength") or 0), start_ts=int(game.get("gameStartTime") or 0),
        players=players, bans=[int(b.get("championId") or 0) for b in game.get("bannedChampions") or []],
        raw=game,
    )


def _lcu_player(p: Dict[str, Any], team: int) -> LivePlayer:
    name = p.get("gameName") or p.get("summonerName") or ""
    tag = p.get("tagLine") or ""
    if not tag and "#" in name:
        name, _, tag = name.partition("#")
    return LivePlayer(
        puuid=p.get("puuid") or "", game_name=name, tag_line=tag,
        champ_key=int(p.get("championId") or 0), team=team,
        spells=[int(p.get("spell1Id") or 0), int(p.get("spell2Id") or 0)],
        position=(p.get("assignedPosition") or p.get("selectedPosition") or "").upper(),
    )


def live_from_lcu_session(session: Dict[str, Any], platform: str) -> LiveGame:
    gd = session.get("gameData") or {}
    queue = gd.get("queue") or {}
    players = [_lcu_player(p, 100) for p in gd.get("teamOne") or []] + \
              [_lcu_player(p, 200) for p in gd.get("teamTwo") or []]
    qid = int(queue.get("id") or 0)
    return LiveGame(source="lcu-ingame", platform=platform, game_id=str(gd.get("gameId") or ""),
                    queue_id=qid, queue_name=QUEUE_NAMES.get(qid, queue.get("description") or ""),
                    players=players, raw=session)


def live_from_champ_select(cs: Dict[str, Any], platform: str) -> LiveGame:
    players = [_lcu_player(p, 100) for p in cs.get("myTeam") or []] + \
              [_lcu_player(p, 200) for p in cs.get("theirTeam") or []]
    bans = [int(c) for c in ((cs.get("bans") or {}).get("myTeamBans") or []) +
            ((cs.get("bans") or {}).get("theirTeamBans") or []) if c]
    return LiveGame(source="lcu-champselect", platform=platform, game_id=str(cs.get("gameId") or ""),
                    queue_name="选人阶段", players=players, bans=bans, raw=cs)
