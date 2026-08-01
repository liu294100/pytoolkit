"""直播源配置数据模型"""

from dataclasses import dataclass, field


@dataclass
class Source:
    """直播源"""
    name: str
    url: str
    type: str = "m3u"
    group: str = ""
    epg: str = ""
    user_agent: str = ""
    note: str = ""
    disabled: bool = False
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "url": self.url,
            "type": self.type,
            "group": self.group,
            "epg": self.epg,
            "userAgent": self.user_agent,
            "note": self.note,
            "disabled": self.disabled,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Source":
        return cls(
            name=data.get("name", ""),
            url=data.get("url", ""),
            type=data.get("type", "m3u"),
            group=data.get("group", ""),
            epg=data.get("epg", ""),
            user_agent=data.get("userAgent", ""),
            note=data.get("note", ""),
            disabled=data.get("disabled", False),
        )


@dataclass
class EpgSource:
    """EPG 节目源"""
    name: str
    url: str
    
    def to_dict(self) -> dict:
        return {"name": self.name, "url": self.url}
    
    @classmethod
    def from_dict(cls, data: dict) -> "EpgSource":
        return cls(
            name=data.get("name", ""),
            url=data.get("url", ""),
        )


@dataclass
class SourceConfig:
    """源配置文件结构"""
    version: int = 2
    sources: list[Source] = field(default_factory=list)
    epg_sources: list[EpgSource] = field(default_factory=list)
    notice: str = ""
    
    @classmethod
    def from_dict(cls, data: dict) -> "SourceConfig":
        sources = [Source.from_dict(s) for s in data.get("sources", []) if not s.get("disabled")]
        epg_sources = [EpgSource.from_dict(e) for e in data.get("epgSources", [])]
        return cls(
            version=data.get("version", 2),
            sources=sources,
            epg_sources=epg_sources,
            notice=data.get("notice", ""),
        )
    
    def get_source_groups(self) -> list[str]:
        """获取所有源分组"""
        groups = sorted(set(s.group for s in self.sources if s.group))
        return groups
