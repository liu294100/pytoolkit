from pathlib import Path


class AppConfig:
    BASE_DIR = Path(__file__).resolve().parent.parent
    REF_DIR = BASE_DIR / "ref"
    SOURCES_FILE = REF_DIR / "iptv-sources.json"
    REQUEST_TIMEOUT_SECONDS = 20
