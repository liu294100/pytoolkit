"""EPG 节目面板 - 支持本地缓存、自动加载、高亮当前节目"""

from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QComboBox, QPushButton, QLabel, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QColor, QBrush

from ..models import EpgSource
from ..services import EpgService, HttpService
from ..services.cache_manager import cache_manager


class EpgLoadThread(QThread):
    """EPG 加载线程"""
    finished = Signal(list, str)
    error = Signal(str)
    progress = Signal(str)
    
    def __init__(self, epg_service: EpgService, epg_url: str, channel_name: str, tvg_id: str):
        super().__init__()
        self._epg_service = epg_service
        self._epg_url = epg_url
        self._channel_name = channel_name
        self._tvg_id = tvg_id
        self._channel_key = f"{channel_name}|{tvg_id}"
    
    def run(self):
        try:
            programmes = self._epg_service.load_programmes(
                epg_url=self._epg_url,
                channel_name=self._channel_name,
                tvg_id=self._tvg_id,
                timeout=60,
                progress_callback=lambda msg: self.progress.emit(msg),
            )
            self.finished.emit(programmes, self._channel_key)
        except Exception as e:
            self.error.emit(str(e))


class EpgPanel(QWidget):
    """EPG 节目面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._epg_sources: list[EpgSource] = []
        self._current_channel_name = ""
        self._current_tvg_id = ""
        self._load_thread: EpgLoadThread | None = None
        
        self._http_service = HttpService()
        self._epg_service = EpgService(self._http_service)
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        # 标题行
        title_layout = QHBoxLayout()
        title = QLabel("📺 节目单")
        title.setStyleSheet("font-weight: bold; color: #e94560;")
        title_layout.addWidget(title)
        
        title_layout.addStretch()
        
        # 打开完整节目单按钮
        self._btn_open_full = QPushButton("📋 完整")
        self._btn_open_full.setToolTip("打开完整节目单弹窗")
        self._btn_open_full.clicked.connect(self._open_epg_dialog)
        title_layout.addWidget(self._btn_open_full)
        
        layout.addLayout(title_layout)
        
        # EPG 源选择
        source_layout = QHBoxLayout()
        source_layout.setSpacing(3)
        
        self._epg_combo = QComboBox()
        self._epg_combo.setMinimumWidth(60)
        source_layout.addWidget(self._epg_combo, 1)
        
        self._btn_load = QPushButton("刷新")
        self._btn_load.clicked.connect(self._load_epg_from_network)
        source_layout.addWidget(self._btn_load)
        
        layout.addLayout(source_layout)
        
        # 当前频道
        self._channel_label = QLabel("当前: -")
        self._channel_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self._channel_label)
        
        # 节目表
        self._table = QTableWidget()
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["时间", "节目"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 70)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setDefaultSectionSize(24)
        layout.addWidget(self._table)
        
        # 状态
        self._status_label = QLabel("选择频道自动加载")
        self._status_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self._status_label)
    
    def set_epg_sources(self, sources: list[EpgSource]):
        """设置 EPG 源列表"""
        self._epg_sources = sources
        
        self._epg_combo.clear()
        for source in sources:
            self._epg_combo.addItem(source.name, source.url)
        
        if not sources:
            self._epg_combo.addItem("无EPG", "")
    
    def set_current_channel(self, name: str, tvg_id: str = "", auto_load: bool = True):
        """设置当前频道，自动加载 EPG（优先缓存）"""
        self._current_channel_name = name
        self._current_tvg_id = tvg_id
        self._channel_label.setText(f"当前: {name}")
        
        if not auto_load:
            return
        
        # 优先从缓存加载
        channel_key = f"{name}|{tvg_id}"
        cached = cache_manager.load_epg(channel_key)
        
        if cached:
            self._display_programmes(cached)
            self._status_label.setText(f"缓存 ({len(cached)}条)")
        else:
            self._table.setRowCount(0)
            if self._get_epg_url():
                self._status_label.setText("加载中...")
                self._load_epg_from_network()
            else:
                self._status_label.setText("无EPG源")
    
    def _get_epg_url(self) -> str:
        return self._epg_combo.currentData() or ""
    
    def _load_epg_from_network(self):
        """从网络加载 EPG"""
        if not self._current_channel_name:
            self._status_label.setText("请先选择频道")
            return
        
        epg_url = self._get_epg_url()
        if not epg_url:
            self._status_label.setText("无EPG源")
            return
        
        if self._load_thread and self._load_thread.isRunning():
            return
        
        self._btn_load.setEnabled(False)
        self._status_label.setText("加载中...")
        
        self._load_thread = EpgLoadThread(
            self._epg_service,
            epg_url,
            self._current_channel_name,
            self._current_tvg_id,
        )
        self._load_thread.finished.connect(self._on_epg_loaded)
        self._load_thread.error.connect(self._on_epg_error)
        self._load_thread.progress.connect(lambda msg: self._status_label.setText(msg))
        self._load_thread.start()
    
    def _on_epg_loaded(self, programmes: list[dict], channel_key: str):
        """EPG 加载完成"""
        self._btn_load.setEnabled(True)
        
        if not programmes:
            self._status_label.setText("未找到节目")
            self._table.setRowCount(0)
            return
        
        # 保存到缓存
        cache_manager.save_epg(channel_key, programmes)
        
        self._display_programmes(programmes)
        self._status_label.setText(f"已加载 ({len(programmes)}条)")
    
    def _parse_epg_time(self, time_str: str) -> datetime | None:
        """解析 EPG 时间字符串，格式: MM-DD HH:MM"""
        if not time_str:
            return None
        try:
            # 格式: "08-01 14:30"
            now = datetime.now()
            parts = time_str.split(" ")
            if len(parts) == 2:
                date_part, time_part = parts
                month, day = map(int, date_part.split("-"))
                hour, minute = map(int, time_part.split(":"))
                return datetime(now.year, month, day, hour, minute)
        except Exception:
            pass
        return None
    
    def _is_current_programme(self, start: str, stop: str) -> bool:
        """判断是否是当前正在播放的节目"""
        now = datetime.now()
        start_time = self._parse_epg_time(start)
        stop_time = self._parse_epg_time(stop)
        
        if start_time and stop_time:
            return start_time <= now <= stop_time
        elif start_time:
            # 没有结束时间，只检查开始时间是否在当前时间之前1小时内
            from datetime import timedelta
            return start_time <= now <= start_time + timedelta(hours=2)
        return False
    
    def _display_programmes(self, programmes: list[dict]):
        """显示节目列表，高亮当前节目并滚动到对应位置"""
        display_list = programmes[:30]
        self._table.setRowCount(len(display_list))
        
        current_row = -1
        highlight_color = QColor("#e94560")
        highlight_bg = QColor("#3d1a2a")
        
        for row, prog in enumerate(display_list):
            start = prog.get("start", "")
            stop = prog.get("stop", "")
            title = prog.get("title", "")
            desc = prog.get("desc", "")
            
            # 时间（只显示 HH:MM）
            time_str = start.split(" ")[-1] if " " in start else start
            time_item = QTableWidgetItem(time_str)
            
            # 节目名
            title_item = QTableWidgetItem(title)
            
            # 构建 tooltip
            tooltip_lines = []
            full_time = start
            if stop:
                full_time += f" - {stop}"
            if full_time:
                tooltip_lines.append(f"时间: {full_time}")
            if title:
                tooltip_lines.append(f"节目: {title}")
            if desc:
                tooltip_lines.append(f"简介: {desc}")
            tooltip = "\n".join(tooltip_lines) if tooltip_lines else "无详细信息"
            
            time_item.setToolTip(tooltip)
            title_item.setToolTip(tooltip)
            
            # 检查是否是当前正在播放的节目
            if self._is_current_programme(start, stop):
                current_row = row
                time_item.setForeground(QBrush(highlight_color))
                title_item.setForeground(QBrush(highlight_color))
                time_item.setBackground(QBrush(highlight_bg))
                title_item.setBackground(QBrush(highlight_bg))
            
            self._table.setItem(row, 0, time_item)
            self._table.setItem(row, 1, title_item)
        
        # 自动滚动到当前节目
        if current_row >= 0:
            self._table.scrollToItem(
                self._table.item(current_row, 0),
                QAbstractItemView.ScrollHint.PositionAtCenter
            )
            self._table.selectRow(current_row)
    
    def _on_epg_error(self, error: str):
        """EPG 加载错误"""
        self._btn_load.setEnabled(True)
        self._status_label.setText(f"失败")
        self._table.setRowCount(0)
    
    def _open_epg_dialog(self):
        """打开完整节目单弹窗"""
        if not self._current_channel_name:
            self._status_label.setText("请先选择频道")
            return
        
        from .epg_dialog import EpgDialog
        dialog = EpgDialog(
            self,
            channel_name=self._current_channel_name,
            tvg_id=self._current_tvg_id,
            epg_sources=self._epg_sources,
        )
        dialog.exec()
    
    def clear(self):
        """清空"""
        self._current_channel_name = ""
        self._current_tvg_id = ""
        self._channel_label.setText("当前: -")
        self._table.setRowCount(0)
        self._status_label.setText("选择频道自动加载")
