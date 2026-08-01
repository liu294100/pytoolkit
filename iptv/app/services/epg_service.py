import gzip
import hashlib
import io
import threading
import time
from datetime import datetime
from xml.etree import ElementTree as ET

from .http_service import decode_text_bytes, ensure_http_url, repair_text, request_url


def _normalize(value: str) -> str:
    return repair_text(value or "").strip().lower().replace(" ", "")


def _candidate_keys(channel_name: str, tvg_id: str) -> set[str]:
    values = {
        _normalize(tvg_id),
        _normalize(channel_name),
        _normalize(channel_name).replace("-", ""),
        _normalize(channel_name).replace("高清", "").replace("标清", "").replace("超清", ""),
        _normalize(channel_name).replace("cctv", "cctv"),
    }
    return {item for item in values if item}


def _parse_xmltv_time(value: str) -> str:
    if not value:
        return ""
    raw = value.strip()
    try:
        dt = datetime.strptime(raw[:14], "%Y%m%d%H%M%S")
        return dt.strftime("%m-%d %H:%M")
    except Exception:
        return raw


def _decode_epg_content(
    content: bytes,
    content_type: str,
    declared_encoding: str | None = None,
    apparent_encoding: str | None = None,
) -> bytes:
    # 检测实际内容是否为 gzip（magic bytes: 1f 8b）
    is_gzip_content = content[:2] == b'\x1f\x8b'
    if is_gzip_content:
        try:
            content = gzip.decompress(content)
        except Exception:
            pass  # 解压失败则使用原内容
    decoded = decode_text_bytes(
        content,
        content_type=content_type,
        declared_encoding=declared_encoding,
        apparent_encoding=apparent_encoding,
    )
    return decoded.encode("utf-8")


# ============== EPG 缓存 ==============

