"""本地缓存管理 - 频道列表和 EPG 数据持久化"""

import json
import sys
import time
from pathlib import Path
from typing import Any

from ..models import ChannelGroup, Channel


def _get_cache_dir() -> Path:
    """获取缓存目录，支持 PyInstaller 打包"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，使用 exe 所在目录
        return Path(sys.executable).parent / "cache"
    else:
        # 开发模式
        return Path(__file__).parent.parent / "cache"


class CacheManager:
    """缓存管理器"""
    
    # 缓存目录（动态获取）
    CACHE_DIR = _get_cache_dir()
    
    # 缓存文件
    CHANNELS_FILE = "channels.json"
    EPG_FILE = "epg.json"
    SETTINGS_FILE = "settings.json"
    
    # EPG 缓存过期时间（秒）
    EPG_CACHE_TTL = 3600 * 6  # 6 小时
    
    def __init__(self):
        self.CACHE_DIR.mkdir(exist_ok=True)
    
    # ========== 频道缓存 ==========
    
    def save_channels(self, groups: list[ChannelGroup], source_info: dict | None = None):
        """保存频道列表到本地"""
        data = {
            "version": 1,
            "updated_at": time.time(),
            "source_info": source_info or {},
            "groups": [self._group_to_dict(g) for g in groups],
        }
        self._write_json(self.CHANNELS_FILE, data)
    
    def load_channels(self) -> tuple[list[ChannelGroup], dict]:
        """加载本地频道列表，返回 (groups, source_info)"""
        data = self._read_json(self.CHANNELS_FILE)
        if not data:
            return [], {}
        
        groups = [self._dict_to_group(g) for g in data.get("groups", [])]
        source_info = data.get("source_info", {})
        return groups, source_info
    
    def has_channels_cache(self) -> bool:
        """是否有频道缓存"""
        return (self.CACHE_DIR / self.CHANNELS_FILE).exists()
    
    def clear_channels_cache(self):
        """清除频道缓存"""
        cache_file = self.CACHE_DIR / self.CHANNELS_FILE
        if cache_file.exists():
            cache_file.unlink()
    
    def _group_to_dict(self, group: ChannelGroup) -> dict:
        return {
            "name": group.name,
            "tvg_id": group.tvg_id,
            "group": group.group,
            "logo": group.logo,
            "channels": [ch.to_dict() for ch in group.channels],
        }
    
    def _dict_to_group(self, data: dict) -> ChannelGroup:
        group = ChannelGroup(
            name=data.get("name", ""),
            tvg_id=data.get("tvg_id", ""),
            group=data.get("group", ""),
            logo=data.get("logo", ""),
        )
        for ch_data in data.get("channels", []):
            group.channels.append(Channel.from_dict(ch_data))
        return group
    
    # ========== EPG 缓存 ==========
    
    def save_epg(self, channel_key: str, programmes: list[dict]):
        """保存频道 EPG 数据"""
        all_epg = self._read_json(self.EPG_FILE) or {"version": 1, "channels": {}}
        
        all_epg["channels"][channel_key] = {
            "updated_at": time.time(),
            "programmes": programmes,
        }
        
        # 清理过期的 EPG 缓存
        self._cleanup_expired_epg(all_epg)
        
        self._write_json(self.EPG_FILE, all_epg)
    
    def load_epg(self, channel_key: str) -> list[dict] | None:
        """加载频道 EPG 数据，过期返回 None"""
        all_epg = self._read_json(self.EPG_FILE)
        if not all_epg:
            return None
        
        channel_data = all_epg.get("channels", {}).get(channel_key)
        if not channel_data:
            return None
        
        # 检查是否过期
        updated_at = channel_data.get("updated_at", 0)
        if time.time() - updated_at > self.EPG_CACHE_TTL:
            return None
        
        return channel_data.get("programmes", [])
    
    def _cleanup_expired_epg(self, all_epg: dict):
        """清理过期的 EPG 缓存"""
        now = time.time()
        channels = all_epg.get("channels", {})
        expired_keys = [
            key for key, data in channels.items()
            if now - data.get("updated_at", 0) > self.EPG_CACHE_TTL
        ]
        for key in expired_keys:
            del channels[key]
    
    def clear_epg_cache(self):
        """清除所有 EPG 缓存"""
        cache_file = self.CACHE_DIR / self.EPG_FILE
        if cache_file.exists():
            cache_file.unlink()
    
    # ========== 设置缓存 ==========
    
    def save_settings(self, settings: dict):
        """保存设置"""
        self._write_json(self.SETTINGS_FILE, settings)
    
    def load_settings(self) -> dict:
        """加载设置"""
        return self._read_json(self.SETTINGS_FILE) or {}
    
    # ========== MPV 配置 ==========
    
    def get_default_mpv_dir(self) -> Path:
        """获取默认 MPV DLL 目录"""
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent / "mpv"
        else:
            return Path(__file__).parent.parent / "mpv"
    
    def save_mpv_config(self, custom_dll_path: str | None):
        """
        保存 MPV 配置
        
        Args:
            custom_dll_path: 自定义 DLL 路径（None 表示使用默认位置）
        """
        settings = self.load_settings()
        settings["mpv_custom_dll_path"] = custom_dll_path
        self.save_settings(settings)
    
    def load_mpv_config(self) -> dict:
        """
        加载 MPV 配置
        
        Returns:
            dict 包含:
                - custom_dll_path: 自定义路径（可能为 None）
                - effective_dll_path: 实际使用的 DLL 路径
                - using_custom: 是否使用自定义路径
        """
        settings = self.load_settings()
        custom_path = settings.get("mpv_custom_dll_path")
        
        # 确定实际使用的路径
        if custom_path and Path(custom_path).exists():
            effective_path = custom_path
            using_custom = True
        else:
            # 默认位置
            default_dll = self.get_default_mpv_dir() / "libmpv-2.dll"
            effective_path = str(default_dll) if default_dll.exists() else None
            using_custom = False
        
        return {
            "custom_dll_path": custom_path,
            "effective_dll_path": effective_path,
            "using_custom": using_custom,
        }
    
    def get_mpv_dll_path(self) -> Path | None:
        """
        获取应该使用的 MPV DLL 路径
        优先使用自定义路径，否则使用默认位置
        
        Returns:
            DLL 文件的 Path，或 None（如果都不存在）
        """
        config = self.load_mpv_config()
        effective = config.get("effective_dll_path")
        if effective:
            return Path(effective)
        return None
    
    def is_mpv_available(self) -> bool:
        """检查 MPV DLL 是否可用"""
        dll_path = self.get_mpv_dll_path()
        return dll_path is not None and dll_path.exists()
    
    # ========== 工具方法 ==========
    
    def _write_json(self, filename: str, data: Any):
        """写入 JSON 文件"""
        filepath = self.CACHE_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _read_json(self, filename: str) -> Any:
        """读取 JSON 文件"""
        filepath = self.CACHE_DIR / filename
        if not filepath.exists():
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None


# 全局缓存管理器实例
cache_manager = CacheManager()
