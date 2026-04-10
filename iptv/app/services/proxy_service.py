import re
from urllib.parse import quote, urljoin


URI_ATTR_PATTERN = re.compile(r'URI="([^"]+)"')


def build_proxy_url(target_url: str) -> str:
    return f"/api/proxy-stream?url={quote(target_url, safe='')}"


def rewrite_m3u8_content(content: str, playlist_url: str) -> str:
    output: list[str] = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            output.append(raw_line)
            continue

        if line.startswith("#EXT") and 'URI="' in line:
            match = URI_ATTR_PATTERN.search(line)
            if match:
                abs_key_url = urljoin(playlist_url, match.group(1))
                proxy_key_url = build_proxy_url(abs_key_url)
                line = URI_ATTR_PATTERN.sub(f'URI="{proxy_key_url}"', line)
            output.append(line)
            continue

        if line.startswith("#"):
            output.append(raw_line)
            continue

        abs_url = urljoin(playlist_url, line)
        output.append(build_proxy_url(abs_url))

    return "\n".join(output)
