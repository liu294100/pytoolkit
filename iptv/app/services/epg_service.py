import gzip
import io
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
    url: str,
    content: bytes,
    content_type: str,
    declared_encoding: str | None = None,
    apparent_encoding: str | None = None,
) -> bytes:
    is_gzip = url.lower().endswith(".gz") or "gzip" in (content_type or "").lower()
    if is_gzip:
        content = gzip.decompress(content)
    decoded = decode_text_bytes(
        content,
        content_type=content_type,
        declared_encoding=declared_encoding,
        apparent_encoding=apparent_encoding,
    )
    return decoded.encode("utf-8")


def load_epg_programmes(epg_url: str, channel_name: str, tvg_id: str, timeout: int, limit: int = 80) -> list[dict]:
    target_url = ensure_http_url(epg_url)
    response = request_url(target_url, timeout=(8, timeout))
    xml_bytes = _decode_epg_content(
        target_url,
        response.content,
        response.headers.get("Content-Type", ""),
        declared_encoding=response.encoding,
        apparent_encoding=response.apparent_encoding,
    )
    candidate_keys = _candidate_keys(channel_name, tvg_id)
    if not candidate_keys:
        return []

    stream = io.BytesIO(xml_bytes)
    programmes: list[dict] = []
    matched_channel_ids: set[str] = set()

    for _, elem in ET.iterparse(stream, events=("end",)):
        if elem.tag == "channel":
            channel_id = elem.attrib.get("id", "")
            normalized_id = _normalize(channel_id)
            display_names = [_normalize(node.text or "") for node in elem.findall("display-name")]
            all_keys = {normalized_id, *display_names}
            if any(key and any(key in value or value in key for value in all_keys if value) for key in candidate_keys):
                if channel_id:
                    matched_channel_ids.add(channel_id)
            elem.clear()
            continue

        if elem.tag != "programme":
            continue
        channel_attr = elem.attrib.get("channel", "")
        normalized_channel = _normalize(channel_attr)
        is_match = channel_attr in matched_channel_ids or any(
            key in normalized_channel or normalized_channel in key for key in candidate_keys if normalized_channel
        )
        if not is_match:
            elem.clear()
            continue

        title_node = elem.find("title")
        desc_node = elem.find("desc")
        item = {
            "channel": channel_attr,
            "title": repair_text((title_node.text or "").strip()) if title_node is not None and title_node.text else "未知节目",
            "desc": repair_text((desc_node.text or "").strip()) if desc_node is not None and desc_node.text else "",
            "start": _parse_xmltv_time(elem.attrib.get("start", "")),
            "stop": _parse_xmltv_time(elem.attrib.get("stop", "")),
        }
        programmes.append(item)
        elem.clear()
        if len(programmes) >= limit:
            break

    return programmes
