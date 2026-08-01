"""EPG 节目单服务"""

import gzip
import hashlib
import io
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from xml.etree import ElementTree as ET
from typing import Callable

from .http_service import HttpService, repair_text, decode_text_bytes


def _normalize(value: str) -> str:
    return repair_text(value or "").strip().lower().replace(" ", "")


def _candidate_keys(channel_name: str, tvg_id: str) -> set[str]:
    """生成用于匹配的候选关键字"""
    values = set()
    
    # 添加原始值
    if tvg_id:
        values.add(_normalize(tvg_id))
    if channel_name:
        norm_name = _normalize(channel_name)
        values.add(norm_name)
        # 去掉清晰度后缀
        for suffix in ["高清", "标清", "超清", "hd", "sd", "4k"]:
            norm_name = norm_name.replace(suffix, "")
        values.add(norm_name)
    
    return {item for item in values if item}


def _is_exact_match(key: str, value: str) -> bool:
    """精确匹配：完全相等或者是完整的频道名匹配"""
    if not key or not value:
        return False
    
    # 完全相等
    if key == value:
        return True
    
    # 处理 CCTV 频道的特殊情况
    # cctv6 不应该匹配 cctv5、cctv16 等
    import re
    
    # 提取频道号（如 cctv6 -> 6, cctv5+ -> 5+）
    cctv_pattern = re.compile(r'^cctv-?(\d+\+?)$')
    
    key_match = cctv_pattern.match(key)
    value_match = cctv_pattern.match(value)
    
    if key_match and value_match:
        # 两个都是 CCTV 频道，必须频道号完全一致
        return key_match.group(1) == value_match.group(1)
    
    # 对于其他频道，如果一个包含另一个，检查是否是完整词匹配
    # 比如 "湖南卫视" 可以匹配 "湖南卫视高清"，但 "cctv5" 不能匹配 "cctv5+"
    if key in value:
        # key 是 value 的子串，检查后面是否是数字（避免 cctv5 匹配 cctv5+）
        suffix = value[value.find(key) + len(key):]
        if suffix and suffix[0].isdigit():
            return False
        return True
    
    if value in key:
        suffix = key[key.find(value) + len(value):]
        if suffix and suffix[0].isdigit():
            return False
        return True
    
    return False


def _parse_xmltv_time(value: str) -> str:
    if not value:
        return ""
    raw = value.strip()
    try:
        dt = datetime.strptime(raw[:14], "%Y%m%d%H%M%S")
        return dt.strftime("%m-%d %H:%M")
    except Exception:
        return raw


@dataclass
class Programme:
    """节目信息"""
    channel: str
    title: str
    desc: str = ""
    start: str = ""
    stop: str = ""
    
    def to_dict(self) -> dict:
        return {
            "channel": self.channel,
            "title": self.title,
            "desc": self.desc,
            "start": self.start,
            "stop": self.stop,
        }


@dataclass
class ParsedEpgData:
    """解析后的 EPG 数据"""
    channel_map: dict[str, set[str]] = field(default_factory=dict)
    programmes: dict[str, list[dict]] = field(default_factory=dict)
    
    def find_programmes(self, channel_name: str, tvg_id: str, limit: int = 80) -> list[dict]:
        """查找频道节目"""
        candidate_keys = _candidate_keys(channel_name, tvg_id)
        if not candidate_keys:
            return []
        
        matched_channel_ids: set[str] = set()
        
        # 使用精确匹配
        for channel_id, names in self.channel_map.items():
            all_values = {_normalize(channel_id), *names}
            for key in candidate_keys:
                for value in all_values:
                    if value and _is_exact_match(key, value):
                        matched_channel_ids.add(channel_id)
                        break
        
        result: list[dict] = []
        for channel_id in matched_channel_ids:
            progs = self.programmes.get(channel_id, [])
            result.extend(progs)
            if len(result) >= limit:
                break
        
        if not result:
            for channel_id, progs in self.programmes.items():
                normalized_channel = _normalize(channel_id)
                for key in candidate_keys:
                    if normalized_channel and _is_exact_match(key, normalized_channel):
                        result.extend(progs)
                        break
                if len(result) >= limit:
                    break
        
        return result[:limit]


