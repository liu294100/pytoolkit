import re

from .http_service import repair_text


ATTRIBUTE_PATTERN = re.compile(r'([\w-]+)="([^"]*)"')


def parse_m3u(m3u_text: str, source_name: str) -> list[dict]:
    channels: list[dict] = []
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
                "tvgId": repair_text(attrs.get("tvg-id", "")),
                "sourceName": repair_text(source_name),
            }
            continue

        if line.startswith("#"):
            continue

        if current_meta is None:
            current_meta = {
                "name": "未命名频道",
                "title": "未命名频道",
                "group": "未分组",
                "logo": "",
                "tvgId": "",
                "sourceName": repair_text(source_name),
            }

        channels.append({**current_meta, "url": line})
        current_meta = None

    return channels
