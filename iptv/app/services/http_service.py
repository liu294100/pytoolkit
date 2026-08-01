import re
from urllib.parse import unquote, urlparse

import requests
from requests.adapters import HTTPAdapter

# 浏览器 UA 用于获取 M3U/EPG 等文本资源
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 播放器 UA 用于代理流媒体，避免部分源拦截浏览器 UA
PLAYER_HEADERS = {
    "User-Agent": "Lavf/60.16.100",
    "Accept": "*/*",
}

# 默认使用浏览器 UA（兼容旧代码）
DEFAULT_HEADERS = BROWSER_HEADERS

_SESSION = requests.Session()
_SESSION.mount("http://", HTTPAdapter(pool_connections=32, pool_maxsize=64))
_SESSION.mount("https://", HTTPAdapter(pool_connections=32, pool_maxsize=64))

_PROXY_SETTINGS = {
    "enabled": False,
    "host": "127.0.0.1",
    "port": 7890,
}

_XML_ENCODING_PATTERN = re.compile(br'encoding=["\']([\w.-]+)["\']', re.I)
_CHARSET_PATTERN = re.compile(r"charset=([\w.-]+)", re.I)
_MOJIBAKE_CHARS = set("ÃÂÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßæçèéêëìíîïðñòóôõöøùúûüýþÿ")


def normalize_input_url(url: str) -> str:
    value = (url or "").strip().strip("`").strip("\"' ")
    value = unquote(value)
    value = value.strip().strip("`").strip("\"' ")
    source_name_index = value.find("&source_name=")
    if source_name_index > 0:
        value = value[:source_name_index]
    return value


def ensure_http_url(url: str) -> str:
    normalized = normalize_input_url(url)
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("仅支持 http/https 地址")
    return normalized


def get_proxy_settings() -> dict:
    return {
        "enabled": bool(_PROXY_SETTINGS["enabled"]),
        "host": str(_PROXY_SETTINGS["host"]),
        "port": int(_PROXY_SETTINGS["port"]),
    }


def update_proxy_settings(enabled: bool, host: str, port: int | str) -> dict:
    host_value = (host or "127.0.0.1").strip() or "127.0.0.1"
    try:
        port_value = int(port)
    except Exception as exc:
        raise ValueError("代理端口必须是数字") from exc
    if port_value <= 0 or port_value > 65535:
        raise ValueError("代理端口范围无效")

    _PROXY_SETTINGS["enabled"] = bool(enabled)
    _PROXY_SETTINGS["host"] = host_value
    _PROXY_SETTINGS["port"] = port_value
    return get_proxy_settings()


def _build_request_proxies() -> dict | None:
    if not _PROXY_SETTINGS["enabled"]:
        return None
    proxy_url = f"http://{_PROXY_SETTINGS['host']}:{_PROXY_SETTINGS['port']}"
    return {
        "http": proxy_url,
        "https": proxy_url,
    }


def _extract_embedded_upstream(url: str) -> str | None:
    marker = "https://gh.aptv.app/"
    if not url.startswith(marker):
        return None
    embedded = url[len(marker):].strip()
    if embedded.startswith("http://") or embedded.startswith("https://"):
        return embedded
    return None


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
        if replacement_count := text.count("\ufffd"):
            continue
        if any(ch in text for ch in _MOJIBAKE_CHARS):
            continue
        if score >= 9.5:
            best_text = text
            break
    fallback_text = best_text or content.decode("utf-8", errors="replace")
    return repair_text(fallback_text)


def _build_referer(url: str) -> str:
    """根据 URL 生成 Referer 头，用于绕过防盗链检测"""
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/"
    except Exception:
        return ""


def request_url(url: str, timeout: int | tuple[int, int], stream: bool = False, extra_headers: dict | None = None, use_player_ua: bool = False) -> requests.Response:
    normalized_url = ensure_http_url(url)
    base_headers = PLAYER_HEADERS if use_player_ua else DEFAULT_HEADERS
    headers = {**base_headers, **(extra_headers or {})}
    # 添加 Referer 头绕过防盗链
    if "Referer" not in headers:
        referer = _build_referer(normalized_url)
        if referer:
            headers["Referer"] = referer
    response = _SESSION.get(
        normalized_url,
        timeout=timeout,
        headers=headers,
        stream=stream,
        proxies=_build_request_proxies(),
    )
    if response.ok:
        return response

    embedded_upstream = _extract_embedded_upstream(normalized_url)
    if embedded_upstream and response.status_code in (401, 403, 429, 500, 502, 503):
        response.close()
        fallback_response = _SESSION.get(
            embedded_upstream,
            timeout=timeout,
            headers=headers,
            stream=stream,
            proxies=_build_request_proxies(),
        )
        if fallback_response.ok:
            return fallback_response
        fallback_response.raise_for_status()

    response.raise_for_status()
    return response


def fetch_text(url: str, timeout: int, user_agent: str | None = None) -> str:
    extra_headers = {"User-Agent": user_agent} if user_agent else None
    response = request_url(url, timeout=(8, timeout), extra_headers=extra_headers)
    return decode_text_bytes(
        response.content,
        content_type=response.headers.get("Content-Type", ""),
        declared_encoding=response.encoding,
        apparent_encoding=response.apparent_encoding,
    )
