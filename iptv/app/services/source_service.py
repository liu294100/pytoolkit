import json
from pathlib import Path
from typing import Any

from .http_service import decode_text_bytes, repair_text


def _repair_structure(value: Any) -> Any:
    if isinstance(value, str):
        return repair_text(value)
    if isinstance(value, list):
        return [_repair_structure(item) for item in value]
    if isinstance(value, dict):
        return {key: _repair_structure(item) for key, item in value.items()}
    return value


def load_sources(file_path: Path) -> dict[str, Any]:
    raw_bytes = file_path.read_bytes()
    json_text = decode_text_bytes(raw_bytes, content_type="application/json; charset=utf-8")
    data = _repair_structure(json.loads(json_text))

    sources = data.get("sources", [])
    data["sources"] = [source for source in sources if not source.get("disabled")]
    return data
