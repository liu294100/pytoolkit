"""Data Dragon 静态数据（英雄中文名、图标）+ 磁盘/内存图片缓存"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from .config import DEFAULT_TIMEOUT, IMG_CACHE_DIR
from .storage import LRU, Storage

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

DD = "https://ddragon.leagueoflegends.com"


class DataDragon:
    def __init__(self, storage: Storage, locale: str = "zh_CN"):
        self.storage = storage
        self.locale = locale
        self.session = requests.Session()
        self.version: str = ""
        self.champions: Dict[int, Dict[str, str]] = {}      # key(int) -> {id, name, title}
        self.champ_by_id: Dict[str, Dict[str, str]] = {}    # "MonkeyKing" -> {...}
        self.spells: Dict[int, str] = {}                    # key -> "SummonerFlash"
        self.ready = threading.Event()
        self._img_mem = LRU(600)
        self._img_locks: Dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()
        IMG_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- load
    def load(self) -> None:
        """在后台线程调用；失败时使用缓存的旧版本数据"""
        try:
            self._load()
        except Exception:
            cached = self.storage.get(f"dd:bundle:{self.locale}:last")
            if cached:
                self._apply(cached)
        finally:
            self.ready.set()

    def _load(self) -> None:
        version = self.storage.get("dd:version")
        if not version:
            versions = self.session.get(f"{DD}/api/versions.json", timeout=DEFAULT_TIMEOUT).json()
            version = versions[0]
            self.storage.set("dd:version", version, ttl=6 * 3600)
        bundle_key = f"dd:bundle:{self.locale}:{version}"
        bundle = self.storage.get(bundle_key)
        if not bundle:
            champs = self.session.get(f"{DD}/cdn/{version}/data/{self.locale}/champion.json",
                                      timeout=DEFAULT_TIMEOUT).json()["data"]
            spells = self.session.get(f"{DD}/cdn/{version}/data/{self.locale}/summoner.json",
                                      timeout=DEFAULT_TIMEOUT).json()["data"]
            bundle = {
                "version": version,
                "champions": {c["key"]: {"id": c["id"], "name": c["name"], "title": c["title"]}
                              for c in champs.values()},
                "spells": {s["key"]: s["id"] for s in spells.values()},
            }
            self.storage.set(bundle_key, bundle, ttl=None)
            self.storage.set(f"dd:bundle:{self.locale}:last", bundle, ttl=None)
        self._apply(bundle)

    def _apply(self, bundle: Dict[str, Any]) -> None:
        self.version = bundle["version"]
        self.champions = {int(k): v for k, v in bundle["champions"].items()}
        self.champ_by_id = {v["id"].lower(): v for v in self.champions.values()}
        self.spells = {int(k): v for k, v in bundle["spells"].items()}

    # ------------------------------------------------------------- lookups
    def champ(self, key: Any = None, champ_id: str = "") -> Dict[str, str]:
        if key not in (None, "", 0, -1):
            try:
                c = self.champions.get(int(key))
                if c:
                    return c
            except (TypeError, ValueError):
                pass
        if champ_id:
            c = self.champ_by_id.get(champ_id.lower())
            if c:
                return c
            return {"id": champ_id, "name": champ_id, "title": ""}
        return {"id": "", "name": str(key or "?"), "title": ""}

    def champ_name(self, key: Any = None, champ_id: str = "") -> str:
        return self.champ(key, champ_id)["name"]

    def champion_search_keys(self, champ_id: str) -> List[str]:
        c = self.champ_by_id.get((champ_id or "").lower())
        if not c:
            return [champ_id]
        return [c["name"], c["id"], c["title"]]

    # --------------------------------------------------------------- images
    def image_url(self, kind: str, ident: Any) -> Optional[str]:
        if not self.version or ident in (None, "", 0):
            return None
        if kind == "champion":
            c = self.champ(ident) if isinstance(ident, int) or str(ident).isdigit() else self.champ(champ_id=str(ident))
            return f"{DD}/cdn/{self.version}/img/champion/{c['id']}.png" if c.get("id") else None
        if kind == "item":
            return f"{DD}/cdn/{self.version}/img/item/{ident}.png"
        if kind == "spell":
            sid = self.spells.get(int(ident)) if str(ident).isdigit() else str(ident)
            return f"{DD}/cdn/{self.version}/img/spell/{sid}.png" if sid else None
        if kind == "profileicon":
            return f"{DD}/cdn/{self.version}/img/profileicon/{ident}.png"
        return None

    def _lock_for(self, key: str) -> threading.Lock:
        with self._locks_guard:
            return self._img_locks.setdefault(key, threading.Lock())

    def load_image(self, url: Optional[str], size: Tuple[int, int]) -> Optional["Image.Image"]:
        """同步加载（请在工作线程调用）：内存 -> 磁盘 -> 网络"""
        if not url or Image is None:
            return None
        mem_key = f"{url}@{size}"
        cached = self._img_mem.get(mem_key)
        if cached is not None:
            return cached
        fname = url.split("://", 1)[-1].replace("/", "_").replace(":", "_")
        path: Path = IMG_CACHE_DIR / fname
        with self._lock_for(fname):
            if not path.exists():
                try:
                    resp = self.session.get(url, timeout=DEFAULT_TIMEOUT)
                    if resp.status_code != 200:
                        return None
                    path.write_bytes(resp.content)
                except (requests.RequestException, OSError):
                    return None
        try:
            img = Image.open(path).convert("RGBA").resize(size, Image.LANCZOS)
        except Exception:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            return None
        self._img_mem.set(mem_key, img)
        return img
