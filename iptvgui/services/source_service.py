"""直播源配置服务"""

import json
import sys
from pathlib import Path

from ..models import Source, EpgSource, SourceConfig
from .http_service import decode_text_bytes, repair_text


def _get_config_path() -> Path:
    """获取配置文件路径，支持 PyInstaller 打包"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，先找 exe 同目录，再找 _MEIPASS/resources
        exe_dir = Path(sys.executable).parent
        if (exe_dir / "iptv-sources.json").exists():
            return exe_dir / "iptv-sources.json"
        return Path(sys._MEIPASS) / "resources" / "iptv-sources.json"
    else:
        # 开发模式，在 resources 目录下
        return Path(__file__).parent.parent / "resources" / "iptv-sources.json"


def _repair_structure(value):
    """递归修复结构中的文本"""
    if isinstance(value, str):
        return repair_text(value)
    if isinstance(value, list):
        return [_repair_structure(item) for item in value]
    if isinstance(value, dict):
        return {key: _repair_structure(item) for key, item in value.items()}
    return value


class SourceService:
    """直播源配置服务"""
    
    # 默认配置文件路径
    DEFAULT_CONFIG_PATH = _get_config_path()
    
    def __init__(self, config_path: Path | None = None):
        self._config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._config: SourceConfig | None = None
    
    @property
    def config_path(self) -> Path:
        return self._config_path
    
    @config_path.setter
    def config_path(self, path: Path):
        self._config_path = path
        self._config = None  # 重置缓存
    
    def load_config(self, force_reload: bool = False) -> SourceConfig:
        """加载配置文件"""
        if self._config is not None and not force_reload:
            return self._config
        
        if not self._config_path.exists():
            self._config = SourceConfig()
            return self._config
        
        raw_bytes = self._config_path.read_bytes()
        json_text = decode_text_bytes(raw_bytes, content_type="application/json; charset=utf-8")
        data = _repair_structure(json.loads(json_text))
        
        self._config = SourceConfig.from_dict(data)
        return self._config
    
    def get_sources(self) -> list[Source]:
        """获取所有直播源"""
        config = self.load_config()
        return config.sources
    
    def get_epg_sources(self) -> list[EpgSource]:
        """获取所有 EPG 源"""
        config = self.load_config()
        return config.epg_sources
    
    def get_source_groups(self) -> list[str]:
        """获取源分组列表"""
        config = self.load_config()
        return config.get_source_groups()
    
    def get_sources_by_group(self, group: str) -> list[Source]:
        """按分组获取源"""
        sources = self.get_sources()
        if not group:
            return sources
        return [s for s in sources if s.group == group]
    
    def find_source_by_name(self, name: str) -> Source | None:
        """按名称查找源"""
        sources = self.get_sources()
        for source in sources:
            if source.name == name:
                return source
        return None
    
    def find_epg_by_name(self, name: str) -> EpgSource | None:
        """按名称查找 EPG 源"""
        epg_sources = self.get_epg_sources()
        for epg in epg_sources:
            if epg.name == name:
                return epg
        return None