class EpgCache:
    """EPG 内存缓存，支持两级缓存：
    1. EPG 源级缓存：缓存整个 EPG 文件的解析结果（频道映射 + 全部节目）
    2. 频道级缓存：缓存特定频道的节目查询结果
    """
    
    # EPG 源缓存过期时间（秒），EPG 数据通常一天更新一次
    SOURCE_CACHE_TTL = 3600  # 1 小时
    # 频道节目缓存过期时间（秒）
    CHANNEL_CACHE_TTL = 1800  # 30 分钟
    # 最大缓存 EPG 源数量
    MAX_SOURCE_CACHE = 10
    # 最大缓存频道查询数量
    MAX_CHANNEL_CACHE = 200
    
    def __init__(self):
        self._lock = threading.RLock()
        # EPG 源缓存: {url_hash: {"data": ParsedEpgData, "time": timestamp}}
        self._source_cache: dict[str, dict] = {}
        # 频道节目缓存: {cache_key: {"programmes": list, "time": timestamp}}
        self._channel_cache: dict[str, dict] = {}
    
    def _hash_url(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()[:16]
    
    def _make_channel_key(self, epg_url: str, channel_name: str, tvg_id: str) -> str:
        return f"{self._hash_url(epg_url)}|{_normalize(channel_name)}|{_normalize(tvg_id)}"
    
    def _cleanup_if_needed(self):
        """清理过期缓存"""
        now = time.time()
        
        # 清理过期的源缓存
        expired_sources = [
            k for k, v in self._source_cache.items()
            if now - v["time"] > self.SOURCE_CACHE_TTL
        ]
        for k in expired_sources:
            del self._source_cache[k]
        
        # 清理过期的频道缓存
        expired_channels = [
            k for k, v in self._channel_cache.items()
            if now - v["time"] > self.CHANNEL_CACHE_TTL
        ]
        for k in expired_channels:
            del self._channel_cache[k]
        
        # 如果缓存过多，删除最旧的
        if len(self._source_cache) > self.MAX_SOURCE_CACHE:
            sorted_keys = sorted(self._source_cache.keys(), key=lambda k: self._source_cache[k]["time"])
            for k in sorted_keys[:len(self._source_cache) - self.MAX_SOURCE_CACHE]:
                del self._source_cache[k]
        
        if len(self._channel_cache) > self.MAX_CHANNEL_CACHE:
            sorted_keys = sorted(self._channel_cache.keys(), key=lambda k: self._channel_cache[k]["time"])
            for k in sorted_keys[:len(self._channel_cache) - self.MAX_CHANNEL_CACHE]:
                del self._channel_cache[k]
    
    def get_channel_programmes(self, epg_url: str, channel_name: str, tvg_id: str) -> list[dict] | None:
        """获取缓存的频道节目"""
        cache_key = self._make_channel_key(epg_url, channel_name, tvg_id)
        with self._lock:
            entry = self._channel_cache.get(cache_key)
            if entry and time.time() - entry["time"] < self.CHANNEL_CACHE_TTL:
                return entry["programmes"]
        return None
    
    def set_channel_programmes(self, epg_url: str, channel_name: str, tvg_id: str, programmes: list[dict]):
        """缓存频道节目"""
        cache_key = self._make_channel_key(epg_url, channel_name, tvg_id)
        with self._lock:
            self._channel_cache[cache_key] = {
                "programmes": programmes,
                "time": time.time(),
            }
            self._cleanup_if_needed()
    
    def get_source_data(self, epg_url: str) -> "ParsedEpgData | None":
        """获取缓存的 EPG 源数据"""
        url_hash = self._hash_url(epg_url)
        with self._lock:
            entry = self._source_cache.get(url_hash)
            if entry and time.time() - entry["time"] < self.SOURCE_CACHE_TTL:
                return entry["data"]
        return None
    
    def set_source_data(self, epg_url: str, data: "ParsedEpgData"):
        """缓存 EPG 源数据"""
        url_hash = self._hash_url(epg_url)
        with self._lock:
            self._source_cache[url_hash] = {
                "data": data,
                "time": time.time(),
            }
            self._cleanup_if_needed()
    
    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        with self._lock:
            return {
                "source_cache_count": len(self._source_cache),
                "channel_cache_count": len(self._channel_cache),
            }


class ParsedEpgData:
    """解析后的 EPG 数据结构"""
    
    def __init__(self):
        # 频道 ID -> 标准化名称集合
        self.channel_map: dict[str, set[str]] = {}
        # 频道 ID -> 节目列表
        self.programmes: dict[str, list[dict]] = {}
    
    def find_programmes(self, channel_name: str, tvg_id: str, limit: int = 80) -> list[dict]:
        """根据频道名或 tvg_id 查找节目"""
        candidate_keys = _candidate_keys(channel_name, tvg_id)
        if not candidate_keys:
            return []
        
        matched_channel_ids: set[str] = set()
        
        # 匹配频道
        for channel_id, names in self.channel_map.items():
            all_keys = {_normalize(channel_id), *names}
            if any(key and any(key in value or value in key for value in all_keys if value) for key in candidate_keys):
                matched_channel_ids.add(channel_id)
        
        # 收集节目
        result: list[dict] = []
        for channel_id in matched_channel_ids:
            progs = self.programmes.get(channel_id, [])
            result.extend(progs)
            if len(result) >= limit:
                break
        
        # 如果没有通过 channel_map 匹配到，尝试直接匹配节目的 channel 属性
        if not result:
            for channel_id, progs in self.programmes.items():
                normalized_channel = _normalize(channel_id)
                if any(key in normalized_channel or normalized_channel in key for key in candidate_keys if normalized_channel):
                    result.extend(progs)
                    if len(result) >= limit:
                        break
        
        return result[:limit]


# 全局缓存实例
_epg_cache = EpgCache()


def _parse_epg_xml(xml_bytes: bytes) -> ParsedEpgData:
    """解析 EPG XML 并返回结构化数据"""
    data = ParsedEpgData()
    stream = io.BytesIO(xml_bytes)
    
    # 使用 start 和 end 事件，确保在 end 时子元素文本已被读取
    context = ET.iterparse(stream, events=("start", "end"))
    
    # 存储当前正在处理的 programme 的信息
    current_programme = None
    current_title = None
    current_desc = None
    
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
        
        # event == "end"
        if elem.tag == "title" and current_programme is not None:
            current_title = repair_text((elem.text or "").strip()) if elem.text else ""
            
        elif elem.tag == "desc" and current_programme is not None:
            current_desc = repair_text((elem.text or "").strip()) if elem.text else ""
            
        elif elem.tag == "display-name":
            # 由 channel 的 end 事件处理
            pass
            
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


def _fetch_and_parse_epg(epg_url: str, timeout: int) -> ParsedEpgData:
    """获取并解析 EPG 数据（带源级缓存）"""
    # 先检查缓存
    cached = _epg_cache.get_source_data(epg_url)
    if cached is not None:
        return cached
    
    # 下载并解析
    target_url = ensure_http_url(epg_url)
    response = request_url(target_url, timeout=(8, timeout))
    xml_bytes = _decode_epg_content(
        response.content,
        response.headers.get("Content-Type", ""),
        declared_encoding=response.encoding,
        apparent_encoding=response.apparent_encoding,
    )
    
    # 解析
    data = _parse_epg_xml(xml_bytes)
    
    # 缓存
    _epg_cache.set_source_data(epg_url, data)
    
    return data


def load_epg_programmes(epg_url: str, channel_name: str, tvg_id: str, timeout: int, limit: int = 80) -> list[dict]:
    """加载指定频道的节目表（带缓存）"""
    # 先检查频道级缓存
    cached = _epg_cache.get_channel_programmes(epg_url, channel_name, tvg_id)
    if cached is not None:
        return cached[:limit]
    
    # 获取 EPG 数据（会自动使用源级缓存）
    epg_data = _fetch_and_parse_epg(epg_url, timeout)
    
    # 查找节目
    programmes = epg_data.find_programmes(channel_name, tvg_id, limit)
    
    # 缓存结果
    _epg_cache.set_channel_programmes(epg_url, channel_name, tvg_id, programmes)
    
    return programmes


def preload_epg_source(epg_url: str, timeout: int) -> dict:
    """预加载 EPG 源，全量下载并缓存到内存，返回统计信息"""
    epg_data = _fetch_and_parse_epg(epg_url, timeout)
    
    return {
        "channel_count": len(epg_data.channel_map),
        "programme_count": sum(len(progs) for progs in epg_data.programmes.values()),
    }


def get_epg_cache_stats() -> dict:
    """获取 EPG 缓存统计信息"""
    return _epg_cache.get_stats()
