"""EPG 节目单弹窗 - 按日期显示"""

from datetime import datetime, timedelta
from collections import defaultdict

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QLabel, QPushButton,
    QHeaderView, QAbstractItemView, QComboBox
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
                limit=200,
                progress_callback=lambda msg: self.progress.emit(msg),
            )
            self.finished.emit(programmes, self._channel_key)
        except Exception as e:
            self.error.emit(str(e))


class EpgDialog(QDialog):
    """EPG 节目单弹窗"""
    
    def __init__(self, parent=None, channel_name: str = "", tvg_id: str = "", 
                 epg_sources: list[EpgSource] = None):
        super().__init__(parent)
        self._channel_name = channel_name
        self._tvg_id = tvg_id
        self._channel_key = f"{channel_name}|{tvg_id}"
        self._epg_sources = epg_sources or []
        self._programmes: list[dict] = []
        self._load_thread: EpgLoadThread | None = None
        
        self._http_service = HttpService()
        self._epg_service = EpgService(self._http_service)
        
        self.setWindowTitle(f"节目单 - {channel_name}")
        self.setMinimumSize(600, 500)
        self.resize(700, 550)
        
        self._init_ui()
        self._load_epg()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 顶部：EPG 源选择
        top_layout = QHBoxLayout()
        
        top_layout.addWidget(QLabel(f"频道: {self._channel_name}"))
        top_layout.addStretch()
        
        top_layout.addWidget(QLabel("EPG 源:"))
        self._epg_combo = QComboBox()
        self._epg_combo.setMinimumWidth(150)
        for source in self._epg_sources:
            self._epg_combo.addItem(source.name, source.url)
        if not self._epg_sources:
            self._epg_combo.addItem("无可用 EPG 源", "")
        top_layout.addWidget(self._epg_combo)
        
        self._btn_refresh = QPushButton("刷新")
        self._btn_refresh.clicked.connect(self._refresh_epg)
        top_layout.addWidget(self._btn_refresh)
        
        layout.addLayout(top_layout)
        
        # 日期 Tab
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)
        
        # 状态
        self._status_label = QLabel("正在加载...")
        self._status_label.setStyleSheet("color: #888;")
        layout.addWidget(self._status_label)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
    
    def _load_epg(self):
        """加载 EPG（优先缓存）"""
        # 先尝试缓存
        cached = cache_manager.load_epg(self._channel_key)
        if cached:
            self._programmes = cached
            self._display_programmes()
            self._status_label.setText(f"已从缓存加载 {len(cached)} 条节目")
            return
        
        # 没有缓存，从网络加载
        self._fetch_epg()
    
    def _refresh_epg(self):
        """刷新 EPG（强制从网络加载）"""
        self._fetch_epg()
    
    def _fetch_epg(self):
        """从网络获取 EPG"""
        epg_url = self._epg_combo.currentData()
        if not epg_url:
            self._status_label.setText("无可用 EPG 源")
            return
        
        if self._load_thread and self._load_thread.isRunning():
            return
        
        self._btn_refresh.setEnabled(False)
        self._status_label.setText("正在加载...")
        
        self._load_thread = EpgLoadThread(
            self._epg_service, epg_url, self._channel_name, self._tvg_id
        )
        self._load_thread.finished.connect(self._on_loaded)
        self._load_thread.error.connect(self._on_error)
        self._load_thread.progress.connect(lambda msg: self._status_label.setText(msg))
        self._load_thread.start()
    
    def _on_loaded(self, programmes: list[dict], channel_key: str):
        """加载完成"""
        self._btn_refresh.setEnabled(True)
        self._programmes = programmes
        
        if programmes:
            # 保存到缓存
            cache_manager.save_epg(channel_key, programmes)
            self._display_programmes()
            self._status_label.setText(f"已加载 {len(programmes)} 条节目")
        else:
            self._status_label.setText("未找到节目信息")
    
    def _on_error(self, error: str):
        """加载错误"""
        self._btn_refresh.setEnabled(True)
        self._status_label.setText(f"加载失败: {error}")
    
    def _display_programmes(self):
        """按日期分组显示节目"""
        self._tabs.clear()
        
        if not self._programmes:
            return
        
        # 按日期分组
        by_date: dict[str, list[dict]] = defaultdict(list)
        
        for prog in self._programmes:
            start = prog.get("start", "")
            if start:
                date_part = start.split(" ")[0] if " " in start else "未知"
                by_date[date_part].append(prog)
            else:
                by_date["未知"].append(prog)
        
        # 排序日期
        sorted_dates = sorted(by_date.keys())
        
        # 获取今天的日期和当前时间
        now = datetime.now()
        today = now.strftime("%m-%d")
        
        highlight_color = QColor("#e94560")
        highlight_bg = QColor("#3d1a2a")
        
        for date_str in sorted_dates:
            progs = by_date[date_str]
            
            # 创建表格
            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["时间", "节目", "简介"])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            table.setColumnWidth(0, 100)
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setAlternatingRowColors(True)
            
            table.setRowCount(len(progs))
            
            current_row = -1
            
            for row, prog in enumerate(progs):
                start = prog.get("start", "")
                stop = prog.get("stop", "")
                title = prog.get("title", "")
                desc = prog.get("desc", "")
                
                # 时间（只显示 HH:MM）
                time_str = start.split(" ")[-1] if " " in start else start
                if stop:
                    time_str += f"-{stop.split(' ')[-1]}"
                time_item = QTableWidgetItem(time_str)
                
                # 节目名
                title_item = QTableWidgetItem(title)
                
                # 简介
                desc_item = QTableWidgetItem(desc)
                
                # 构建 tooltip 详细信息
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
                desc_item.setToolTip(tooltip)
                
                # 检查是否是当前正在播放的节目（仅限今天）
                if date_str == today:
                    if self._is_current_programme(start, stop):
                        current_row = row
                        for item in [time_item, title_item, desc_item]:
                            item.setForeground(QBrush(highlight_color))
                            item.setBackground(QBrush(highlight_bg))
                        time_item.setText("▶ " + time_str)
                
                table.setItem(row, 0, time_item)
                table.setItem(row, 1, title_item)
                table.setItem(row, 2, desc_item)
            
            # Tab 标题
            tab_title = date_str
            if date_str == today:
                tab_title = f"★ {date_str} (今天)"
            
            self._tabs.addTab(table, tab_title)
            
            # 如果是今天，自动滚动到当前节目
            if date_str == today and current_row >= 0:
                table.scrollToItem(
                    table.item(current_row, 0),
                    QAbstractItemView.ScrollHint.PositionAtCenter
                )
                table.selectRow(current_row)
        
        # 选中今天的 Tab
        for i in range(self._tabs.count()):
            if today in self._tabs.tabText(i):
                self._tabs.setCurrentIndex(i)
                break
    
    def _parse_epg_time(self, time_str: str) -> datetime | None:
        """解析 EPG 时间字符串"""
        if not time_str:
            return None
        try:
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
            return start_time <= now <= start_time + timedelta(hours=2)
        return False
