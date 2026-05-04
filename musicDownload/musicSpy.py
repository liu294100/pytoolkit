import os
import sys
import threading
import json
import hashlib
import shutil
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime

import requests
from PyQt5.QtCore import (
    QObject,
    QPoint,
    QRect,
    QRunnable,
    QSize,
    Qt,
    QThread,
    QThreadPool,
    pyqtSignal,
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QComboBox,
    QDockWidget,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLayout,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

try:
    from musicdl import musicdl

    MUSICDL_AVAILABLE = True
except ImportError:
    MUSICDL_AVAILABLE = False
    print("警告：musicdl 库未安装，请运行 pip install musicdl")


SEARCH_CACHE_TTL_SECONDS = 600


class ProxyEnv:
    def __init__(self, enabled, host, port):
        self.enabled = enabled
        self.host = host
        self.port = port
        self._old_http = None
        self._old_https = None

    def __enter__(self):
        self._old_http = os.environ.get("HTTP_PROXY")
        self._old_https = os.environ.get("HTTPS_PROXY")
        if self.enabled:
            proxy_url = f"http://{self.host}:{self.port}"
            os.environ["HTTP_PROXY"] = proxy_url
            os.environ["HTTPS_PROXY"] = proxy_url
        else:
            os.environ.pop("HTTP_PROXY", None)
            os.environ.pop("HTTPS_PROXY", None)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._old_http is None:
            os.environ.pop("HTTP_PROXY", None)
        else:
            os.environ["HTTP_PROXY"] = self._old_http
        if self._old_https is None:
            os.environ.pop("HTTPS_PROXY", None)
        else:
            os.environ["HTTPS_PROXY"] = self._old_https


class SearchWorker(QThread):
    progress = pyqtSignal(int, int, str)
    log = pyqtSignal(str)
    result_chunk = pyqtSignal(str, list, int, int)
    finished_ok = pyqtSignal(dict)
    cancelled = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(
        self,
        keyword,
        mode,
        selected_sources,
        limit,
        work_dir,
        cache_dir,
        proxy_enabled,
        proxy_host,
        proxy_port,
    ):
        super().__init__()
        self.keyword = keyword
        self.mode = mode
        self.selected_sources = selected_sources
        self.limit = limit
        self.work_dir = work_dir
        self.cache_dir = cache_dir
        self.proxy_enabled = proxy_enabled
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()

    def _create_client(self, sources):
        init_cfg = {}
        for source in sources:
            init_cfg[source] = {
                "search_size_per_source": self.limit,
                "work_dir": self.work_dir,
            }
        return musicdl.MusicClient(music_sources=sources, init_music_clients_cfg=init_cfg)

    def _cache_file_for_source(self, source):
        key_raw = f"{self.mode}|{source}|{self.keyword}|{self.limit}"
        key = hashlib.md5(key_raw.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{key}.json")

    def _load_cached_source_result(self, source):
        cache_file = self._cache_file_for_source(source)
        if not os.path.exists(cache_file):
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                payload = json.load(f)
            ts = payload.get("ts")
            if ts:
                cache_age = time.time() - datetime.fromisoformat(ts).timestamp()
                if cache_age > SEARCH_CACHE_TTL_SECONDS:
                    self.log.emit(f"{source} 缓存已过期，重新在线搜索")
                    return None
            songs = payload.get("songs", [])
            if isinstance(songs, list):
                self.log.emit(f"{source} 命中缓存，直接返回 {len(songs)} 首")
                return songs
        except Exception as exc:
            self.log.emit(f"{source} 缓存读取失败，将走在线搜索：{exc}")
        return None

    def _save_cached_source_result(self, source, songs):
        os.makedirs(self.cache_dir, exist_ok=True)
        cache_file = self._cache_file_for_source(source)
        payload = {
            "source": source,
            "mode": self.mode,
            "keyword": self.keyword,
            "limit": self.limit,
            "ts": datetime.now().isoformat(),
            "songs": songs,
        }
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
        except Exception as exc:
            self.log.emit(f"{source} 缓存写入失败：{exc}")

    def run(self):
        if not MUSICDL_AVAILABLE:
            self.error.emit("musicdl 未安装，请先执行 pip install musicdl")
            return
        try:
            with ProxyEnv(self.proxy_enabled, self.proxy_host, self.proxy_port):
                if self.mode == "解析歌单链接":
                    self.log.emit("开始解析歌单链接...")
                    client = self._create_client(self.selected_sources)
                    results = client.parseplaylist(self.keyword)
                    if self.cancel_event.is_set():
                        self.cancelled.emit()
                        return
                    if not isinstance(results, dict):
                        results = {"歌单": results}
                    self.progress.emit(1, 1, "歌单解析完成")
                    self.finished_ok.emit(results)
                    return

                total = len(self.selected_sources)
                done = 0
                merged = {}

                self.log.emit(f"开始并发搜索，共 {total} 个音源...")

                def search_one(source):
                    if self.cancel_event.is_set():
                        return source, [], 0.0
                    t0 = time.time()
                    cached = self._load_cached_source_result(source)
                    if cached is not None:
                        return source, cached, time.time() - t0
                    self.log.emit(f"{source} 开始在线搜索...")
                    client = self._create_client([source])
                    result = client.search(keyword=self.keyword)
                    if isinstance(result, dict):
                        songs = []
                        for value in result.values():
                            if isinstance(value, list):
                                songs.extend(value)
                        result = songs
                    songs = result if isinstance(result, list) else []
                    self._save_cached_source_result(source, songs)
                    return source, songs, time.time() - t0

                max_workers = min(max(total, 1), 12)
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {executor.submit(search_one, src): src for src in self.selected_sources}
                    pending = set(futures.keys())
                    while pending:
                        if self.cancel_event.is_set():
                            executor.shutdown(wait=False, cancel_futures=True)
                            self.cancelled.emit()
                            return
                        done_futures, pending = wait(
                            pending, timeout=0.2, return_when=FIRST_COMPLETED
                        )
                        if not done_futures:
                            continue
                        for future in done_futures:
                            source = futures[future]
                            try:
                                _, songs, elapsed = future.result()
                                merged[source] = songs
                                self.log.emit(f"{source} 搜索完成，结果 {len(songs)} 首，用时 {elapsed:.2f}s")
                            except Exception as exc:
                                merged[source] = []
                                elapsed = 0.0
                                self.log.emit(f"{source} 搜索失败：{exc}")
                            done += 1
                            self.result_chunk.emit(source, merged[source], done, total)
                            self.progress.emit(done, total, f"已完成 {done}/{total} 个音源")

                if self.cancel_event.is_set():
                    self.cancelled.emit()
                    return
                self.finished_ok.emit(merged)
        except Exception as exc:
            self.error.emit(str(exc))


class DownloadWorker(QThread):
    progress = pyqtSignal(int, int, str)
    log = pyqtSignal(str)
    finished_ok = pyqtSignal(dict)
    cancelled = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, songs, limit, download_dir, proxy_enabled, proxy_host, proxy_port):
        super().__init__()
        self.songs = songs
        self.limit = limit
        self.download_dir = download_dir
        self.proxy_enabled = proxy_enabled
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()

    def _create_client(self):
        sources = sorted({song.get("source", "") for song in self.songs if song.get("source", "")})
        init_cfg = {}
        for source in sources:
            init_cfg[source] = {
                "search_size_per_source": self.limit,
                "work_dir": self.download_dir,
            }
        return musicdl.MusicClient(music_sources=sources, init_music_clients_cfg=init_cfg)

    def run(self):
        if not MUSICDL_AVAILABLE:
            self.error.emit("musicdl 未安装，请先执行 pip install musicdl")
            return
        if not self.songs:
            self.finished_ok.emit({"success": 0, "failed": 0, "total": 0, "failed_items": []})
            return
        try:
            with ProxyEnv(self.proxy_enabled, self.proxy_host, self.proxy_port):
                client = self._create_client()
                total = len(self.songs)
                success = 0
                failed_items = []
                for idx, song in enumerate(self.songs, start=1):
                    if self.cancel_event.is_set():
                        self.cancelled.emit(
                            {
                                "success": success,
                                "failed": len(failed_items),
                                "total": total,
                                "failed_items": failed_items,
                            }
                        )
                        return
                    title = song.get("song_name", "未知歌曲")
                    singers = song.get("singers", [])
                    singer_text = ", ".join(singers) if isinstance(singers, list) else str(singers)
                    self.progress.emit(idx - 1, total, f"下载中：{title}")
                    self.log.emit(f"开始下载：{title} - {singer_text}")
                    try:
                        client.download(song_infos=[song])
                        success += 1
                        self.log.emit(f"下载成功：{title}")
                    except Exception as song_exc:
                        failed_items.append(f"{title}: {song_exc}")
                        self.log.emit(f"下载失败：{title} -> {song_exc}")
                    self.progress.emit(idx, total, f"已完成 {idx}/{total}")

                self.finished_ok.emit(
                    {
                        "success": success,
                        "failed": len(failed_items),
                        "total": total,
                        "failed_items": failed_items,
                    }
                )
        except Exception as exc:
            self.error.emit(str(exc))


class ImageSignals(QObject):
    finished = pyqtSignal(int, str, QPixmap)
    error = pyqtSignal(int, str)


class ImageTask(QRunnable):
    def __init__(self, row, image_url, signals):
        super().__init__()
        self.row = row
        self.image_url = image_url
        self.signals = signals

    def run(self):
        try:
            if not self.image_url:
                self.signals.error.emit(self.row, self.image_url)
                return
            response = requests.get(self.image_url, timeout=8)
            if response.status_code != 200:
                self.signals.error.emit(self.row, self.image_url)
                return
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            scaled = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.signals.finished.emit(self.row, self.image_url, scaled)
        except Exception:
            self.signals.error.emit(self.row, self.image_url)


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=-1, hspacing=-1, vspacing=-1):
        super().__init__(parent)
        self._item_list = []
        self._hspacing = hspacing
        self._vspacing = vspacing
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._item_list.append(item)

    def horizontalSpacing(self):
        return self._hspacing if self._hspacing >= 0 else self.smartSpacing(QStyle.PM_LayoutHorizontalSpacing)

    def verticalSpacing(self):
        return self._vspacing if self._vspacing >= 0 else self.smartSpacing(QStyle.PM_LayoutVerticalSpacing)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        return self._item_list[index] if 0 <= index < len(self._item_list) else None

    def takeAt(self, index):
        return self._item_list.pop(index) if 0 <= index < len(self._item_list) else None

    def expandingDirections(self):
        return Qt.Orientations()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.calculate_height(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.calculate_height(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        return size + QSize(left + right, top + bottom)

    def calculate_height(self, rect, test_only):
        left, top, right, bottom = self.getContentsMargins()
        effective = rect.adjusted(left, top, -right, -bottom)
        x = effective.x()
        y = effective.y()
        line_height = 0
        for item in self._item_list:
            widget = item.widget()
            space_x = self.horizontalSpacing()
            if space_x == -1:
                space_x = widget.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
            space_y = self.verticalSpacing()
            if space_y == -1:
                space_y = widget.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > effective.right() and line_height > 0:
                x = effective.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        return y + line_height - rect.y() + bottom

    def smartSpacing(self, pm):
        parent = self.parent()
        if not parent:
            return -1
        if parent.isWidgetType():
            return parent.style().pixelMetric(pm, None, parent)
        return parent.spacing()


class MusicDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Music Download Pro")
        self.resize(1450, 920)
        self.setMinimumSize(1250, 800)
        self.setStyleSheet(self.get_style_sheet())

        self.source_map_cn_to_en = {
            "苹果音乐": "AppleMusicClient",
            "Deezer": "DeezerMusicClient",
            "5sing": "FiveSingMusicClient",
            "Jamendo": "JamendoMusicClient",
            "Joox": "JooxMusicClient",
            "酷我音乐": "KuwoMusicClient",
            "酷狗音乐": "KugouMusicClient",
            "咪咕音乐": "MiguMusicClient",
            "网易云音乐": "NeteaseMusicClient",
            "QQ音乐": "QQMusicClient",
            "千千音乐": "QianqianMusicClient",
            "Qobuz": "QobuzMusicClient",
            "SoundCloud": "SoundCloudMusicClient",
            "StreetVoice": "StreetVoiceMusicClient",
            "汽水音乐": "SodaMusicClient",
            "Spotify": "SpotifyMusicClient",
            "TIDAL": "TIDALMusicClient",
        }
        self.source_map_en_to_cn = {v: k for k, v in self.source_map_cn_to_en.items()}

        self.search_results = {}
        self.music_records = {}
        self.current_right_click_row = -1
        self.search_worker = None
        self.download_worker = None
        self.log_view = None
        self.current_dir = os.getcwd()
        self.download_dir = os.path.join(self.current_dir, "下载音乐")
        self.search_cache_dir = os.path.join(self.current_dir, "搜索缓存")
        self.save_dir = self.download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.search_cache_dir, exist_ok=True)

        self.image_pool = QThreadPool.globalInstance()
        self.image_pool.setMaxThreadCount(8)
        self.image_signals = ImageSignals()
        self.image_signals.finished.connect(self.on_image_downloaded)
        self.image_signals.error.connect(self.on_image_error)
        self.image_cache = {}
        self.seen_song_keys = set()

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        self.setup_controls(root_layout)
        self.setup_table(root_layout)
        self.setup_log_dock()
        self.append_log("应用启动完成。")

        if not MUSICDL_AVAILABLE:
            QMessageBox.warning(self, "警告", "musicdl 库未安装，请运行: pip install musicdl")

    def get_style_sheet(self):
        return """
        QMainWindow {
            background-color: #0d1117;
        }
        QWidget {
            color: #e6edf3;
            font-size: 10pt;
        }
        QGroupBox {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 10px;
            margin-top: 12px;
            padding-top: 8px;
            font-weight: 600;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 6px;
            color: #58a6ff;
        }
        QLineEdit, QComboBox, QSpinBox, QTableWidget {
            background-color: #0d1117;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 6px 8px;
            color: #e6edf3;
        }
        QPushButton {
            background-color: #1f6feb;
            border: 0px;
            border-radius: 8px;
            color: white;
            padding: 8px 14px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #388bfd;
        }
        QPushButton:disabled {
            background-color: #30363d;
            color: #8b949e;
        }
        QProgressBar {
            border: 1px solid #30363d;
            border-radius: 8px;
            text-align: center;
            background: #0d1117;
            height: 18px;
        }
        QProgressBar::chunk {
            border-radius: 7px;
            background-color: #2ea043;
        }
        QTableWidget {
            gridline-color: #21262d;
            alternate-background-color: #161b22;
        }
        QHeaderView::section {
            background-color: #161b22;
            border: none;
            border-right: 1px solid #21262d;
            border-bottom: 1px solid #21262d;
            padding: 6px;
            color: #58a6ff;
            font-weight: 600;
        }
        QPlainTextEdit {
            background: #0b0f14;
            border: 1px solid #30363d;
            color: #b1bac4;
            border-radius: 6px;
            font-family: Consolas, 'Courier New', monospace;
        }
        """

    def setup_controls(self, parent_layout):
        top_group = QGroupBox("控制台")
        top_layout = QVBoxLayout(top_group)
        top_layout.setSpacing(10)

        source_group = QGroupBox("音源选择")
        source_layout = FlowLayout()
        self.source_checkboxes = []
        default_checked = {"网易云音乐", "QQ音乐", "酷我音乐", "酷狗音乐", "咪咕音乐"}
        for chinese_name in self.source_map_cn_to_en.keys():
            cb = QCheckBox(chinese_name)
            cb.setChecked(chinese_name in default_checked)
            self.source_checkboxes.append(cb)
            source_layout.addWidget(cb)
        source_group.setLayout(source_layout)
        top_layout.addWidget(source_group)

        row1 = QHBoxLayout()
        self.spin_limit = QSpinBox()
        self.spin_limit.setRange(1, 120)
        self.spin_limit.setValue(15)
        self.spin_limit.setSuffix(" 条/源")
        self.save_dir_edit = QLineEdit(self.download_dir)
        self.save_dir_edit.setReadOnly(True)
        self.btn_browse_dir = QPushButton("选择目录")
        self.btn_browse_dir.clicked.connect(self.on_browse_save_dir)
        self.btn_clear_cache = QPushButton("清除缓存")
        self.btn_clear_cache.clicked.connect(self.on_clear_cache)
        self.check_auto_download = QCheckBox("搜索完成后自动下载")
        row1.addWidget(QLabel("结果数量"))
        row1.addWidget(self.spin_limit)
        row1.addSpacing(16)
        row1.addWidget(QLabel("下载目录"))
        row1.addWidget(self.save_dir_edit, 1)
        row1.addWidget(self.btn_browse_dir)
        row1.addWidget(self.btn_clear_cache)
        row1.addSpacing(16)
        row1.addWidget(self.check_auto_download)
        top_layout.addLayout(row1)

        proxy_group = QGroupBox("代理设置")
        proxy_layout = QHBoxLayout(proxy_group)
        self.proxy_enable = QCheckBox("启用代理")
        self.proxy_enable.setChecked(False)
        self.proxy_host = QLineEdit("127.0.0.1")
        self.proxy_port = QSpinBox()
        self.proxy_port.setRange(1, 65535)
        self.proxy_port.setValue(7890)
        self.proxy_enable.stateChanged.connect(self.on_proxy_toggle)
        proxy_layout.addWidget(self.proxy_enable)
        proxy_layout.addWidget(QLabel("Host"))
        proxy_layout.addWidget(self.proxy_host)
        proxy_layout.addWidget(QLabel("Port"))
        proxy_layout.addWidget(self.proxy_port)
        proxy_layout.addStretch()
        top_layout.addWidget(proxy_group)
        self.on_proxy_toggle()

        row2 = QHBoxLayout()
        self.search_mode = QComboBox()
        self.search_mode.addItems(["搜索歌曲", "解析歌单链接"])
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入关键词或歌单链接...")
        self.btn_search = QPushButton("开始搜索")
        self.btn_cancel_search = QPushButton("取消搜索")
        self.btn_cancel_search.setEnabled(False)
        self.btn_search.clicked.connect(self.on_search)
        self.btn_cancel_search.clicked.connect(self.on_cancel_search)

        self.combo_download_scope = QComboBox()
        self.combo_download_scope.addItems(["全选", "勾选", "未勾选"])
        self.btn_download = QPushButton("开始下载")
        self.btn_cancel_download = QPushButton("取消下载")
        self.btn_download.setEnabled(False)
        self.btn_cancel_download.setEnabled(False)
        self.btn_download.clicked.connect(self.on_download)
        self.btn_cancel_download.clicked.connect(self.on_cancel_download)

        row2.addWidget(self.search_mode)
        row2.addWidget(self.search_edit, 1)
        row2.addWidget(self.btn_search)
        row2.addWidget(self.btn_cancel_search)
        row2.addSpacing(16)
        row2.addWidget(QLabel("下载范围"))
        row2.addWidget(self.combo_download_scope)
        row2.addWidget(self.btn_download)
        row2.addWidget(self.btn_cancel_download)
        top_layout.addLayout(row2)

        progress_layout = QHBoxLayout()
        self.search_progress = QProgressBar()
        self.search_progress.setFormat("搜索进度 %p%")
        self.search_progress.setValue(0)
        self.download_progress = QProgressBar()
        self.download_progress.setFormat("下载进度 %p%")
        self.download_progress.setValue(0)
        self.status_label = QLabel("就绪")
        self.status_label.setMinimumWidth(260)
        progress_layout.addWidget(self.search_progress, 1)
        progress_layout.addWidget(self.download_progress, 1)
        progress_layout.addWidget(self.status_label)
        top_layout.addLayout(progress_layout)

        parent_layout.addWidget(top_group)

    def setup_table(self, parent_layout):
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(9)
        self.results_table.setHorizontalHeaderLabels(
            ["选择", "封面", "歌曲名", "歌手", "专辑", "格式", "大小", "时长", "来源"]
        )
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self.show_table_context_menu)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.results_table.horizontalHeader().setStretchLastSection(False)
        self.results_table.setColumnWidth(0, 55)
        self.results_table.setColumnWidth(1, 80)
        self.results_table.setColumnWidth(3, 160)
        self.results_table.setColumnWidth(5, 80)
        self.results_table.setColumnWidth(6, 90)
        self.results_table.setColumnWidth(7, 90)
        self.results_table.setColumnWidth(8, 120)
        self.results_table.verticalHeader().setDefaultSectionSize(74)
        parent_layout.addWidget(self.results_table, 1)

    def setup_log_dock(self):
        dock = QDockWidget("日志窗口", self)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(8, 8, 8, 8)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        font = QFont("Consolas")
        font.setPointSize(9)
        self.log_view.setFont(font)

        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(self.log_view.clear)

        log_layout.addWidget(self.log_view, 1)
        log_layout.addWidget(clear_btn, 0)
        dock.setWidget(log_container)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        dock.setMinimumHeight(180)

    def append_log(self, message):
        if self.log_view is None:
            return
        now = datetime.now().strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{now}] {message}")

    def on_proxy_toggle(self):
        enabled = self.proxy_enable.isChecked()
        self.proxy_host.setEnabled(enabled)
        self.proxy_port.setEnabled(enabled)
        state_text = "开启" if enabled else "关闭"
        self.append_log(f"代理已{state_text}")

    def get_proxy_args(self):
        return (
            self.proxy_enable.isChecked(),
            self.proxy_host.text().strip() or "127.0.0.1",
            int(self.proxy_port.value()),
        )

    def get_selected_sources(self):
        return [self.source_map_cn_to_en[cb.text()] for cb in self.source_checkboxes if cb.isChecked()]

    def on_browse_save_dir(self):
        target = QFileDialog.getExistingDirectory(self, "选择保存目录", self.current_dir)
        if target:
            self.download_dir = target
            self.save_dir = target
            self.save_dir_edit.setText(target)
            self.append_log(f"下载目录已设置为：{target}")

    def on_clear_cache(self):
        removed = 0
        failed = 0
        self.image_cache.clear()
        if os.path.exists(self.search_cache_dir):
            for name in os.listdir(self.search_cache_dir):
                path = os.path.join(self.search_cache_dir, name)
                try:
                    if os.path.isfile(path) or os.path.islink(path):
                        os.remove(path)
                    elif os.path.isdir(path):
                        shutil.rmtree(path)
                    removed += 1
                except Exception:
                    failed += 1
        self.append_log(f"缓存清理完成：成功 {removed} 项，失败 {failed} 项。")
        QMessageBox.information(self, "清理完成", f"搜索缓存已清理。\n成功：{removed}\n失败：{failed}")

    def get_file_format(self, song_info):
        for key in ["format", "ext", "file_format", "type"]:
            if song_info.get(key):
                return str(song_info.get(key)).upper()
        url = str(song_info.get("download_url", "")).lower()
        for ext in ["mp3", "flac", "wav", "m4a", "aac"]:
            if f".{ext}" in url:
                return ext.upper()
        return "未知"

    def get_album_image_url(self, song_info):
        for key in [
            "cover",
            "album_cover",
            "pic",
            "picture",
            "img",
            "image",
            "album_img",
            "album_pic",
            "cover_url",
            "pic_url",
        ]:
            value = str(song_info.get(key, ""))
            if value.startswith("http"):
                return value
        return ""

    def on_search(self):
        if self.search_worker and self.search_worker.isRunning():
            QMessageBox.information(self, "提示", "搜索正在进行，请先取消或等待完成。")
            return
        keyword = self.search_edit.text().strip()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入搜索关键词或歌单链接。")
            return
        sources = self.get_selected_sources()
        if not sources:
            QMessageBox.warning(self, "提示", "请至少选择一个音乐源。")
            return
        os.makedirs(self.save_dir, exist_ok=True)
        os.makedirs(self.search_cache_dir, exist_ok=True)

        proxy_enabled, proxy_host, proxy_port = self.get_proxy_args()
        self.search_worker = SearchWorker(
            keyword=keyword,
            mode=self.search_mode.currentText(),
            selected_sources=sources,
            limit=self.spin_limit.value(),
            work_dir=self.search_cache_dir,
            cache_dir=self.search_cache_dir,
            proxy_enabled=proxy_enabled,
            proxy_host=proxy_host,
            proxy_port=proxy_port,
        )
        self.search_worker.progress.connect(self.on_search_progress)
        self.search_worker.log.connect(self.append_log)
        self.search_worker.result_chunk.connect(self.on_search_chunk)
        self.search_worker.finished_ok.connect(self.on_search_finished)
        self.search_worker.cancelled.connect(self.on_search_cancelled)
        self.search_worker.error.connect(self.on_search_error)

        self.results_table.clearContents()
        self.results_table.setRowCount(0)
        self.search_results = {}
        self.music_records = {}
        self.seen_song_keys = set()
        self.btn_search.setEnabled(False)
        self.btn_cancel_search.setEnabled(True)
        self.search_progress.setValue(0)
        self.status_label.setText("搜索中...")
        self.append_log(
            f"开始搜索：{keyword} | 模式={self.search_mode.currentText()} | 音源={len(sources)} | "
            f"下载目录={self.download_dir} | 缓存目录={self.search_cache_dir}"
        )
        self.search_worker.start()

    def on_cancel_search(self):
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.cancel()
            self.status_label.setText("正在取消搜索...")
            self.append_log("收到取消搜索请求。")

    def on_search_progress(self, done, total, text):
        percent = int(done * 100 / total) if total else 0
        self.search_progress.setValue(percent)
        self.status_label.setText(text)

    def on_search_chunk(self, source, songs, done, total):
        self.search_results[source] = songs
        self.append_song_rows(songs)
        self.btn_download.setEnabled(self.results_table.rowCount() > 0)
        source_cn = self.source_map_en_to_cn.get(source, source)
        self.append_log(f"{source_cn} 已加入结果列表：{len(songs)} 首（{done}/{total}）")

    def on_search_finished(self, search_results):
        self.append_log("搜索任务完成。")
        self.search_results = search_results
        all_songs = []
        for songs in search_results.values():
            if isinstance(songs, list):
                all_songs.extend(songs)
        self.btn_search.setEnabled(True)
        self.btn_cancel_search.setEnabled(False)
        self.search_progress.setValue(100)
        self.status_label.setText(f"搜索完成，共 {len(all_songs)} 首")
        self.append_log(f"搜索完成：共 {len(all_songs)} 首歌曲。")
        if self.check_auto_download.isChecked() and all_songs:
            self.append_log("自动下载已开启，开始下载全部结果。")
            self.start_download(all_songs, ask_confirm=False)

    def on_search_cancelled(self):
        self.btn_search.setEnabled(True)
        self.btn_cancel_search.setEnabled(False)
        self.status_label.setText("搜索已取消")
        if self.search_progress.value() == 0:
            self.search_progress.setValue(1)
        self.append_log("搜索已取消。")

    def on_search_error(self, error_msg):
        self.btn_search.setEnabled(True)
        self.btn_cancel_search.setEnabled(False)
        self.status_label.setText("搜索失败")
        self.search_progress.setValue(0)
        self.append_log(f"搜索失败：{error_msg}")
        QMessageBox.critical(self, "搜索失败", str(error_msg))

    def load_table_with_results(self, all_songs):
        self.results_table.clearContents()
        self.results_table.setRowCount(0)
        self.music_records = {}
        self.image_cache = {}
        self.seen_song_keys = set()
        self.append_song_rows(all_songs)

    def make_song_key(self, song):
        song_name = str(song.get("song_name", "")).strip().lower()
        singers = song.get("singers", "")
        if isinstance(singers, list):
            singer_text = "|".join(sorted(str(x).strip().lower() for x in singers if str(x).strip()))
        else:
            singer_text = str(singers).strip().lower()
        album = str(song.get("album", "")).strip().lower()
        duration = str(song.get("duration", "")).strip().lower()
        return f"{song_name}::{singer_text}::{album}::{duration}"

    def append_song_rows(self, songs):
        if not songs:
            return
        added_count = 0
        for song in songs:
            song_key = self.make_song_key(song)
            if song_key in self.seen_song_keys:
                continue
            self.seen_song_keys.add(song_key)
            row = self.results_table.rowCount()
            self.results_table.setRowCount(row + 1)
            check_holder = QWidget()
            check_layout = QHBoxLayout(check_holder)
            check_layout.setContentsMargins(0, 0, 0, 0)
            check_layout.setAlignment(Qt.AlignCenter)
            check_layout.addWidget(QCheckBox())
            self.results_table.setCellWidget(row, 0, check_holder)

            song_name = str(song.get("song_name", ""))
            singers = song.get("singers", "")
            singer_text = ", ".join(singers) if isinstance(singers, list) else str(singers)
            album = str(song.get("album", ""))
            file_size = str(song.get("file_size", ""))
            duration = str(song.get("duration", ""))
            source_en = str(song.get("source", ""))
            source_cn = self.source_map_en_to_cn.get(source_en, source_en)
            file_format = self.get_file_format(song)

            values = [song_name, singer_text, album, file_format, file_size, duration, source_cn]
            for idx, value in enumerate(values, start=2):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                self.results_table.setItem(row, idx, item)
            self.music_records[str(row)] = song

            cover_url = self.get_album_image_url(song)
            if cover_url in self.image_cache:
                self.on_image_downloaded(row, cover_url, self.image_cache[cover_url])
            else:
                self.results_table.setCellWidget(row, 1, self.build_cover_placeholder())
                task = ImageTask(row=row, image_url=cover_url, signals=self.image_signals)
                self.image_pool.start(task)
            added_count += 1
        if added_count:
            self.append_log(f"本批新增 {added_count} 首，当前列表共 {self.results_table.rowCount()} 首。")
        self.btn_download.setEnabled(self.results_table.rowCount() > 0)

    def build_cover_placeholder(self):
        label = QLabel("♪")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 24px; color: #8b949e;")
        return label

    def on_image_downloaded(self, row, image_url, pixmap):
        if row >= self.results_table.rowCount():
            return
        if image_url:
            self.image_cache[image_url] = pixmap
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        label.setPixmap(pixmap)
        self.results_table.setCellWidget(row, 1, label)

    def on_image_error(self, row, image_url):
        if row < self.results_table.rowCount():
            self.results_table.setCellWidget(row, 1, self.build_cover_placeholder())

    def show_table_context_menu(self, pos):
        item = self.results_table.itemAt(pos)
        if not item:
            return
        row = item.row()
        self.current_right_click_row = row
        menu = QMenu(self)
        download_action = QAction("下载当前歌曲", self)
        download_action.triggered.connect(self.download_current_row)
        select_all_action = QAction("全选", self)
        select_all_action.triggered.connect(self.select_all_songs)
        unselect_all_action = QAction("取消全选", self)
        unselect_all_action.triggered.connect(self.deselect_all_songs)
        menu.addAction(download_action)
        menu.addSeparator()
        menu.addAction(select_all_action)
        menu.addAction(unselect_all_action)
        menu.exec_(self.results_table.mapToGlobal(pos))

    def select_all_songs(self):
        for row in range(self.results_table.rowCount()):
            holder = self.results_table.cellWidget(row, 0)
            if not holder:
                continue
            checkbox = holder.findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(True)

    def deselect_all_songs(self):
        for row in range(self.results_table.rowCount()):
            holder = self.results_table.cellWidget(row, 0)
            if not holder:
                continue
            checkbox = holder.findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(False)

    def get_songs_by_download_scope(self):
        scope = self.combo_download_scope.currentText()
        songs = []
        for row in range(self.results_table.rowCount()):
            holder = self.results_table.cellWidget(row, 0)
            if not holder:
                continue
            checkbox = holder.findChild(QCheckBox)
            checked = checkbox.isChecked() if checkbox else False
            if scope == "全选" or (scope == "勾选" and checked) or (scope == "未勾选" and not checked):
                item = self.music_records.get(str(row))
                if item:
                    songs.append(item)
        return songs

    def download_current_row(self):
        if self.current_right_click_row < 0:
            return
        song = self.music_records.get(str(self.current_right_click_row))
        if not song:
            return
        self.start_download([song], ask_confirm=True)

    def on_download(self):
        songs = self.get_songs_by_download_scope()
        if not songs:
            QMessageBox.warning(self, "提示", "没有可下载歌曲。")
            return
        self.start_download(songs, ask_confirm=True)

    def start_download(self, songs, ask_confirm):
        if self.download_worker and self.download_worker.isRunning():
            QMessageBox.information(self, "提示", "下载任务正在进行，请先取消或等待完成。")
            return
        if ask_confirm:
            reply = QMessageBox.question(
                self,
                "确认下载",
                f"确定下载 {len(songs)} 首歌曲吗？\n保存目录：{self.save_dir}",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        os.makedirs(self.save_dir, exist_ok=True)
        proxy_enabled, proxy_host, proxy_port = self.get_proxy_args()
        self.download_worker = DownloadWorker(
            songs=songs,
            limit=self.spin_limit.value(),
            download_dir=self.download_dir,
            proxy_enabled=proxy_enabled,
            proxy_host=proxy_host,
            proxy_port=proxy_port,
        )
        self.download_worker.progress.connect(self.on_download_progress)
        self.download_worker.log.connect(self.append_log)
        self.download_worker.finished_ok.connect(self.on_download_finished)
        self.download_worker.cancelled.connect(self.on_download_cancelled)
        self.download_worker.error.connect(self.on_download_error)

        self.download_progress.setValue(0)
        self.status_label.setText("下载中...")
        self.btn_download.setEnabled(False)
        self.btn_cancel_download.setEnabled(True)
        self.append_log(f"开始下载任务，共 {len(songs)} 首。")
        self.download_worker.start()

    def on_cancel_download(self):
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.cancel()
            self.status_label.setText("正在取消下载...")
            self.append_log("收到取消下载请求。")

    def on_download_progress(self, done, total, text):
        percent = int(done * 100 / total) if total else 0
        self.download_progress.setValue(percent)
        self.status_label.setText(text)

    def on_download_finished(self, result):
        self.btn_download.setEnabled(True)
        self.btn_cancel_download.setEnabled(False)
        self.download_progress.setValue(100)
        self.status_label.setText("下载完成")
        self.append_log(
            f"下载完成：成功 {result['success']}，失败 {result['failed']}，总计 {result['total']}。"
        )
        if result["failed_items"]:
            self.append_log("失败列表：")
            for item in result["failed_items"]:
                self.append_log(f"  {item}")
        QMessageBox.information(
            self,
            "下载完成",
            f"任务完成\n成功：{result['success']}\n失败：{result['failed']}\n保存目录：{self.save_dir}",
        )

    def on_download_cancelled(self, partial):
        self.btn_download.setEnabled(True)
        self.btn_cancel_download.setEnabled(False)
        self.status_label.setText("下载已取消")
        self.append_log(
            f"下载已取消：已成功 {partial['success']}，失败 {partial['failed']}，总计 {partial['total']}。"
        )
        QMessageBox.information(
            self,
            "已取消",
            f"下载已取消\n已成功：{partial['success']}\n失败：{partial['failed']}",
        )

    def on_download_error(self, error_msg):
        self.btn_download.setEnabled(True)
        self.btn_cancel_download.setEnabled(False)
        self.status_label.setText("下载失败")
        self.append_log(f"下载错误：{error_msg}")
        QMessageBox.critical(self, "下载失败", str(error_msg))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MusicDownloader()
    window.show()
    sys.exit(app.exec_())
