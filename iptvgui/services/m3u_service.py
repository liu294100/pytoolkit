"""M3U 解析服务"""

import re
from typing import Callable

from ..models import Channel, ChannelGroup
from .http_service import HttpService, repair_text


ATTRIBUTE_PATTERN = re.compile(r'([\w-]+)="([^"]*)"')


class M3uService:
    """M3U 解析服务"""
    
    def __init__(self, http_service: HttpService | None = None):
        self._http = http_service or HttpService()
    
    def load_from_url(
        self,
        url: str,
        source_name: str = "",
        timeout: int = 30,
        user_agent: str | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> list[Channel]:
        """从 URL 加载 M3U 并解析"""
        if progress_callback:
            progress_callback(f"正在加载: {url}")
        
        headers = {"User-Agent": user_agent} if user_agent else None
        response = self._http.get(url, timeout=timeout, headers=headers)
        m3u_text = self._http.decode_response(response)
        
        if progress_callback:
            progress_callback("正在解析频道列表...")
        
        return self.parse(m3u_text, source_name or url)
    
    def parse(self, m3u_text: str, source_name: str = "") -> list[Channel]:
        """解析 M3U 文本"""
        channels: list[Channel] = []
        current_meta: dict | None = None
        
        for raw_line in m3u_text.replace("\r", "").split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            
            if line.startswith("#EXTINF"):
                attrs = dict(ATTRIBUTE_PATTERN.findall(line))
                title = repair_text(line.split(",", maxsplit=1)[1].strip() if "," in line else "未命名频道")
                current_meta = {
                    "name": repair_text(attrs.get("tvg-name") or title),
                    "title": title,
                    "group": repair_text(attrs.get("group-title") or "未分组"),
                    "logo": attrs.get("tvg-logo", "").strip(),
                    "tvg_id": repair_text(attrs.get("tvg-id", "")),
                    "source_name": repair_text(source_name),
                }
                continue
            
            if line.startswith("#"):
                continue
            
            # URL 行
            if current_meta is None:
                current_meta = {
                    "name": "未命名频道",
                    "title": "未命名频道",
                    "group": "未分组",
                    "logo": "",
                    "tvg_id": "",
                    "source_name": repair_text(source_name),
                }
            
            channels.append(Channel(
                name=current_meta["name"],
                url=line,
                title=current_meta["title"],
                group=current_meta["group"],
                logo=current_meta["logo"],
                tvg_id=current_meta["tvg_id"],
                source_name=current_meta["source_name"],
            ))
            current_meta = None
        
        return channels
    
    def parse_and_group(self, m3u_text: str, source_name: str = "") -> list[ChannelGroup]:
        """解析 M3U 并按频道名聚合"""
        channels = self.parse(m3u_text, source_name)
        return ChannelGroup.group_channels(channels)
    
    def load_and_group(
        self,
        url: str,
        source_name: str = "",
        timeout: int = 30,
        user_agent: str | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> list[ChannelGroup]:
        """从 URL 加载并聚合"""
        channels = self.load_from_url(url, source_name, timeout, user_agent, progress_callback)
        
        if progress_callback:
            progress_callback(f"正在聚合频道（共 {len(channels)} 个信号源）...")
        
        return ChannelGroup.group_channels(channels)
    
    def get_groups(self, channels: list[Channel]) -> list[str]:
        """获取所有频道分组"""
        groups = sorted(set(ch.group for ch in channels if ch.group))
        return groups
    
    def filter_channels(
        self,
        channels: list[Channel],
        keyword: str = "",
        group: str = "",
    ) -> list[Channel]:
        """筛选频道"""
        result = channels
        
        if keyword:
            keyword_lower = keyword.lower()
            result = [ch for ch in result if keyword_lower in ch.name.lower() or keyword_lower in ch.title.lower()]
        
        if group:
            result = [ch for ch in result if ch.group == group]
        
        return result
    
    def filter_groups(
        self,
        groups: list[ChannelGroup],
        keyword: str = "",
        group: str = "",
    ) -> list[ChannelGroup]:
        """筛选频道分组"""
        result = groups
        
        if keyword:
            keyword_lower = keyword.lower()
            result = [g for g in result if keyword_lower in g.name.lower()]
        
        if group:
            result = [g for g in result if g.group == group]
        
        return result
