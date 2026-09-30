"""SQLite 持久化：API 缓存 + 本地玩家索引（用于模糊搜索）

相比 v2 每次 set 都重写整份 cache.json，这里使用 SQLite WAL + 内存 LRU：
- 对局详情不可变，永久缓存
- 其余数据按 TTL 过期
- 玩家索引记录搜索历史 / 收藏 / 对局中见过的玩家 / 客户端好友
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


class LRU:
    def __init__(self, capacity: int = 512):
        self.capacity = capacity
        self._data: "OrderedDict[str, Any]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        with self._lock:
            if key not in self._data:
                return None
            self._data.move_to_end(key)
            return self._data[key]

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value
            self._data.move_to_end(key)
            while len(self._data) > self.capacity:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class Storage:
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS kv (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        expires REAL            -- NULL = 永不过期
    );
    CREATE TABLE IF NOT EXISTS players (
        riot_id TEXT NOT NULL,          -- 名字#标签
        platform TEXT NOT NULL,
        puuid TEXT,
        source TEXT,                    -- history / favorite / seen / friend / lcu
        hits INTEGER DEFAULT 0,         -- 被主动搜索次数
        seen INTEGER DEFAULT 0,         -- 在对局中出现次数
        favorite INTEGER DEFAULT 0,
        last_used REAL DEFAULT 0,
        PRIMARY KEY (riot_id, platform)
    );
    CREATE INDEX IF NOT EXISTS idx_players_puuid ON players(puuid);
    """

    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False, isolation_level=None)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(self.SCHEMA)
        self._lock = threading.RLock()
        self._mem = LRU(1024)

    # ------------------------------------------------------------------ kv
    def get(self, key: str) -> Any:
        cached = self._mem.get(key)
        if cached is not None:
            value, expires = cached
            if expires is None or expires > time.time():
                return value
        with self._lock:
            row = self._conn.execute("SELECT value, expires FROM kv WHERE key=?", (key,)).fetchone()
        if not row:
            return None
        value_text, expires = row
        if expires is not None and expires <= time.time():
            return None
        value = json.loads(value_text)
        self._mem.set(key, (value, expires))
        return value

    def set(self, key: str, value: Any, ttl: Optional[float] = 1800) -> None:
        expires = None if ttl is None else time.time() + ttl
        self._mem.set(key, (value, expires))
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO kv(key, value, expires) VALUES (?,?,?)",
                (key, json.dumps(value, ensure_ascii=False, separators=(",", ":")), expires),
            )

    def clear_cache(self, keep_permanent: bool = False) -> None:
        self._mem.clear()
        with self._lock:
            if keep_permanent:
                self._conn.execute("DELETE FROM kv WHERE expires IS NOT NULL")
            else:
                self._conn.execute("DELETE FROM kv")
            self._conn.execute("VACUUM")

    def purge_expired(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM kv WHERE expires IS NOT NULL AND expires < ?", (time.time(),))

    # ------------------------------------------------------------- players
    def touch_player(self, riot_id: str, platform: str, puuid: Optional[str] = None,
                     source: str = "history", searched: bool = False) -> None:
        if not riot_id or "#" not in riot_id:
            return
        now = time.time()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO players(riot_id, platform, puuid, source, hits, seen, last_used)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(riot_id, platform) DO UPDATE SET
                    puuid = COALESCE(excluded.puuid, players.puuid),
                    source = CASE WHEN players.source IN ('history','favorite') THEN players.source
                                  ELSE excluded.source END,
                    hits = players.hits + excluded.hits,
                    seen = players.seen + excluded.seen,
                    last_used = CASE WHEN excluded.hits > 0 THEN excluded.last_used ELSE players.last_used END
                """,
                (riot_id, platform, puuid, source, 1 if searched else 0, 0 if searched else 1,
                 now if searched else 0),
            )

    def touch_players_bulk(self, rows: Iterable[tuple], source: str = "seen") -> None:
        """rows: (riot_id, platform, puuid)"""
        data = [(r, p, u, source) for r, p, u in rows if r and "#" in r]
        if not data:
            return
        with self._lock:
            self._conn.execute("BEGIN")
            try:
                self._conn.executemany(
                    """
                    INSERT INTO players(riot_id, platform, puuid, source, seen)
                    VALUES (?,?,?,?,1)
                    ON CONFLICT(riot_id, platform) DO UPDATE SET
                        puuid = COALESCE(excluded.puuid, players.puuid),
                        seen = players.seen + 1
                    """,
                    data,
                )
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def set_favorite(self, riot_id: str, platform: str, favorite: bool) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE players SET favorite=? WHERE riot_id=? AND platform=?",
                (1 if favorite else 0, riot_id, platform),
            )

    def is_favorite(self, riot_id: str, platform: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT favorite FROM players WHERE riot_id=? AND platform=?", (riot_id, platform)
            ).fetchone()
        return bool(row and row[0])

    def all_players(self, limit: int = 5000) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """SELECT riot_id, platform, puuid, source, hits, seen, favorite, last_used
                   FROM players ORDER BY favorite DESC, last_used DESC, seen DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        keys = ("riot_id", "platform", "puuid", "source", "hits", "seen", "favorite", "last_used")
        return [dict(zip(keys, r)) for r in rows]

    def recent_players(self, limit: int = 15) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """SELECT riot_id, platform, puuid, favorite FROM players
                   WHERE hits > 0 OR favorite = 1
                   ORDER BY favorite DESC, last_used DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(zip(("riot_id", "platform", "puuid", "favorite"), r)) for r in rows]

    def clear_history(self) -> None:
        with self._lock:
            self._conn.execute("UPDATE players SET hits=0, last_used=0 WHERE favorite=0")

    def import_legacy_history(self, path: Path) -> None:
        """导入 v2 的 search_history.json"""
        if not path.exists() or self.get("meta:legacy_imported"):
            return
        try:
            entries = json.loads(path.read_text(encoding="utf-8")).get("entries", [])
            for e in entries:
                self.touch_player(e.get("riot_id", ""), e.get("platform", ""), e.get("puuid"), searched=True)
        except (OSError, json.JSONDecodeError, AttributeError):
            pass
        self.set("meta:legacy_imported", True, ttl=None)
