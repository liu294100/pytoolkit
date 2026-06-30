"""GitLab Code Search - Application entry point.

High-performance desktop code search tool for GitLab repositories.
Uses ripgrep for blazing fast search and PySide6 for the GUI.

Usage:
    python main.py
    python main.py --config path/to/config.json
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from gitlab_code_search.model.config import AppConfig
from gitlab_code_search.gui.main_window import MainWindow


def setup_logging() -> None:
    """Configure logging to file and console."""
    log_dir = Path(__file__).parent / "data"
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "app.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def find_config_path() -> Path:
    """Determine config file path from args or default location."""
    # Check command line args
    if len(sys.argv) > 2 and sys.argv[1] == "--config":
        return Path(sys.argv[2])

    # Default: config.json next to main.py
    return Path(__file__).parent / "config.json"


def main() -> int:
    """Application entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting GitLab Code Search")

    # Load configuration
    config_path = find_config_path()
    config = AppConfig.load(config_path)
    logger.info("Config loaded from: %s", config_path)

    # Ensure directories exist
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    config.db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create Qt application
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("GitLab Code Search")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("GitLabCodeSearch")

    # Main window
    window = MainWindow(config)
    window.show()

    logger.info("Application started")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