class EpgCache:
    """EPG 缓存"""
    
    SOURCE_CACHE_TTL = 3600  # 1 小时
    CHANNEL_CACHE_TTL = 1800  # 30 分钟
    MAX_SOURCE_CACHE = 10
    MAX_CHANNEL_CACHE = 200
    
    def __init__(self):
        self._lock = threading.RLock()
        self._source_cache: dict[str, dict] = {}
        self._channel_cache: dict[str, dict] = {}
    
    def _hash_url(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()[:16]
    
    def _make_channel_key(self, epg_url: str, channel_name: str, tvg_id: str) -> str:
        return f"{self._hash_url(epg_url)}|{_normalize(channel_name)}|{_normalize(tvg_id)}"
    
    def _cleanup_if_needed(self):
        now = time.time()
        
        expired_sources = [k for k, v in self._source_cache.items() if now - v["time"] > self.SOURCE_CACHE_TTL]
        for k in expired_sources:
            del self._source_cache[k]
        
        expired_channels = [k for k, v in self._channel_cache.items() if now - v["time"] > self.CHANNEL_CACHE_TTL]
        for k in expired_channels:
            del self._channel_cache[k]
        
        if len(self._source_cache) > self.MAX_SOURCE_CACHE:
            sorted_keys = sorted(self._source_cache.keys(), key=lambda k: self._source_cache[k]["time"])
            for k in sorted_keys[:len(self._source_cache) - self.MAX_SOURCE_CACHE]:
                del self._source_cache[k]
        
        if len(self._channel_cache) > self.MAX_CHANNEL_CACHE:
            sorted_keys = sorted(self._channel_cache.keys(), key=lambda k: self._channel_cache[k]["time"])
            for k in sorted_keys[:len(self._channel_cache) - self.MAX_CHANNEL_CACHE]:
                del self._channel_cache[k]
    
    def get_channel_programmes(self, epg_url: str, channel_name: str, tvg_id: str) -> list[dict] | None:
        cache_key = self._make_channel_key(epg_url, channel_name, tvg_id)
        with self._lock:
            entry = self._channel_cache.get(cache_key)
            if entry and time.time() - entry["time"] < self.CHANNEL_CACHE_TTL:
                return entry["programmes"]
        return None
    
    def set_channel_programmes(self, epg_url: str, channel_name: str, tvg_id: str, programmes: list[dict]):
        cache_key = self._make_channel_key(epg_url, channel_name, tvg_id)
        with self._lock:
            self._channel_cache[cache_key] = {"programmes": programmes, "time": time.time()}
            self._cleanup_if_needed()
    
    def get_source_data(self, epg_url: str) -> ParsedEpgData | None:
        url_hash = self._hash_url(epg_url)
        with self._lock:
            entry = self._source_cache.get(url_hash)
            if entry and time.time() - entry["time"] < self.SOURCE_CACHE_TTL:
                return entry["data"]
        return None
    
    def set_source_data(self, epg_url: str, data: ParsedEpgData):
        url_hash = self._hash_url(epg_url)
        with self._lock:
            self._source_cache[url_hash] = {"data": data, "time": time.time()}
            self._cleanup_if_needed()
    
    def get_stats(self) -> dict:
        with self._lock:
            return {
                "source_cache_count": len(self._source_cache),
                "channel_cache_count": len(self._channel_cache),
            }


class EpgService:
    """EPG 服务"""
    
    def __init__(self, http_service: HttpService | None = None):
        self._http = http_service or HttpService()
        self._cache = EpgCache()
    
    def load_programmes(
        self,
        epg_url: str,
        channel_name: str,
        tvg_id: str = "",
        timeout: int = 60,
        limit: int = 80,
        progress_callback: Callable[[str], None] | None = None,
    ) -> list[dict]:
        """加载指定频道的节目表"""
        # 检查缓存
        cached = self._cache.get_channel_programmes(epg_url, channel_name, tvg_id)
        if cached is not None:
            return cached[:limit]
        
        if progress_callback:
            progress_callback(f"正在加载 EPG: {epg_url}")
        
        # 获取 EPG 数据
        epg_data = self._fetch_and_parse(epg_url, timeout, progress_callback)
        
        if progress_callback:
            progress_callback("正在查找节目...")
        
        # 查找节目
        programmes = epg_data.find_programmes(channel_name, tvg_id, limit)
        
        # 缓存结果
        self._cache.set_channel_programmes(epg_url, channel_name, tvg_id, programmes)
        
        return programmes
    
    def _fetch_and_parse(
        self,
        epg_url: str,
        timeout: int,
        progress_callback: Callable[[str], None] | None = None,
    ) -> ParsedEpgData:
        """获取并解析 EPG"""
        cached = self._cache.get_source_data(epg_url)
        if cached is not None:
            return cached
        
        response = self._http.get(epg_url, timeout=(8, timeout))
        content = response.content
        
        # 解压 gzip
        if content[:2] == b'\x1f\x8b':
            try:
                content = gzip.decompress(content)
            except Exception:
                pass
        
        if progress_callback:
            progress_callback("正在解析 EPG XML...")
        
        # 解码
        xml_text = decode_text_bytes(
            content,
            content_type=response.headers.get("Content-Type", ""),
            declared_encoding=response.encoding,
            apparent_encoding=response.apparent_encoding,
        )
        xml_bytes = xml_text.encode("utf-8")
        
        # 解析
        data = self._parse_xml(xml_bytes)
        
        # 缓存
        self._cache.set_source_data(epg_url, data)
        
        return data
    
    def _parse_xml(self, xml_bytes: bytes) -> ParsedEpgData:
        """解析 EPG XML"""
        data = ParsedEpgData()
        stream = io.BytesIO(xml_bytes)
        
        current_programme = None
        current_title = None
        current_desc = None
        
        context = ET.iterparse(stream, events=("start", "end"))
        
        for event, elem in context:
            if event == "start":
                if elem.tag == "programme":
                    current_programme = {
                        "channel": elem.attrib.get("channel", ""),
                        "start": _parse_xmltv_time(elem.attrib.get("start", "")),
                        "stop": _parse_xmltv_time(elem.attrib.get("stop", "")),
                    }
                    current_title = None
                    current_desc = None
                continue
            
            if elem.tag == "title" and current_programme is not None:
                current_title = repair_text((elem.text or "").strip()) if elem.text else ""
            
            elif elem.tag == "desc" and current_programme is not None:
                current_desc = repair_text((elem.text or "").strip()) if elem.text else ""
            
            elif elem.tag == "channel":
                channel_id = elem.attrib.get("id", "")
                if channel_id:
                    display_names = {_normalize(node.text or "") for node in elem.findall("display-name") if node.text}
                    data.channel_map[channel_id] = display_names
                elem.clear()
            
            elif elem.tag == "programme":
                if current_programme and current_programme["channel"]:
                    item = {
                        "channel": current_programme["channel"],
                        "title": current_title or "未知节目",
                        "desc": current_desc or "",
                        "start": current_programme["start"],
                        "stop": current_programme["stop"],
                    }
                    channel_attr = current_programme["channel"]
                    if channel_attr not in data.programmes:
                        data.programmes[channel_attr] = []
                    data.programmes[channel_attr].append(item)
                current_programme = None
                elem.clear()
        
        return data
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计"""
        return self._cache.get_stats()
