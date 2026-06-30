"""Application configuration model."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class AppConfig:
    """Application configuration loaded from config.json."""

    gitlab_url: str = ""
    token: str = ""
    proxy: str = ""
    proxy_enabled: bool = False
    clone_folder: str = "./cache"
    thread_count: int = 8
    search_timeout: int = 30
    theme: str = "dark"
    max_results_per_project: int = 500
    context_lines: int = 10
    auto_sync_interval_minutes: int = 30
    rg_path: str = "rg"

    # Runtime paths (not serialized)
    _config_path: str = field(default="", repr=False)

    @classmethod
    def load(cls, path: str | Path | None = None) -> AppConfig:
        """Load config from JSON file. Creates default if not exists."""
        if path is None:
            path = Path(os.path.dirname(os.path.abspath(__file__))) / "../../config.json"
        path = Path(path).resolve()

        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            config = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__ and not k.startswith("_")})
        else:
            config = cls()

        config._config_path = str(path)
        return config

    def save(self) -> None:
        """Persist config to JSON file."""
        path = Path(self._config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v for k, v in asdict(self).items() if not k.startswith("_")}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @property
    def cache_dir(self) -> Path:
        """Resolved cache directory path."""
        base = Path(self._config_path).parent if self._config_path else Path(".")
        return (base / self.clone_folder).resolve()

    @property
    def db_path(self) -> Path:
        """Database file path."""
        base = Path(self._config_path).parent if self._config_path else Path(".")
        return (base / "data" / "database.db").resolve()
