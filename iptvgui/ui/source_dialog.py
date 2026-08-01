"""直播源加载对话框"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QComboBox, QLineEdit, QTextEdit, QPushButton, QLabel,
    QGroupBox, QFormLayout, QMessageBox, QProgressDialog
)
from PySide6.QtCore import Qt, Signal, QThread

from ..models import Source, SourceConfig
from ..services import SourceService, M3uService, HttpService


# 默认 User-Agent
DEFAULT_USER_AGENT = "AptvPlayer/1.5.8"


class LoadThread(QThread):
    """加载线程"""
    finished = Signal(list, str)  # (groups, source_name)
    error = Signal(str)
    progress = Signal(str)
    
    def __init__(self, m3u_service: M3uService, url: str, source_name: str, user_agent: str):
        super().__init__()
        self._m3u_service = m3u_service
        self._url = url
        self._source_name = source_name
        self._user_agent = user_agent
    
    def run(self):
        try:
            groups = self._m3u_service.load_and_group(
                url=self._url,
                source_name=self._source_name,
                timeout=30,
                user_agent=self._user_agent,
                progress_callback=lambda msg: self.progress.emit(msg),
            )
            self.finished.emit(groups, self._source_name)
        except Exception as e:
            self.error.emit(str(e))


class SourceDialog(QDialog):
    """直播源加载对话框"""
    
    # 加载完成信号
    channels_loaded = Signal(list, str)  # (groups, source_name)
    
    def __init__(self, http_service: HttpService, parent=None):
        super().__init__(parent)
        self._http_service = http_service
        self._m3u_service = M3uService(http_service)
        self._source_service = SourceService()
        self._load_thread: LoadThread | None = None
        
        self.setWindowTitle("加载直播源")
        self.setMinimumSize(500, 400)
        self.setModal(True)
        
        self._init_ui()
        self._load_preset_sources()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标签页
        self._tabs = QTabWidget()
        
        # 预设源
        preset_tab = self._create_preset_tab()
        self._tabs.addTab(preset_tab, "预设源")
        
        # 手动输入
        manual_tab = self._create_manual_tab()
        self._tabs.addTab(manual_tab, "手动输入")
        
        # 文本导入
        text_tab = self._create_text_tab()
        self._tabs.addTab(text_tab, "文本导入")
        
        layout.addWidget(self._tabs)
        
        # User-Agent 设置
        ua_group = QGroupBox("请求设置")
        ua_layout = QFormLayout(ua_group)
        
        self._ua_input = QLineEdit(DEFAULT_USER_AGENT)
        self._ua_input.setPlaceholderText("自定义 User-Agent")
        ua_layout.addRow("User-Agent:", self._ua_input)
        
        layout.addWidget(ua_group)
        
        # 状态
        self._status_label = QLabel("就绪")
        self._status_label.setStyleSheet("color: #888;")
        layout.addWidget(self._status_label)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self._btn_load = QPushButton("加载")
        self._btn_load.setDefault(True)
        self._btn_load.clicked.connect(self._on_load)
        btn_layout.addWidget(self._btn_load)
        
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)
    
    def _create_preset_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 15, 10, 10)
        
        # 分组筛选
        group_layout = QHBoxLayout()
        group_layout.addWidget(QLabel("分组:"))
        
        self._preset_group_combo = QComboBox()
        self._preset_group_combo.addItem("全部", "")
        self._preset_group_combo.currentIndexChanged.connect(self._filter_preset_sources)
        group_layout.addWidget(self._preset_group_combo, 1)
        layout.addLayout(group_layout)
        
        # 源选择
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("直播源:"))
        
        self._preset_source_combo = QComboBox()
        self._preset_source_combo.currentIndexChanged.connect(self._on_preset_changed)
        source_layout.addWidget(self._preset_source_combo, 1)
        layout.addLayout(source_layout)
        
        # 源信息
        self._preset_info = QLabel("")
        self._preset_info.setStyleSheet("color: #888; font-size: 11px;")
        self._preset_info.setWordWrap(True)
        layout.addWidget(self._preset_info)
        
        layout.addStretch()
        return widget
    
    def _create_manual_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 15, 10, 10)
        
        layout.addWidget(QLabel("M3U 地址:"))
        self._manual_url = QLineEdit()
        self._manual_url.setPlaceholderText("https://example.com/live.m3u")
        layout.addWidget(self._manual_url)
        
        layout.addWidget(QLabel("名称 (可选):"))
        self._manual_name = QLineEdit()
        self._manual_name.setPlaceholderText("自定义名称")
        layout.addWidget(self._manual_name)
        
        layout.addStretch()
        return widget
    
    def _create_text_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 15, 10, 10)
        
        layout.addWidget(QLabel("粘贴 M3U 文本内容:"))
        self._text_input = QTextEdit()
        self._text_input.setPlaceholderText("#EXTM3U\n#EXTINF:-1,频道名\nhttp://...")
        layout.addWidget(self._text_input)
        
        return widget
    
    def _load_preset_sources(self):
        """加载预设源配置"""
        try:
            config = self._source_service.load_config()
            
            # 更新分组
            groups = config.get_source_groups()
            self._preset_group_combo.clear()
            self._preset_group_combo.addItem("全部", "")
            for group in groups:
                self._preset_group_combo.addItem(group, group)
            
            # 更新源列表
            self._update_preset_sources(config.sources)
            
        except Exception as e:
            self._status_label.setText(f"加载配置失败: {e}")
    
    def _update_preset_sources(self, sources: list[Source]):
        self._preset_source_combo.clear()
        for source in sources:
            display = source.name
            if source.note:
                display += f" - {source.note}"
            self._preset_source_combo.addItem(display, source)
    
    def _filter_preset_sources(self):
        group = self._preset_group_combo.currentData() or ""
        sources = self._source_service.get_sources_by_group(group)
        self._update_preset_sources(sources)
    
    def _on_preset_changed(self):
        source: Source = self._preset_source_combo.currentData()
        if source:
            info = f"URL: {source.url}"
            if source.epg:
                info += f"\nEPG: {source.epg}"
            if source.user_agent:
                info += f"\n需要 UA: {source.user_agent}"
                # 自动填充 UA
                self._ua_input.setText(source.user_agent)
            self._preset_info.setText(info)
        else:
            self._preset_info.setText("")
    
    def _on_load(self):
        """点击加载"""
        tab_index = self._tabs.currentIndex()
        
        if tab_index == 0:  # 预设源
            source: Source = self._preset_source_combo.currentData()
            if not source:
                QMessageBox.warning(self, "提示", "请选择一个直播源")
                return
            self._load_from_url(source.url, source.name)
        
        elif tab_index == 1:  # 手动输入
            url = self._manual_url.text().strip()
            if not url:
                QMessageBox.warning(self, "提示", "请输入 M3U 地址")
                return
            name = self._manual_name.text().strip() or url
            self._load_from_url(url, name)
        
        elif tab_index == 2:  # 文本导入
            text = self._text_input.toPlainText().strip()
            if not text:
                QMessageBox.warning(self, "提示", "请粘贴 M3U 内容")
                return
            self._load_from_text(text)
    
    def _load_from_url(self, url: str, source_name: str):
        """从 URL 加载"""
        if self._load_thread and self._load_thread.isRunning():
            return
        
        self._btn_load.setEnabled(False)
        self._status_label.setText("正在加载...")
        
        ua = self._ua_input.text().strip() or DEFAULT_USER_AGENT
        
        self._load_thread = LoadThread(self._m3u_service, url, source_name, ua)
        self._load_thread.finished.connect(self._on_load_finished)
        self._load_thread.error.connect(self._on_load_error)
        self._load_thread.progress.connect(lambda msg: self._status_label.setText(msg))
        self._load_thread.start()
    
    def _load_from_text(self, text: str):
        """从文本加载"""
        try:
            groups = self._m3u_service.parse_and_group(text, "文本导入")
            self._on_load_finished(groups, "文本导入")
        except Exception as e:
            self._on_load_error(str(e))
    
    def _on_load_finished(self, groups: list, source_name: str):
        self._btn_load.setEnabled(True)
        self._status_label.setText(f"加载成功，共 {len(groups)} 个频道")
        self.channels_loaded.emit(groups, source_name)
        self.accept()
    
    def _on_load_error(self, error: str):
        self._btn_load.setEnabled(True)
        self._status_label.setText(f"加载失败: {error}")
        QMessageBox.critical(self, "加载失败", error)
