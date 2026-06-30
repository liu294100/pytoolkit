"""SQLite database service for caching and history."""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

from ..model.project import Project, Group

logger = logging.getLogger(__name__)


class DBService:
    """SQLite-based persistence for projects, groups, and search history.
    
    Uses WAL mode for better concurrent read performance.
    """

    def __init__(self, db_path: str | Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent reads
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.row_factory = sqlite3.Row

        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                full_path TEXT NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                path_with_namespace TEXT NOT NULL,
                group_name TEXT,
                default_branch TEXT DEFAULT 'master',
                web_url TEXT,
                clone_url TEXT,
                branches TEXT,
                last_synced TEXT,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                file_pattern TEXT,
                use_regex INTEGER DEFAULT 0,
                ignore_case INTEGER DEFAULT 1,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                file_pattern TEXT,
                use_regex INTEGER DEFAULT 0,
                ignore_case INTEGER DEFAULT 1,
                label TEXT,
                created_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_projects_group ON projects(group_name);
            CREATE INDEX IF NOT EXISTS idx_history_keyword ON search_history(keyword);
            CREATE INDEX IF NOT EXISTS idx_history_created ON search_history(created_at DESC);
        """)
        self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # --- Groups ---

    def save_groups(self, groups: list[Group]) -> None:
        """Bulk save groups (replace all)."""
        now = time.time()
        self._conn.execute("DELETE FROM groups")
        self._conn.executemany(
            "INSERT INTO groups (id, name, full_path, updated_at) VALUES (?, ?, ?, ?)",
            [(g.id, g.name, g.full_path, now) for g in groups],
        )
        self._conn.commit()

    def get_groups(self) -> list[Group]:
        """Load cached groups."""
        rows = self._conn.execute("SELECT id, name, full_path FROM groups ORDER BY name").fetchall()
        return [Group(id=r["id"], name=r["name"], full_path=r["full_path"]) for r in rows]

    # --- Projects ---

    def save_projects(self, projects: list[Project]) -> None:
        """Bulk save projects (replace all)."""
        now = time.time()
        self._conn.execute("DELETE FROM projects")
        self._conn.executemany(
            """INSERT INTO projects 
               (id, name, path_with_namespace, group_name, default_branch, web_url, clone_url, branches, last_synced, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (p.id, p.name, p.path_with_namespace, p.group, p.default_branch,
                 p.web_url, p.clone_url, json.dumps(p.branches), p.last_synced, now)
                for p in projects
            ],
        )
        self._conn.commit()

    def get_projects(self, group: Optional[str] = None) -> list[Project]:
        """Load cached projects, optionally filtered by group."""
        if group:
            rows = self._conn.execute(
                "SELECT * FROM projects WHERE group_name = ? ORDER BY name", (group,)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM projects ORDER BY name").fetchall()

        projects = []
        for r in rows:
            p = Project(
                id=r["id"],
                name=r["name"],
                path_with_namespace=r["path_with_namespace"],
                group=r["group_name"] or "",
                default_branch=r["default_branch"] or "master",
                web_url=r["web_url"] or "",
                clone_url=r["clone_url"] or "",
                branches=json.loads(r["branches"]) if r["branches"] else [],
                last_synced=r["last_synced"],
            )
            projects.append(p)
        return projects

    def update_project_branches(self, project_id: int, branches: list[str]) -> None:
        """Update branches for a specific project."""
        self._conn.execute(
            "UPDATE projects SET branches = ?, updated_at = ? WHERE id = ?",
            (json.dumps(branches), time.time(), project_id),
        )
        self._conn.commit()

    def update_project_synced(self, project_id: int, synced_time: str) -> None:
        """Mark project as synced."""
        self._conn.execute(
            "UPDATE projects SET last_synced = ?, updated_at = ? WHERE id = ?",
            (synced_time, time.time(), project_id),
        )
        self._conn.commit()

    # --- Search History ---

    def add_history(self, keyword: str, file_pattern: str = "", use_regex: bool = False, ignore_case: bool = True) -> None:
        """Add search to history."""
        self._conn.execute(
            "INSERT INTO search_history (keyword, file_pattern, use_regex, ignore_case, created_at) VALUES (?, ?, ?, ?, ?)",
            (keyword, file_pattern, int(use_regex), int(ignore_case), time.time()),
        )
        self._conn.commit()
        # Keep only last 100
        self._conn.execute(
            "DELETE FROM search_history WHERE id NOT IN (SELECT id FROM search_history ORDER BY created_at DESC LIMIT 100)"
        )
        self._conn.commit()

    def get_history(self, limit: int = 20) -> list[dict]:
        """Get recent search history."""
        rows = self._conn.execute(
            "SELECT keyword, file_pattern, use_regex, ignore_case, created_at FROM search_history ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Favorites ---

    def add_favorite(self, keyword: str, file_pattern: str = "", use_regex: bool = False,
                     ignore_case: bool = True, label: str = "") -> None:
        """Save a search as favorite."""
        self._conn.execute(
            "INSERT INTO favorites (keyword, file_pattern, use_regex, ignore_case, label, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (keyword, file_pattern, int(use_regex), int(ignore_case), label, time.time()),
        )
        self._conn.commit()

    def get_favorites(self) -> list[dict]:
        """Get all favorites."""
        rows = self._conn.execute(
            "SELECT id, keyword, file_pattern, use_regex, ignore_case, label FROM favorites ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def remove_favorite(self, fav_id: int) -> None:
        """Remove a favorite by ID."""
        self._conn.execute("DELETE FROM favorites WHERE id = ?", (fav_id,))
        self._conn.commit()

    # --- Utility ---

    def has_cached_data(self) -> bool:
        """Check if we have cached projects."""
        row = self._conn.execute("SELECT COUNT(*) as cnt FROM projects").fetchone()
        return row["cnt"] > 0
