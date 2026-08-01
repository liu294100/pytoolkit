"""HTTP 服务 - 网络请求封装"""

import re
from urllib.parse import unquote, urlparse

import requests
from requests.adapters import HTTPAdapter


# 浏览器 UA
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"

# 播放器 UA
PLAYER_UA = "Lavf/60.16.100"

# 编码相关正则
_XML_ENCODING_PATTERN = re.compile(br'encoding=["\']([\w.-]+)["\']', re.I)
_CHARSET_PATTERN = re.compile(r"charset=([\w.-]+)", re.I)
_MOJIBAKE_CHARS = set("ÃÂÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßæçèéêëìíîïðñòóôõöøùúûüýþÿ")


class HttpService:
    """HTTP 请求服务"""
    
    def __init__(self):
        self._session = requests.Session()
        self._session.mount("http://", HTTPAdapter(pool_connections=16, pool_maxsize=32))
        self._session.mount("https://", HTTPAdapter(pool_connections=16, pool_maxsize=32))
        
        # 代理设置
        self._proxy_enabled = False
        self._proxy_host = "127.0.0.1"
        self._proxy_port = 7890
    
    @property
    def proxy_settings(self) -> dict:
        return {
            "enabled": self._proxy_enabled,
            "host": self._proxy_host,
            "port": self._proxy_port,
        }
    
    def set_proxy(self, enabled: bool, host: str = "127.0.0.1", port: int = 7890):
        """设置代理"""
        self._proxy_enabled = enabled
        self._proxy_host = host.strip() or "127.0.0.1"
        self._proxy_port = port
    
    def _get_proxies(self) -> dict | None:
        if not self._proxy_enabled:
            return None
        proxy_url = f"http://{self._proxy_host}:{self._proxy_port}"
        return {"http": proxy_url, "https": proxy_url}
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """规范化 URL"""
        value = (url or "").strip().strip("`").strip("\"' ")
        value = unquote(value)
        value = value.strip().strip("`").strip("\"' ")
        return value
    
    @staticmethod
    def ensure_http_url(url: str) -> str:
        """确保是有效的 HTTP URL"""
        normalized = HttpService.normalize_url(url)
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("仅支持 http/https 地址")
        return normalized
    
    def get(
        self,
        url: str,
        timeout: int | tuple[int, int] = 30,
        headers: dict | None = None,
        stream: bool = False,
        use_player_ua: bool = False,
    ) -> requests.Response:
        """发送 GET 请求"""
        normalized_url = self.ensure_http_url(url)
        
        default_headers = {
            "User-Agent": PLAYER_UA if use_player_ua else BROWSER_UA,
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        
        # 添加 Referer
        try:
            parsed = urlparse(normalized_url)
            default_headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"
        except Exception:
            pass
        
        if headers:
            default_headers.update(headers)
        
        response = self._session.get(
            normalized_url,
            timeout=timeout if isinstance(timeout, tuple) else (8, timeout),
            headers=default_headers,
            stream=stream,
            proxies=self._get_proxies(),
        )
        response.raise_for_status()
        return response
    
    def fetch_text(self, url: str, timeout: int = 30, user_agent: str | None = None) -> str:
        """获取文本内容（自动处理编码）"""
        headers = {"User-Agent": user_agent} if user_agent else None
        response = self.get(url, timeout=timeout, headers=headers)
        return self.decode_response(response)
    
    def decode_response(self, response: requests.Response) -> str:
        """解码响应内容"""
        return decode_text_bytes(
            response.content,
            content_type=response.headers.get("Content-Type", ""),
            declared_encoding=response.encoding,
            apparent_encoding=response.apparent_encoding,
        )


def _extract_charset(content_type: str) -> str | None:
    match = _CHARSET_PATTERN.search(content_type or "")
    return match.group(1).strip("\"' ") if match else None


def _extract_xml_encoding(content: bytes) -> str | None:
    head = (content or b"")[:200]
    match = _XML_ENCODING_PATTERN.search(head)
    if not match:
        return None
    try:
        return match.group(1).decode("ascii", errors="ignore")
    except Exception:
        return None


def _score_decoded_text(text: str) -> float:
    """评估解码质量"""
    if not text:
        return float("-inf")
    length = max(len(text), 1)
    replacement_count = text.count("\ufffd")
    mojibake_count = sum(1 for ch in text if ch in _MOJIBAKE_CHARS)
    printable_count = sum(1 for ch in text if ch.isprintable() or ch in "\r\n\t")
    control_count = sum(1 for ch in text if ord(ch) < 32 and ch not in "\r\n\t")
    return (
        printable_count / length * 10
        - replacement_count * 12
        - mojibake_count * 3
        - control_count * 6
    )


def repair_text(value: str) -> str:
    """修复乱码文本"""
    text = (value or "").strip()
    if not text:
        return ""
    candidates = [text]
    if any(ch in text for ch in _MOJIBAKE_CHARS) or "\ufffd" in text:
        for source_encoding in ("latin1", "cp1252"):
            try:
                raw_bytes = text.encode(source_encoding, errors="ignore")
            except Exception:
                continue
            for target_encoding in ("utf-8", "utf-8-sig", "gb18030", "gbk", "big5"):
                try:
                    candidates.append(raw_bytes.decode(target_encoding, errors="replace"))
                except Exception:
                    continue
    best_text = text
    best_score = _score_decoded_text(text)
    for candidate in candidates[1:]:
        score = _score_decoded_text(candidate)
        if score > best_score:
            best_text = candidate
            best_score = score
    return best_text


def decode_text_bytes(
    content: bytes,
    content_type: str = "",
    declared_encoding: str | None = None,
    apparent_encoding: str | None = None,
) -> str:
    """解码字节内容为文本"""
    if not content:
        return ""
    candidates = [
        declared_encoding,
        _extract_charset(content_type),
        _extract_xml_encoding(content),
        apparent_encoding,
        "utf-8",
        "utf-8-sig",
        "gb18030",
        "gbk",
        "big5",
        "latin1",
    ]
    best_text = ""
    best_score = float("-inf")
    seen: set[str] = set()
    for encoding in candidates:
        if not encoding:
            continue
        normalized_encoding = encoding.strip().lower()
        if normalized_encoding in seen:
            continue
        seen.add(normalized_encoding)
        try:
            text = content.decode(normalized_encoding, errors="replace")
        except Exception:
            continue
        score = _score_decoded_text(text)
        if score > best_score:
            best_text = text
            best_score = score
        if text.count("\ufffd"):
            continue
        if any(ch in text for ch in _MOJIBAKE_CHARS):
            continue
        if score >= 9.5:
            best_text = text
            break
    fallback_text = best_text or content.decode("utf-8", errors="replace")
    return repair_text(fallback_text)
