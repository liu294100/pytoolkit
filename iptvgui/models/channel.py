"""频道数据模型"""

from dataclasses import dataclass, field


@dataclass
class Channel:
    """频道信息"""
    name: str
    url: str
    title: str = ""
    group: str = "未分组"
    logo: str = ""
    tvg_id: str = ""
    source_name: str = ""
    
    def __post_init__(self):
        if not self.title:
            self.title = self.name
    
    @property
    def display_name(self) -> str:
        """显示名称"""
        return self.title or self.name
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "url": self.url,
            "title": self.title,
            "group": self.group,
            "logo": self.logo,
            "tvgId": self.tvg_id,
            "sourceName": self.source_name,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Channel":
        return cls(
            name=data.get("name", ""),
            url=data.get("url", ""),
            title=data.get("title", ""),
            group=data.get("group", "未分组"),
            logo=data.get("logo", ""),
            tvg_id=data.get("tvgId", ""),
            source_name=data.get("sourceName", ""),
        )


@dataclass
class ChannelGroup:
    """频道分组，支持多信号源"""
    name: str
    tvg_id: str = ""
    group: str = "未分组"
    logo: str = ""
    channels: list[Channel] = field(default_factory=list)
    
    @property
    def source_count(self) -> int:
        """信号源数量"""
        return len(self.channels)
    
    @property
    def current_channel(self) -> Channel | None:
        """当前选中的频道（默认第一个）"""
        return self.channels[0] if self.channels else None
    
    def add_channel(self, channel: Channel):
        """添加频道（信号源）"""
        self.channels.append(channel)
    
    @staticmethod
    def group_channels(channels: list[Channel]) -> list["ChannelGroup"]:
        """将频道列表按名称/tvg_id 聚合为分组"""
        groups: dict[str, ChannelGroup] = {}
        
        for channel in channels:
            # 使用 tvg_id 或 name 作为聚合 key
            key = channel.tvg_id.strip().lower() if channel.tvg_id else channel.name.strip().lower()
            if not key:
                key = channel.name.strip().lower()
            
            if key not in groups:
                groups[key] = ChannelGroup(
                    name=channel.name,
                    tvg_id=channel.tvg_id,
                    group=channel.group,
                    logo=channel.logo,
                )
            groups[key].add_channel(channel)
        
        return list(groups.values())
