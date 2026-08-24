#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎵 Music Downloader Pro v2.4
现代化音乐下载器 - 多音源并发搜索、实时结果展示、批量下载
"""

import os
import sys
import json
import hashlib
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from datetime import datetime
from typing import Optional, List, Dict
from queue import Queue

import requests
from PyQt5.QtCore import (
    Qt, QThread, QThreadPool, QRunnable, QObject, QTimer,
    QSize, QPoint, QRect, pyqtSignal, QSettings,
)
from PyQt5.QtGui import QFont, QPixmap, QColor, QPainter, QBrush, QIcon, QTextCursor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFrame, QSplitter, QLabel, QLineEdit, QPushButton,
    QCheckBox, QComboBox, QSpinBox, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox, QMenu,
    QAction, QActionGroup, QMenuBar, QDialog, QDialogButtonBox, QGroupBox,
    QPlainTextEdit, QTextEdit, QSizePolicy, QLayout, QStyle,
)

# musicdl 导入
try:
    from musicdl import musicdl
    MUSICDL_AVAILABLE = True
except ImportError:
    MUSICDL_AVAILABLE = False
    print("⚠️ musicdl 未安装，请运行: pip install musicdl")

# ═══════════════════════════════════════════════════════════════════════════════
#                              配置
# ═══════════════════════════════════════════════════════════════════════════════

CACHE_TTL = 600
MAX_WORKERS = 12

SOURCE_MAP = {
    "网易云音乐": "NeteaseMusicClient",
    "QQ音乐": "QQMusicClient",
    "酷我音乐": "KuwoMusicClient",
    "酷狗音乐": "KugouMusicClient",
    "咪咕音乐": "MiguMusicClient",
    "千千音乐": "QianqianMusicClient",
    "汽水音乐": "SodaMusicClient",
    "5sing": "FiveSingMusicClient",
    "苹果音乐": "AppleMusicClient",
    "Spotify": "SpotifyMusicClient",
    "Deezer": "DeezerMusicClient",
    "SoundCloud": "SoundCloudMusicClient",
    "TIDAL": "TIDALMusicClient",
    "Qobuz": "QobuzMusicClient",
    "Jamendo": "JamendoMusicClient",
    "Joox": "JooxMusicClient",
    "StreetVoice": "StreetVoiceMusicClient",
}
SOURCE_MAP_REVERSE = {v: k for k, v in SOURCE_MAP.items()}
DEFAULT_SOURCES = {"网易云音乐", "QQ音乐", "酷我音乐", "酷狗音乐", "咪咕音乐"}

# ═══════════════════════════════════════════════════════════════════════════════
#                              主题样式
# ═══════════════════════════════════════════════════════════════════════════════

DARK_THEME = """
QMainWindow, QWidget, QDialog {
    background-color: #1a1a2e;
    color: #eaeaea;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 10pt;
}
QMenuBar {
    background: #16213e;
    border-bottom: 1px solid #0f3460;
    padding: 4px;
}
QMenuBar::item { padding: 6px 12px; border-radius: 4px; color: #eaeaea; }
QMenuBar::item:selected { background: #0f3460; }
QMenu {
    background: #16213e;
    border: 1px solid #0f3460;
    border-radius: 8px;
    padding: 5px;
}
QMenu::item { padding: 8px 25px; border-radius: 4px; color: #eaeaea; }
QMenu::item:selected { background: #e94560; }
QMenu::separator { height: 1px; background: #0f3460; margin: 5px 10px; }

#SearchBox {
    background: #16213e;
    border: 2px solid #0f3460;
    border-radius: 12px;
    padding: 14px 20px;
    font-size: 14pt;
    color: #eaeaea;
}
#SearchBox:focus { border-color: #e94560; background: #1a1a2e; }

#SearchBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e94560, stop:1 #ff6b6b);
    border: none;
    border-radius: 12px;
    padding: 14px 30px;
    font-size: 12pt;
    font-weight: bold;
    color: white;
}
#SearchBtn:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff6b6b, stop:1 #ee8572); }
#SearchBtn:disabled { background: #0f3460; color: #6a6a8e; }

#CancelBtn {
    background: #533483;
    border: none;
    border-radius: 12px;
    padding: 14px 20px;
    font-size: 11pt;
    color: white;
}
#CancelBtn:hover { background: #6a4c93; }

QPushButton {
    background: #16213e;
    border: 1px solid #0f3460;
    border-radius: 6px;
    padding: 8px 16px;
    color: #eaeaea;
}
QPushButton:hover { background: #0f3460; border-color: #e94560; }
QPushButton:disabled { background: #1a1a2e; color: #6a6a8e; }

#DownloadBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00b4d8, stop:1 #0096c7);
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-weight: bold;
    color: white;
}
#DownloadBtn:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #48cae4, stop:1 #00b4d8); }
#DownloadBtn:disabled { background: #0f3460; color: #6a6a8e; }

QProgressBar {
    background: #16213e;
    border: none;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    color: white;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e94560, stop:1 #ff6b6b);
    border-radius: 6px;
}

QTableWidget {
    background: #1a1a2e;
    alternate-background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 8px;
    gridline-color: #0f3460;
    selection-background-color: #533483;
    color: #eaeaea;
}
QTableWidget::item { padding: 5px; border-bottom: 1px solid #0f3460; color: #eaeaea; }
QTableWidget::item:selected { background: #533483; color: #ffffff; }
QHeaderView::section {
    background: #0f3460;
    color: #00b4d8;
    font-weight: bold;
    padding: 10px 5px;
    border: none;
    border-right: 1px solid #1a1a2e;
    border-bottom: 1px solid #e94560;
}

QCheckBox { color: #eaeaea; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 2px solid #0f3460; background: #1a1a2e; }
QCheckBox::indicator:checked { background: #e94560; border-color: #e94560; }
QCheckBox::indicator:hover { border-color: #e94560; }

QComboBox, QSpinBox {
    background: #16213e;
    border: 1px solid #0f3460;
    border-radius: 6px;
    padding: 6px 10px;
    color: #eaeaea;
    min-width: 80px;
}
QComboBox:focus, QSpinBox:focus { border-color: #e94560; }
QComboBox::drop-down { border: none; padding-right: 8px; }
QComboBox QAbstractItemView { background: #16213e; border: 1px solid #0f3460; selection-background-color: #e94560; color: #eaeaea; }

QGroupBox {
    font-weight: bold;
    border: 1px solid #0f3460;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 10px;
    color: #eaeaea;
}
QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 8px; color: #00b4d8; }

QTextEdit, QPlainTextEdit {
    background: #0f0f1a;
    border: 1px solid #0f3460;
    border-radius: 6px;
    color: #c0c0d0;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 9pt;
    padding: 8px;
}

QScrollBar:vertical { background: #1a1a2e; width: 10px; border-radius: 5px; }
QScrollBar::handle:vertical { background: #0f3460; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #e94560; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #1a1a2e; height: 10px; border-radius: 5px; }
QScrollBar::handle:horizontal { background: #0f3460; border-radius: 5px; min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: #e94560; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

#StatusBar { background: #0f0f1a; border-top: 1px solid #0f3460; padding: 6px 15px; color: #a0a0c0; }
#SourceChip { background: #16213e; border: 1px solid #0f3460; border-radius: 15px; padding: 5px 12px; margin: 2px; color: #eaeaea; }
#SourceChip:checked { background: #e94560; border-color: #e94560; }
#SourceChip:hover { border-color: #e94560; }
QLabel { color: #eaeaea; }
#LogWindow { background: #12121f; border: 1px solid #0f3460; border-radius: 10px; }
#LogTitle { background: #16213e; border-top-left-radius: 10px; border-top-right-radius: 10px; padding: 10px 15px; color: #00b4d8; font-weight: bold; }
"""

LIGHT_THEME = """
QMainWindow, QWidget, QDialog {
    background-color: #f5f5f5;
    color: #333333;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 10pt;
}
QMenuBar { background: #ffffff; border-bottom: 1px solid #e0e0e0; padding: 4px; }
QMenuBar::item { padding: 6px 12px; border-radius: 4px; color: #333333; }
QMenuBar::item:selected { background: #e8f4fd; }
QMenu { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 5px; }
QMenu::item { padding: 8px 25px; border-radius: 4px; color: #333333; }
QMenu::item:selected { background: #1976d2; color: white; }
QMenu::separator { height: 1px; background: #e0e0e0; margin: 5px 10px; }

#SearchBox { background: #ffffff; border: 2px solid #e0e0e0; border-radius: 12px; padding: 14px 20px; font-size: 14pt; color: #333333; }
#SearchBox:focus { border-color: #1976d2; }
#SearchBtn { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1976d2, stop:1 #2196f3); border: none; border-radius: 12px; padding: 14px 30px; font-size: 12pt; font-weight: bold; color: white; }
#SearchBtn:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2196f3, stop:1 #42a5f5); }
#SearchBtn:disabled { background: #bdbdbd; color: #757575; }
#CancelBtn { background: #f44336; border: none; border-radius: 12px; padding: 14px 20px; font-size: 11pt; color: white; }
#CancelBtn:hover { background: #e53935; }

QPushButton { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 8px 16px; color: #333333; }
QPushButton:hover { background: #f5f5f5; border-color: #1976d2; }
QPushButton:disabled { background: #f5f5f5; color: #9e9e9e; }
#DownloadBtn { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4caf50, stop:1 #66bb6a); border: none; border-radius: 8px; padding: 10px 24px; font-weight: bold; color: white; }
#DownloadBtn:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #66bb6a, stop:1 #81c784); }
#DownloadBtn:disabled { background: #bdbdbd; color: #757575; }

QProgressBar { background: #e0e0e0; border: none; border-radius: 6px; height: 12px; text-align: center; color: #333333; }
QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4caf50, stop:1 #81c784); border-radius: 6px; }

QTableWidget { background: #ffffff; alternate-background-color: #fafafa; border: 1px solid #e0e0e0; border-radius: 8px; gridline-color: #eeeeee; selection-background-color: #e3f2fd; color: #333333; }
QTableWidget::item { padding: 5px; border-bottom: 1px solid #eeeeee; color: #333333; }
QTableWidget::item:selected { background: #e3f2fd; color: #1976d2; }
QHeaderView::section { background: #f5f5f5; color: #1976d2; font-weight: bold; padding: 10px 5px; border: none; border-right: 1px solid #e0e0e0; border-bottom: 2px solid #1976d2; }

QCheckBox { color: #333333; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 2px solid #bdbdbd; background: #ffffff; }
QCheckBox::indicator:checked { background: #1976d2; border-color: #1976d2; }
QCheckBox::indicator:hover { border-color: #1976d2; }

QComboBox, QSpinBox { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 6px 10px; color: #333333; min-width: 80px; }
QComboBox:focus, QSpinBox:focus { border-color: #1976d2; }
QComboBox::drop-down { border: none; padding-right: 8px; }
QComboBox QAbstractItemView { background: #ffffff; border: 1px solid #e0e0e0; selection-background-color: #1976d2; color: #333333; }

QGroupBox { font-weight: bold; border: 1px solid #e0e0e0; border-radius: 8px; margin-top: 12px; padding-top: 10px; color: #333333; }
QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 8px; color: #1976d2; }

QTextEdit, QPlainTextEdit { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 6px; color: #424242; font-family: "Cascadia Code", "Consolas", monospace; font-size: 9pt; padding: 8px; }

QScrollBar:vertical { background: #f5f5f5; width: 10px; border-radius: 5px; }
QScrollBar::handle:vertical { background: #bdbdbd; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #9e9e9e; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #f5f5f5; height: 10px; border-radius: 5px; }
QScrollBar::handle:horizontal { background: #bdbdbd; border-radius: 5px; min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: #9e9e9e; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

#StatusBar { background: #ffffff; border-top: 1px solid #e0e0e0; padding: 6px 15px; color: #757575; }
#SourceChip { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 15px; padding: 5px 12px; margin: 2px; color: #333333; }
#SourceChip:checked { background: #1976d2; border-color: #1976d2; color: white; }
#SourceChip:hover { border-color: #1976d2; }
QLabel { color: #333333; }
#LogWindow { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 10px; }
#LogTitle { background: #f5f5f5; border-top-left-radius: 10px; border-top-right-radius: 10px; padding: 10px 15px; color: #1976d2; font-weight: bold; }
"""


# ═══════════════════════════════════════════════════════════════════════════════
#                              工具函数
# ═══════════════════════════════════════════════════════════════════════════════

class ProxyContext:
    def __init__(self, enabled, host, port):
        self.enabled, self.host, self.port = enabled, host, port
        self._old = {}

    def __enter__(self):
        self._old = {k: os.environ.get(k) for k in ('HTTP_PROXY', 'HTTPS_PROXY')}
        if self.enabled:
            proxy = f"http://{self.host}:{self.port}"
            os.environ['HTTP_PROXY'] = os.environ['HTTPS_PROXY'] = proxy
        else:
            os.environ.pop('HTTP_PROXY', None)
            os.environ.pop('HTTPS_PROXY', None)
        return self

    def __exit__(self, *args):
        for k, v in self._old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def get_song_display(song: dict) -> dict:
    if not isinstance(song, dict):
        return {'name': '', 'singer': '', 'album': '', 'format': '', 'size': '', 'duration': '', 'source': '', 'cover': ''}

    singers = song.get('singers', [])
    if isinstance(singers, str):
        singers = [singers]

    cover = ""
    for k in ['cover', 'album_cover', 'pic', 'picture', 'img', 'cover_url', 'pic_url']:
        v = str(song.get(k, ''))
        if v.startswith('http'):
            cover = v
            break

    fmt = ""
    for k in ['format', 'ext', 'file_format', 'type']:
        if song.get(k):
            fmt = str(song.get(k)).upper()
            break
    if not fmt:
        url = str(song.get('download_url', '')).lower()
        for ext in ['flac', 'mp3', 'wav', 'm4a', 'aac']:
            if f'.{ext}' in url:
                fmt = ext.upper()
                break

    return {
        'name': str(song.get('song_name', '')),
        'singer': ', '.join(singers) if singers else '未知',
        'album': str(song.get('album', '')),
        'format': fmt or '未知',
        'size': str(song.get('file_size', '')),
        'duration': str(song.get('duration', '')),
        'source': SOURCE_MAP_REVERSE.get(song.get('source', ''), song.get('source', '')),
        'cover': cover,
    }


def make_song_key(song: dict) -> str:
    if not isinstance(song, dict):
        return str(id(song))
    name = str(song.get('song_name', '')).strip().lower()
    singers = song.get('singers', [])
    if isinstance(singers, list):
        singer = '|'.join(sorted(str(s).strip().lower() for s in singers))
    else:
        singer = str(singers).strip().lower()
    return f"{name}::{singer}::{song.get('duration', '')}"


def ensure_serializable(data):
    if isinstance(data, dict):
        return {k: ensure_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [ensure_serializable(item) for item in data]
    elif isinstance(data, (str, int, float, bool, type(None))):
        return data
    else:
        return str(data)


# ═══════════════════════════════════════════════════════════════════════════════
#                              信号类
# ═══════════════════════════════════════════════════════════════════════════════

class SearchSignals(QObject):
    """搜索信号 - 支持实时结果推送"""
    progress = pyqtSignal(int, int)  # done, total
    log = pyqtSignal(str)
    result = pyqtSignal(str, list)  # source, songs（每个音源完成立即发送）
    finished = pyqtSignal()
    error = pyqtSignal(str)


class DownloadSignals(QObject):
    progress = pyqtSignal(int, int, str)
    log = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)


class ImageSignals(QObject):
    loaded = pyqtSignal(int, QPixmap)
    failed = pyqtSignal(int)


# ═══════════════════════════════════════════════════════════════════════════════
#                      搜索线程（每个音源独立线程，实时回调）
# ═══════════════════════════════════════════════════════════════════════════════

class SourceSearchThread(QThread):
    """单个音源的搜索线程 - 搜索完成立即通知"""
    done = pyqtSignal(str, list, float)  # source, songs, elapsed
    log = pyqtSignal(str)

    def __init__(self, source: str, keyword: str, limit: int, cache_dir: str, proxy_cfg: tuple):
        super().__init__()
        self.source = source
        self.keyword = keyword
        self.limit = limit
        self.cache_dir = cache_dir
        self.proxy_cfg = proxy_cfg
        self._stop = False

    def stop(self):
        self._stop = True
        # 强制终止（musicdl 搜索是阻塞的）
        self.terminate()

    def _cache_path(self):
        key = hashlib.md5(f"{self.source}|{self.keyword}|{self.limit}".encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key}.json")

    def _load_cache(self):
        path = self._cache_path()
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if time.time() - datetime.fromisoformat(data['ts']).timestamp() > CACHE_TTL:
                return None
            return data.get('songs', [])
        except:
            return None

    def _save_cache(self, songs):
        os.makedirs(self.cache_dir, exist_ok=True)
        try:
            with open(self._cache_path(), 'w', encoding='utf-8') as f:
                json.dump({'ts': datetime.now().isoformat(), 'songs': ensure_serializable(songs)}, f, ensure_ascii=False)
        except Exception as e:
            self.log.emit(f"⚠️ 缓存写入失败: {e}")

    def run(self):
        if self._stop:
            return

        source_cn = SOURCE_MAP_REVERSE.get(self.source, self.source)
        t0 = time.time()

        # 检查缓存
        cached = self._load_cache()
        if cached is not None:
            self.log.emit(f"💾 {source_cn} 缓存命中 ({len(cached)}首)")
            self.done.emit(self.source, cached, time.time() - t0)
            return

        self.log.emit(f"🔍 {source_cn} 搜索中...")

        try:
            with ProxyContext(*self.proxy_cfg):
                client = musicdl.MusicClient(
                    music_sources=[self.source],
                    init_music_clients_cfg={self.source: {
                        'search_size_per_source': self.limit,
                        'work_dir': self.cache_dir,
                    }}
                )
                result = client.search(keyword=self.keyword)

                # 提取歌曲列表
                songs = []
                if isinstance(result, dict):
                    for key, value in result.items():
                        if isinstance(value, list):
                            songs.extend(value)
                            self.log.emit(f"   📂 {key}: {len(value)} 首")
                elif isinstance(result, list):
                    songs = result

                # 清理数据 - 支持 SongInfo 对象和字典
                clean_songs = []
                for s in songs:
                    try:
                        # 如果是 SongInfo 对象，转换为字典
                        if hasattr(s, 'todict'):
                            song_dict = s.todict()
                        elif isinstance(s, dict):
                            song_dict = s
                        else:
                            continue
                        
                        # 确保有歌曲名
                        if song_dict.get('song_name'):
                            clean_songs.append(ensure_serializable(song_dict))
                    except Exception as e:
                        self.log.emit(f"   ⚠️ 转换失败: {e}")

                if clean_songs:
                    self._save_cache(clean_songs)

                elapsed = time.time() - t0
                self.log.emit(f"✅ {source_cn} 完成: {len(clean_songs)}首 ({elapsed:.1f}s)")
                self.done.emit(self.source, clean_songs, elapsed)

        except Exception as e:
            import traceback
            elapsed = time.time() - t0
            self.log.emit(f"❌ {source_cn} 失败: {e}")
            self.done.emit(self.source, [], elapsed)


class SearchManager(QObject):
    """搜索管理器 - 管理多个并行搜索线程"""
    progress = pyqtSignal(int, int)
    log = pyqtSignal(str)
    result = pyqtSignal(str, list)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._threads: List[SourceSearchThread] = []
        self._total = 0
        self._done = 0

    def start_search(self, keyword: str, sources: list, limit: int, cache_dir: str, proxy_cfg: tuple):
        """启动并行搜索"""
        self.stop()  # 停止之前的搜索

        self._total = len(sources)
        self._done = 0
        self._threads = []

        self.log.emit(f"🚀 开始并行搜索 {self._total} 个音源")

        for source in sources:
            thread = SourceSearchThread(source, keyword, limit, cache_dir, proxy_cfg)
            thread.done.connect(self._on_source_done)
            thread.log.connect(self.log.emit)
            self._threads.append(thread)
            thread.start()  # 立即启动

    def _on_source_done(self, source: str, songs: list, elapsed: float):
        """单个音源搜索完成"""
        self._done += 1

        # 始终发送结果到 UI（即使为空，让 UI 知道进度）
        self.result.emit(source, songs)

        self.progress.emit(self._done, self._total)

        # 检查是否全部完成
        if self._done >= self._total:
            self.finished.emit()

    def stop(self):
        """停止所有搜索"""
        for t in self._threads:
            if t.isRunning():
                t.stop()  # 会调用 terminate()
        self._threads.clear()
        self._done = self._total  # 标记为完成

    def is_running(self) -> bool:
        return any(t.isRunning() for t in self._threads)


class DownloadWorker(QThread):
    def __init__(self, songs, download_dir, proxy_cfg):
        super().__init__()
        self.songs = songs
        self.download_dir = download_dir
        self.proxy_cfg = proxy_cfg
        self.signals = DownloadSignals()
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        if not MUSICDL_AVAILABLE:
            self.signals.error.emit("musicdl 未安装")
            return

        try:
            # 导入 SongInfo 类
            from musicdl.modules.utils.data import SongInfo
            
            with ProxyContext(*self.proxy_cfg):
                sources = list(set(s.get('source', '') for s in self.songs if isinstance(s, dict) and s.get('source')))
                client = musicdl.MusicClient(
                    music_sources=sources,
                    init_music_clients_cfg={src: {'work_dir': self.download_dir} for src in sources}
                )

                total = len(self.songs)
                success = 0

                for i, song in enumerate(self.songs, 1):
                    if self._stop:
                        break

                    if not isinstance(song, dict):
                        continue

                    name = song.get('song_name', '未知')
                    self.signals.progress.emit(i, total, name)
                    self.signals.log.emit(f"⬇️ 下载: {name}")

                    try:
                        # 将字典转换回 SongInfo 对象
                        song_info = SongInfo.fromdict(song)
                        song_info.work_dir = self.download_dir
                        client.download(song_infos=[song_info])
                        success += 1
                        self.signals.log.emit(f"✅ 完成: {name}")
                    except Exception as e:
                        self.signals.log.emit(f"❌ 失败: {name} - {e}")

                self.signals.log.emit(f"📦 下载完成: {success}/{total}")
                self.signals.finished.emit()

        except Exception as e:
            self.signals.error.emit(str(e))


class ImageTask(QRunnable):
    def __init__(self, row, url, signals):
        super().__init__()
        self.row, self.url, self.signals = row, url, signals

    def run(self):
        try:
            if not self.url:
                self.signals.failed.emit(self.row)
                return
            resp = requests.get(self.url, timeout=5)
            if resp.status_code == 200:
                pix = QPixmap()
                if pix.loadFromData(resp.content):
                    self.signals.loaded.emit(self.row, pix.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    return
            self.signals.failed.emit(self.row)
        except:
            self.signals.failed.emit(self.row)


# ═══════════════════════════════════════════════════════════════════════════════
#                              流式布局
# ═══════════════════════════════════════════════════════════════════════════════

class FlowLayout(QLayout):
    def __init__(self, parent=None, spacing=8):
        super().__init__(parent)
        self._items = []
        self._spacing = spacing

    def addItem(self, item): self._items.append(item)
    def count(self): return len(self._items)
    def itemAt(self, i): return self._items[i] if 0 <= i < len(self._items) else None
    def takeAt(self, i): return self._items.pop(i) if 0 <= i < len(self._items) else None
    def hasHeightForWidth(self): return True
    def heightForWidth(self, w): return self._layout(QRect(0, 0, w, 0), True)
    def setGeometry(self, r): super().setGeometry(r); self._layout(r, False)
    def sizeHint(self): return self.minimumSize()
    def minimumSize(self):
        s = QSize()
        for item in self._items: s = s.expandedTo(item.minimumSize())
        return s

    def _layout(self, rect, test):
        x, y, h = rect.x(), rect.y(), 0
        for item in self._items:
            sz = item.sizeHint()
            if x + sz.width() > rect.right() and h > 0:
                x, y = rect.x(), y + h + self._spacing
                h = 0
            if not test: item.setGeometry(QRect(QPoint(x, y), sz))
            x += sz.width() + self._spacing
            h = max(h, sz.height())
        return y + h - rect.y()


# ═══════════════════════════════════════════════════════════════════════════════
#                              日志窗口
# ═══════════════════════════════════════════════════════════════════════════════

class LogWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("📋 详细日志")
        self.setObjectName("LogWindow")
        self.resize(600, 400)
        self.setMinimumSize(400, 250)

        self._settings = QSettings("MusicDownloaderPro", "LogWindow")
        geo = self._settings.value("geometry")
        if geo: self.restoreGeometry(geo)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title_bar = QWidget()
        title_bar.setObjectName("LogTitle")
        title_bar.setFixedHeight(40)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 10, 0)
        title_layout.addWidget(QLabel("📋 详细日志"))
        title_layout.addStretch()

        self._auto_scroll = QCheckBox("自动滚动")
        self._auto_scroll.setChecked(True)
        title_layout.addWidget(self._auto_scroll)

        clear_btn = QPushButton("清空")
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(lambda: self._log_area.clear())
        title_layout.addWidget(clear_btn)
        layout.addWidget(title_bar)

        self._log_area = QTextEdit()
        self._log_area.setReadOnly(True)
        self._log_area.setStyleSheet("border: none; border-radius: 0;")
        layout.addWidget(self._log_area)

    def append_log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        if "✅" in msg or "完成" in msg: color = "#4ade80"
        elif "❌" in msg or "失败" in msg: color = "#f87171"
        elif "⚠️" in msg: color = "#fbbf24"
        elif "🔍" in msg: color = "#60a5fa"
        elif "💾" in msg: color = "#a78bfa"
        elif "⬇️" in msg: color = "#22d3ee"
        elif "🚀" in msg: color = "#fb923c"
        else: color = "#94a3b8"

        self._log_area.append(f'<span style="color: #6b7280;">[{ts}]</span> <span style="color: {color};">{msg}</span>')
        if self._auto_scroll.isChecked():
            cursor = self._log_area.textCursor()
            cursor.movePosition(QTextCursor.End)
            self._log_area.setTextCursor(cursor)

    def closeEvent(self, event):
        self._settings.setValue("geometry", self.saveGeometry())
        self.hide()
        event.ignore()


# ═══════════════════════════════════════════════════════════════════════════════
#                              对话框
# ═══════════════════════════════════════════════════════════════════════════════

class SettingsDialog(QDialog):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.setWindowTitle("⚙️ 设置")
        self.setFixedSize(500, 400)
        self.config = config
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        dl_group = QGroupBox("下载设置")
        dl_layout = QGridLayout(dl_group)
        dl_layout.addWidget(QLabel("下载目录:"), 0, 0)
        self.dir_edit = QLineEdit(config.get('download_dir', ''))
        self.dir_edit.setReadOnly(True)
        dl_layout.addWidget(self.dir_edit, 0, 1)
        browse_btn = QPushButton("选择...")
        browse_btn.clicked.connect(self._browse_dir)
        dl_layout.addWidget(browse_btn, 0, 2)
        dl_layout.addWidget(QLabel("单源结果数:"), 1, 0)
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 100)
        self.limit_spin.setValue(config.get('limit', 15))
        dl_layout.addWidget(self.limit_spin, 1, 1)
        layout.addWidget(dl_group)

        proxy_group = QGroupBox("代理设置")
        proxy_layout = QGridLayout(proxy_group)
        self.proxy_check = QCheckBox("启用代理")
        self.proxy_check.setChecked(config.get('proxy_enabled', False))
        proxy_layout.addWidget(self.proxy_check, 0, 0, 1, 3)
        proxy_layout.addWidget(QLabel("地址:"), 1, 0)
        self.proxy_host = QLineEdit(config.get('proxy_host', '127.0.0.1'))
        proxy_layout.addWidget(self.proxy_host, 1, 1)
        proxy_layout.addWidget(QLabel("端口:"), 2, 0)
        self.proxy_port = QSpinBox()
        self.proxy_port.setRange(1, 65535)
        self.proxy_port.setValue(config.get('proxy_port', 7890))
        proxy_layout.addWidget(self.proxy_port, 2, 1)
        layout.addWidget(proxy_group)

        cache_group = QGroupBox("缓存")
        cache_layout = QHBoxLayout(cache_group)
        clear_btn = QPushButton("🗑️ 清除搜索缓存")
        clear_btn.clicked.connect(self._clear_cache)
        cache_layout.addWidget(clear_btn)
        cache_layout.addStretch()
        layout.addWidget(cache_group)
        layout.addStretch()

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _browse_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择下载目录")
        if path: self.dir_edit.setText(path)

    def _clear_cache(self):
        cache_dir = self.config.get('cache_dir', '')
        if os.path.exists(cache_dir):
            count = sum(1 for f in os.listdir(cache_dir) if os.remove(os.path.join(cache_dir, f)) or True)
            QMessageBox.information(self, "完成", f"已清除缓存")

    def get_config(self):
        return {
            'download_dir': self.dir_edit.text(), 'limit': self.limit_spin.value(),
            'proxy_enabled': self.proxy_check.isChecked(), 'proxy_host': self.proxy_host.text(),
            'proxy_port': self.proxy_port.value(), 'cache_dir': self.config.get('cache_dir', ''),
        }


class SourceDialog(QDialog):
    def __init__(self, parent, selected):
        super().__init__(parent)
        self.setWindowTitle("🎵 选择音源")
        self.setFixedSize(550, 380)
        layout = QVBoxLayout(self)

        btn_row = QHBoxLayout()
        all_btn = QPushButton("全选"); all_btn.clicked.connect(lambda: self._toggle(True))
        none_btn = QPushButton("全不选"); none_btn.clicked.connect(lambda: self._toggle(False))
        cn_btn = QPushButton("国内源"); cn_btn.clicked.connect(self._select_cn)
        btn_row.addWidget(all_btn); btn_row.addWidget(none_btn); btn_row.addWidget(cn_btn); btn_row.addStretch()
        layout.addLayout(btn_row)

        self.checkboxes = {}
        source_widget = QWidget()
        source_layout = FlowLayout(source_widget, spacing=10)
        for name in SOURCE_MAP.keys():
            cb = QCheckBox(name); cb.setObjectName("SourceChip"); cb.setChecked(name in selected)
            self.checkboxes[name] = cb; source_layout.addWidget(cb)
        layout.addWidget(source_widget, 1)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _toggle(self, state):
        for cb in self.checkboxes.values(): cb.setChecked(state)

    def _select_cn(self):
        cn = {"网易云音乐", "QQ音乐", "酷我音乐", "酷狗音乐", "咪咕音乐", "千千音乐", "汽水音乐", "5sing"}
        for name, cb in self.checkboxes.items(): cb.setChecked(name in cn)

    def get_selected(self): return {name for name, cb in self.checkboxes.items() if cb.isChecked()}


# ═══════════════════════════════════════════════════════════════════════════════
#                              主窗口
# ═══════════════════════════════════════════════════════════════════════════════

class MusicDownloaderPro(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎵 Music Downloader Pro")
        self.resize(1300, 800)
        self.setMinimumSize(1000, 600)

        self._settings = QSettings("MusicDownloaderPro", "Settings")
        base = os.getcwd()
        self._config = {
            'download_dir': os.path.join(base, "下载音乐"),
            'cache_dir': os.path.join(base, "搜索缓存"),
            'limit': 15, 'proxy_enabled': False, 'proxy_host': '127.0.0.1', 'proxy_port': 7890,
        }
        self._selected_sources = DEFAULT_SOURCES.copy()
        self._theme = self._settings.value("theme", "dark")

        os.makedirs(self._config['download_dir'], exist_ok=True)
        os.makedirs(self._config['cache_dir'], exist_ok=True)

        self._songs = {}
        self._seen = set()
        self._download_worker = None

        # 搜索管理器（并行搜索）
        self._search_manager = SearchManager()
        self._search_manager.progress.connect(self._on_search_progress)
        self._search_manager.log.connect(self._log)
        self._search_manager.result.connect(self._on_search_result)
        self._search_manager.finished.connect(self._on_search_done)

        self._img_pool = QThreadPool.globalInstance()
        self._img_pool.setMaxThreadCount(8)
        self._img_signals = ImageSignals()
        self._img_signals.loaded.connect(self._on_img_loaded)
        self._img_signals.failed.connect(lambda r: None)
        self._img_cache = {}

        self._log_window = LogWindow(self)
        self._setup_ui()
        self._apply_theme()
        self._log("🎵 Music Downloader Pro v2.4 启动")

    def _setup_ui(self):
        self._create_menu()
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 15, 20, 10)
        layout.setSpacing(12)

        layout.addLayout(self._create_search_bar())
        layout.addLayout(self._create_toolbar())

        self._progress = QProgressBar()
        self._progress.setFixedHeight(14)
        self._progress.setTextVisible(False)
        layout.addWidget(self._progress)

        layout.addWidget(self._create_table(), 1)
        layout.addWidget(self._create_status_bar())

    def _create_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件")
        source_action = QAction("🎵 选择音源...", self); source_action.setShortcut("Ctrl+E"); source_action.triggered.connect(self._open_source_dialog)
        file_menu.addAction(source_action)
        settings_action = QAction("⚙️ 设置...", self); settings_action.setShortcut("Ctrl+,"); settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)
        file_menu.addSeparator()
        open_dir_action = QAction("📁 打开下载目录", self); open_dir_action.triggered.connect(self._open_download_dir)
        file_menu.addAction(open_dir_action)
        open_cache_action = QAction("📂 打开缓存目录", self); open_cache_action.triggered.connect(self._open_cache_dir)
        file_menu.addAction(open_cache_action)
        file_menu.addSeparator()
        
        # 清理菜单
        clean_menu = file_menu.addMenu("🗑️ 清理")
        clear_cache_action = QAction("清除搜索缓存", self); clear_cache_action.triggered.connect(self._clear_cache)
        clean_menu.addAction(clear_cache_action)
        clear_download_action = QAction("清除下载音乐", self); clear_download_action.triggered.connect(self._clear_downloads)
        clean_menu.addAction(clear_download_action)
        clean_menu.addSeparator()
        clear_all_action = QAction("清除全部", self); clear_all_action.triggered.connect(self._clear_all)
        clean_menu.addAction(clear_all_action)
        
        file_menu.addSeparator()
        exit_action = QAction("退出", self); exit_action.setShortcut("Ctrl+Q"); exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("视图")
        theme_menu = view_menu.addMenu("🎨 主题")
        theme_group = QActionGroup(self)
        dark_action = QAction("🌙 深色模式", self, checkable=True); dark_action.setChecked(self._theme == "dark"); dark_action.triggered.connect(lambda: self._set_theme("dark"))
        theme_group.addAction(dark_action); theme_menu.addAction(dark_action)
        light_action = QAction("☀️ 浅色模式", self, checkable=True); light_action.setChecked(self._theme == "light"); light_action.triggered.connect(lambda: self._set_theme("light"))
        theme_group.addAction(light_action); theme_menu.addAction(light_action)
        view_menu.addSeparator()
        log_action = QAction("📋 显示日志窗口", self); log_action.setShortcut("Ctrl+L"); log_action.triggered.connect(self._show_log_window)
        view_menu.addAction(log_action)

        edit_menu = menubar.addMenu("编辑")
        select_all = QAction("全选结果", self); select_all.setShortcut("Ctrl+A"); select_all.triggered.connect(lambda: self._toggle_selection(True))
        edit_menu.addAction(select_all)
        deselect_all = QAction("取消全选", self); deselect_all.triggered.connect(lambda: self._toggle_selection(False))
        edit_menu.addAction(deselect_all)
        edit_menu.addSeparator()
        clear_action = QAction("清空结果", self); clear_action.triggered.connect(self._clear_results)
        edit_menu.addAction(clear_action)

        help_menu = menubar.addMenu("帮助")
        about_action = QAction("关于", self); about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_search_bar(self):
        layout = QHBoxLayout(); layout.setSpacing(12)
        self._search_input = QLineEdit(); self._search_input.setObjectName("SearchBox")
        self._search_input.setPlaceholderText("🔍 输入歌曲名、歌手...")
        self._search_input.returnPressed.connect(self._on_search)

        self._search_btn = QPushButton("搜 索"); self._search_btn.setObjectName("SearchBtn")
        self._search_btn.setFixedSize(100, 50); self._search_btn.clicked.connect(self._on_search)

        self._cancel_btn = QPushButton("取消"); self._cancel_btn.setObjectName("CancelBtn")
        self._cancel_btn.setFixedSize(80, 50); self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._on_cancel_search)

        layout.addWidget(self._search_input, 1); layout.addWidget(self._search_btn); layout.addWidget(self._cancel_btn)
        return layout

    def _create_toolbar(self):
        layout = QHBoxLayout(); layout.setSpacing(10)

        self._source_label = QLabel(); self._update_source_label()
        layout.addWidget(self._source_label)

        source_btn = QPushButton("选择音源..."); source_btn.clicked.connect(self._open_source_dialog)
        layout.addWidget(source_btn); layout.addStretch()

        self._count_label = QLabel("结果: 0 首"); self._count_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self._count_label); layout.addSpacing(15)

        select_btn = QPushButton("全选"); select_btn.clicked.connect(lambda: self._toggle_selection(True))
        layout.addWidget(select_btn)
        deselect_btn = QPushButton("取消"); deselect_btn.clicked.connect(lambda: self._toggle_selection(False))
        layout.addWidget(deselect_btn); layout.addSpacing(15)

        layout.addWidget(QLabel("范围:"))
        self._scope_combo = QComboBox(); self._scope_combo.addItems(["全部", "已勾选", "未勾选"])
        layout.addWidget(self._scope_combo)

        self._dl_btn = QPushButton("⬇️ 下载"); self._dl_btn.setObjectName("DownloadBtn")
        self._dl_btn.setEnabled(False); self._dl_btn.clicked.connect(self._on_download)
        layout.addWidget(self._dl_btn)

        self._cancel_dl_btn = QPushButton("取消"); self._cancel_dl_btn.setEnabled(False)
        self._cancel_dl_btn.clicked.connect(self._on_cancel_download)
        layout.addWidget(self._cancel_dl_btn)
        return layout

    def _create_table(self):
        self._table = QTableWidget()
        self._table.setColumnCount(9)
        self._table.setHorizontalHeaderLabels(["", "封面", "歌曲", "歌手", "专辑", "格式", "大小", "时长", "来源"])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_ctx_menu)

        self._table.setColumnWidth(0, 35); self._table.setColumnWidth(1, 60)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self._table.setColumnWidth(3, 130)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        self._table.setColumnWidth(5, 60); self._table.setColumnWidth(6, 70)
        self._table.setColumnWidth(7, 65); self._table.setColumnWidth(8, 80)
        self._table.verticalHeader().setDefaultSectionSize(55)
        return self._table

    def _create_status_bar(self):
        bar = QWidget(); bar.setObjectName("StatusBar")
        layout = QHBoxLayout(bar); layout.setContentsMargins(10, 5, 10, 5)
        self._status_label = QLabel("就绪"); layout.addWidget(self._status_label); layout.addStretch()
        log_btn = QPushButton("📋 详细日志"); log_btn.clicked.connect(self._show_log_window)
        layout.addWidget(log_btn)
        return bar

    def _show_log_window(self):
        if self._log_window.isVisible():
            self._log_window.raise_(); self._log_window.activateWindow()
        else:
            main_geo = self.geometry()
            self._log_window.move(main_geo.right() + 10, main_geo.top())
            self._log_window.show()

    def _apply_theme(self):
        style = DARK_THEME if self._theme == "dark" else LIGHT_THEME
        self.setStyleSheet(style); self._log_window.setStyleSheet(style)

    def _set_theme(self, theme):
        self._theme = theme; self._settings.setValue("theme", theme); self._apply_theme()
        self._log(f"🎨 已切换到{'深色' if theme == 'dark' else '浅色'}主题")

    def _update_source_label(self):
        n = len(self._selected_sources)
        names = ', '.join(list(self._selected_sources)[:3])
        if n > 3: names += f" +{n-3}"
        self._source_label.setText(f"🎵 音源: {names} ({n}个)")

    def _log(self, msg): self._log_window.append_log(msg)
    def _set_status(self, msg): self._status_label.setText(msg)

    def _open_settings(self):
        dlg = SettingsDialog(self, self._config)
        if dlg.exec_() == QDialog.Accepted:
            self._config.update(dlg.get_config())
            os.makedirs(self._config['download_dir'], exist_ok=True)
            self._log("⚙️ 设置已更新")

    def _open_source_dialog(self):
        dlg = SourceDialog(self, self._selected_sources)
        if dlg.exec_() == QDialog.Accepted:
            self._selected_sources = dlg.get_selected()
            self._update_source_label()
            self._log(f"🎵 已选择 {len(self._selected_sources)} 个音源")

    def _open_download_dir(self):
        path = self._config['download_dir']
        if sys.platform == 'win32': os.startfile(path)
        elif sys.platform == 'darwin': os.system(f'open "{path}"')
        else: os.system(f'xdg-open "{path}"')

    def _open_cache_dir(self):
        path = self._config['cache_dir']
        if sys.platform == 'win32': os.startfile(path)
        elif sys.platform == 'darwin': os.system(f'open "{path}"')
        else: os.system(f'xdg-open "{path}"')

    def _clear_cache(self):
        """清除搜索缓存（包括文件夹）"""
        import shutil
        cache_dir = self._config['cache_dir']
        
        if not os.path.exists(cache_dir):
            QMessageBox.information(self, "提示", "缓存目录不存在")
            return
        
        reply = QMessageBox.question(self, "确认", f"确定删除缓存目录?\n\n{cache_dir}")
        if reply != QMessageBox.Yes:
            return
        
        try:
            shutil.rmtree(cache_dir)
            self._log(f"🗑️ 已删除缓存目录: {cache_dir}")
            QMessageBox.information(self, "完成", "缓存目录已删除")
        except Exception as e:
            self._log(f"❌ 删除失败: {e}")
            QMessageBox.warning(self, "错误", f"删除失败: {e}")

    def _clear_downloads(self):
        """清除下载的音乐（包括文件夹）"""
        import shutil
        dl_dir = self._config['download_dir']
        
        if not os.path.exists(dl_dir):
            QMessageBox.information(self, "提示", "下载目录不存在")
            return
        
        # 统计文件数
        files = []
        for root, dirs, filenames in os.walk(dl_dir):
            for f in filenames:
                files.append(os.path.join(root, f))
        
        reply = QMessageBox.warning(self, "警告", 
            f"确定删除下载目录?\n\n{dl_dir}\n\n包含 {len(files)} 个文件\n\n此操作不可恢复!",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        
        try:
            shutil.rmtree(dl_dir)
            self._log(f"🗑️ 已删除下载目录: {dl_dir}")
            QMessageBox.information(self, "完成", "下载目录已删除")
        except Exception as e:
            self._log(f"❌ 删除失败: {e}")
            QMessageBox.warning(self, "错误", f"删除失败: {e}")

    def _clear_all(self):
        """清除全部（缓存+下载文件夹）"""
        import shutil
        
        reply = QMessageBox.warning(self, "警告", 
            "确定删除全部数据目录?\n\n包括:\n• 搜索缓存目录\n• 下载音乐目录\n\n此操作不可恢复!",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        
        deleted = []
        
        # 删除缓存目录
        cache_dir = self._config['cache_dir']
        if os.path.exists(cache_dir):
            try:
                shutil.rmtree(cache_dir)
                deleted.append("缓存目录")
            except: pass
        
        # 删除下载目录
        dl_dir = self._config['download_dir']
        if os.path.exists(dl_dir):
            try:
                shutil.rmtree(dl_dir)
                deleted.append("下载目录")
            except: pass
        
        if deleted:
            self._log(f"🗑️ 已删除: {', '.join(deleted)}")
            QMessageBox.information(self, "完成", f"已删除:\n• " + "\n• ".join(deleted))
        else:
            QMessageBox.information(self, "提示", "没有需要删除的目录")

    def _show_about(self):
        QMessageBox.about(self, "关于",
            "🎵 Music Downloader Pro v2.4\n\n"
            "⚡ 真正的并行搜索 - 每个音源独立线程\n"
            "📺 实时结果渲染 - 有结果立即显示\n"
            "🎨 支持主题切换\n\n"
            "基于 musicdl 开发")

    # ═══════════════════════════ 搜索 ═══════════════════════════

    def _on_search(self):
        if self._search_manager.is_running():
            return

        keyword = self._search_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入搜索关键词"); return
        if not self._selected_sources:
            QMessageBox.warning(self, "提示", "请先选择音源"); return

        self._clear_results()
        self._show_log_window()

        sources = [SOURCE_MAP[n] for n in self._selected_sources]
        proxy_cfg = (self._config['proxy_enabled'], self._config['proxy_host'], self._config['proxy_port'])

        self._search_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._progress.setValue(0)
        self._set_status("搜索中...")
        self._log(f"🔍 搜索: {keyword}")

        # 启动并行搜索
        self._search_manager.start_search(keyword, sources, self._config['limit'], self._config['cache_dir'], proxy_cfg)

    def _on_cancel_search(self):
        self._search_manager.stop()
        self._log("⏹️ 已取消搜索")
        self._search_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._set_status("已取消")

    def _on_search_progress(self, done, total):
        self._progress.setValue(int(done * 100 / total))
        self._set_status(f"搜索中: {done}/{total} 音源")

    def _on_search_result(self, source, songs):
        """实时接收搜索结果并渲染"""
        source_cn = SOURCE_MAP_REVERSE.get(source, source)
        self._log(f"📥 收到 {source_cn} 结果: {len(songs)} 首")
        
        added = 0
        for song in songs:
            if not isinstance(song, dict): continue
            key = make_song_key(song)
            if key in self._seen: continue
            self._seen.add(key)
            self._add_row(song)
            added += 1

        if added > 0:
            self._log(f"   ➕ 添加 {added} 首新歌曲")
        
        self._count_label.setText(f"结果: {self._table.rowCount()} 首")
        self._dl_btn.setEnabled(self._table.rowCount() > 0)

    def _on_search_done(self):
        self._search_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._progress.setValue(100)
        n = self._table.rowCount()
        self._set_status(f"搜索完成: {n} 首")
        self._log(f"🎉 搜索完成: 共 {n} 首歌曲")

    def _add_row(self, song):
        row = self._table.rowCount()
        self._table.setRowCount(row + 1)
        self._songs[row] = song
        info = get_song_display(song)

        cb = QCheckBox()
        cb_widget = QWidget()
        cb_layout = QHBoxLayout(cb_widget); cb_layout.setContentsMargins(0, 0, 0, 0); cb_layout.setAlignment(Qt.AlignCenter)
        cb_layout.addWidget(cb)
        self._table.setCellWidget(row, 0, cb_widget)

        cover_label = QLabel("🎵"); cover_label.setAlignment(Qt.AlignCenter); cover_label.setStyleSheet("font-size: 18px;")
        self._table.setCellWidget(row, 1, cover_label)

        if info['cover']:
            if info['cover'] in self._img_cache:
                self._on_img_loaded(row, self._img_cache[info['cover']])
            else:
                self._img_pool.start(ImageTask(row, info['cover'], self._img_signals))

        for col, key in enumerate(['name', 'singer', 'album', 'format', 'size', 'duration', 'source'], 2):
            item = QTableWidgetItem(info[key]); item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, col, item)

    def _on_img_loaded(self, row, pix):
        if row < self._table.rowCount():
            song = self._songs.get(row)
            if song and isinstance(song, dict):
                info = get_song_display(song)
                if info['cover']: self._img_cache[info['cover']] = pix
            label = QLabel(); label.setAlignment(Qt.AlignCenter); label.setPixmap(pix)
            self._table.setCellWidget(row, 1, label)

    # ═══════════════════════════ 下载 ═══════════════════════════

    def _on_download(self):
        if self._download_worker and self._download_worker.isRunning(): return
        songs = self._get_songs_by_scope()
        if not songs:
            QMessageBox.warning(self, "提示", "没有可下载的歌曲"); return
        if QMessageBox.question(self, "确认", f"确定下载 {len(songs)} 首歌曲?\n\n目录: {self._config['download_dir']}") != QMessageBox.Yes:
            return

        self._show_log_window()
        proxy_cfg = (self._config['proxy_enabled'], self._config['proxy_host'], self._config['proxy_port'])
        self._download_worker = DownloadWorker(songs, self._config['download_dir'], proxy_cfg)
        self._download_worker.signals.progress.connect(self._on_dl_progress)
        self._download_worker.signals.log.connect(self._log)
        self._download_worker.signals.finished.connect(self._on_dl_done)
        self._download_worker.signals.error.connect(self._on_dl_error)

        self._dl_btn.setEnabled(False); self._cancel_dl_btn.setEnabled(True)
        self._progress.setValue(0); self._set_status("下载中...")
        self._log(f"⬇️ 开始下载 {len(songs)} 首")
        self._download_worker.start()

    def _on_cancel_download(self):
        if self._download_worker: self._download_worker.stop()
        self._log("⏹️ 正在取消下载...")

    def _on_dl_progress(self, done, total, name):
        self._progress.setValue(int(done * 100 / total))
        self._set_status(f"下载: {done}/{total} - {name}")

    def _on_dl_done(self):
        self._dl_btn.setEnabled(True); self._cancel_dl_btn.setEnabled(False)
        self._progress.setValue(100); self._set_status("下载完成")
        QMessageBox.information(self, "完成", f"下载完成!\n\n目录: {self._config['download_dir']}")

    def _on_dl_error(self, err):
        self._dl_btn.setEnabled(True); self._cancel_dl_btn.setEnabled(False)
        self._set_status("下载失败"); QMessageBox.critical(self, "错误", err)

    def _get_songs_by_scope(self):
        scope = self._scope_combo.currentText()
        songs = []
        for row in range(self._table.rowCount()):
            w = self._table.cellWidget(row, 0)
            if not w: continue
            cb = w.findChild(QCheckBox)
            checked = cb.isChecked() if cb else False
            if scope == "全部" or (scope == "已勾选" and checked) or (scope == "未勾选" and not checked):
                if row in self._songs and isinstance(self._songs[row], dict):
                    songs.append(self._songs[row])
        return songs

    def _toggle_selection(self, state):
        for row in range(self._table.rowCount()):
            w = self._table.cellWidget(row, 0)
            if w:
                cb = w.findChild(QCheckBox)
                if cb: cb.setChecked(state)

    def _clear_results(self):
        self._table.setRowCount(0); self._songs.clear(); self._seen.clear()
        self._count_label.setText("结果: 0 首"); self._dl_btn.setEnabled(False)

    def _show_ctx_menu(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        row = item.row(); song = self._songs.get(row)
        if not song or not isinstance(song, dict): return

        menu = QMenu(self)
        dl_action = QAction(f"⬇️ 下载: {song.get('song_name', '')[:20]}", self)
        dl_action.triggered.connect(lambda: self._download_single(song))
        menu.addAction(dl_action); menu.addSeparator()
        menu.addAction(QAction("全选", self, triggered=lambda: self._toggle_selection(True)))
        menu.addAction(QAction("取消全选", self, triggered=lambda: self._toggle_selection(False)))
        menu.exec_(self._table.mapToGlobal(pos))

    def _download_single(self, song):
        if self._download_worker and self._download_worker.isRunning():
            QMessageBox.warning(self, "提示", "下载任务进行中"); return
        self._show_log_window()
        proxy_cfg = (self._config['proxy_enabled'], self._config['proxy_host'], self._config['proxy_port'])
        self._download_worker = DownloadWorker([song], self._config['download_dir'], proxy_cfg)
        self._download_worker.signals.progress.connect(self._on_dl_progress)
        self._download_worker.signals.log.connect(self._log)
        self._download_worker.signals.finished.connect(self._on_dl_done)
        self._download_worker.signals.error.connect(self._on_dl_error)
        self._dl_btn.setEnabled(False); self._cancel_dl_btn.setEnabled(True)
        self._log(f"⬇️ 下载: {song.get('song_name', '')}")
        self._download_worker.start()

    def closeEvent(self, event):
        self._search_manager.stop()
        self._log_window.close()
        event.accept()


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    win = MusicDownloaderPro()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
