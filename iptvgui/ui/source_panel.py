"""直播源管理面板"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QComboBox,
    QLineEdit, QPushButton, QLabel, QTextEdit, QTabWidget,
    QCheckBox, QSpinBox
)
from PySide6.QtCore import Qt, Signal, QThread

from ..models import Source, SourceConfig
from ..services import SourceService, M3uService, HttpService


class LoadSourceThread(QThread):
    """加载源线程"""
    
    finished = Signal(list)  # 加载完成，返回频道列表
    error = Signal(str)
    progress = Signal(str)
    
    def __init__(self, m3u_service: M3uService, url: str, source_name: str, user_agent: str | None):
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
            self.finished.emit(groups)
        except Exception as e:
            self.error.emit(str(e))


class SourcePanel(QWidget):
    """直播源管理面板"""
    
    # 信号
    channels_loaded = Signal(list)  # 频道加载完成
    loading_started = Signal()
    loading_finished = Signal()
    status_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._source_service = SourceService()
        self._http_service = HttpService()
        self._m3u_service = M3uService(self._http_service)
        self._load_thread: LoadSourceThread | None = None
        
        self._init_ui()
        self._load_preset_sources()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # 标签页
        self._tabs = QTabWidget()
        
        # 预设源标签页
        preset_tab = self._create_preset_tab()
        self._tabs.addTab(preset_tab, "预设源")
        
        # 手动输入标签页
        manual_tab = self._create_manual_tab()
        self._tabs.addTab(manual_tab, "手动输入")
        
        # 文本导入标签页
        text_tab = self._create_text_tab()
        self._tabs.addTab(text_tab, "文本导入")
        
        layout.addWidget(self._tabs)
        
        # 代理设置
        proxy_group = self._create_proxy_group()
        layout.addWidget(proxy_group)
        
        # 状态
        self._status_label = QLabel("就绪")
        self._status_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self._status_label)
    
    def _create_preset_tab(self) -> QWidget:
        """创建预设源标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 10, 5, 5)
        
        # 分组筛选
        group_layout = QHBoxLayout()
        group_label = QLabel("分组:")
        group_label.setFixedWidth(40)
        group_layout.addWidget(group_label)
        
        self._preset_group_combo = QComboBox()
        self._preset_group_combo.addItem("全部", "")
        self._preset_group_combo.currentIndexChanged.connect(self._filter_preset_sources)
        group_layout.addWidget(self._preset_group_combo)
        layout.addLayout(group_layout)
        
        # 源选择
        source_layout = QHBoxLayout()
        source_label = QLabel("直播源:")
        source_label.setFixedWidth(40)
        source_layout.addWidget(source_label)
        
        self._preset_source_combo = QComboBox()
        self._preset_source_combo.setMinimumWidth(200)
        source_layout.addWidget(self._preset_source_combo)
        layout.addLayout(source_layout)
        
        # 源信息
        self._preset_info_label = QLabel("")
        self._preset_info_label.setStyleSheet("color: #888; font-size: 11px;")
        self._preset_info_label.setWordWrap(True)
        layout.addWidget(self._preset_info_label)
        
        # 加载按钮
        self._btn_load_preset = QPushButton("加载选中源")
        self._btn_load_preset.clicked.connect(self._load_preset_source)
        layout.addWidget(self._btn_load_preset)
        
        layout.addStretch()
        
        # 关联下拉框变化
        self._preset_source_combo.currentIndexChanged.connect(self._on_preset_source_changed)
        
        return widget
    
    def _create_manual_tab(self) -> QWidget:
        """创建手动输入标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 10, 5, 5)
        
        # URL 输入
        url_label = QLabel("M3U 地址:")
        layout.addWidget(url_label)
        
        self._manual_url_input = QLineEdit()
        self._manual_url_input.setPlaceholderText("https://example.com/live.m3u")
        layout.addWidget(self._manual_url_input)
        
        # 源名称
        name_layout = QHBoxLayout()
        name_label = QLabel("名称:")
        name_label.setFixedWidth(40)
        name_layout.addWidget(name_label)
        
        self._manual_name_input = QLineEdit()
        self._manual_name_input.setPlaceholderText("可选，留空使用 URL")
        name_layout.addWidget(self._manual_name_input)
        layout.addLayout(name_layout)
        
        # 加载按钮
        self._btn_load_manual = QPushButton("加载")
        self._btn_load_manual.clicked.connect(self._load_manual_source)
        layout.addWidget(self._btn_load_manual)
        
        layout.addStretch()
        return widget
    
    def _create_text_tab(self) -> QWidget:
        """创建文本导入标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 10, 5, 5)
        
        # 说明
        hint_label = QLabel("粘贴 M3U 文本内容:")
        layout.addWidget(hint_label)
        
        # 文本框
        self._text_input = QTextEdit()
        self._text_input.setPlaceholderText("#EXTM3U\n#EXTINF:-1,频道名\nhttp://...")
        layout.addWidget(self._text_input)
        
        # 导入按钮
        self._btn_import_text = QPushButton("导入")
        self._btn_import_text.clicked.connect(self._import_text)
        layout.addWidget(self._btn_import_text)
        
        return widget
    
    def _create_proxy_group(self) -> QGroupBox:
        """创建代理设置分组"""
        group = QGroupBox("代理设置")
        layout = QVBoxLayout(group)
        
        # 启用开关
        enable_layout = QHBoxLayout()
        self._proxy_enabled = QCheckBox("启用代理")
        self._proxy_enabled.stateChanged.connect(self._on_proxy_changed)
        enable_layout.addWidget(self._proxy_enabled)
        enable_layout.addStretch()
        layout.addLayout(enable_layout)
        
        # 代理地址
        addr_layout = QHBoxLayout()
        
        host_label = QLabel("主机:")
        host_label.setFixedWidth(30)
        addr_layout.addWidget(host_label)
        
        self._proxy_host = QLineEdit("127.0.0.1")
        self._proxy_host.setFixedWidth(120)
        addr_layout.addWidget(self._proxy_host)
        
        port_label = QLabel("端口:")
        port_label.setFixedWidth(30)
        addr_layout.addWidget(port_label)
        
        self._proxy_port = QSpinBox()
        self._proxy_port.setRange(1, 65535)
        self._proxy_port.setValue(7890)
        self._proxy_port.setFixedWidth(80)
        addr_layout.addWidget(self._proxy_port)
        
        addr_layout.addStretch()
        layout.addLayout(addr_layout)
        
        return group
    
    def _load_preset_sources(self):
        """加载预设源配置"""
        try:
            config = self._source_service.load_config()
            
            # 更新分组下拉框
            groups = config.get_source_groups()
            self._preset_group_combo.clear()
            self._preset_group_combo.addItem("全部", "")
            for group in groups:
                self._preset_group_combo.addItem(group, group)
            
            # 更新源下拉框
            self._update_preset_source_list(config.sources)
            
            # 保存 EPG 源供其他组件使用
            self._epg_sources = config.epg_sources
            
        except Exception as e:
            self._status_label.setText(f"加载配置失败: {e}")
    
    def _update_preset_source_list(self, sources: list[Source]):
        """更新预设源下拉框"""
        self._preset_source_combo.clear()
        
        for source in sources:
            display = source.name
            if source.note:
                display += f" ({source.note})"
            self._preset_source_combo.addItem(display, source)
    
    def _filter_preset_sources(self):
        """筛选预设源"""
        group = self._preset_group_combo.currentData() or ""
        sources = self._source_service.get_sources_by_group(group)
        self._update_preset_source_list(sources)
    
    def _on_preset_source_changed(self, index: int):
        """预设源选择变化"""
        source: Source = self._preset_source_combo.currentData()
        if source:
            info = f"URL: {source.url}"
            if source.epg:
                info += f"\nEPG: {source.epg}"
            if source.user_agent:
                info += f"\nUA: {source.user_agent}"
            self._preset_info_label.setText(info)
        else:
            self._preset_info_label.setText("")
    
    def _load_preset_source(self):
        """加载预设源"""
        source: Source = self._preset_source_combo.currentData()
        if not source:
            self._status_label.setText("请选择一个直播源")
            return
        
        self._load_source(source.url, source.name, source.user_agent)
    
    def _load_manual_source(self):
        """加载手动输入的源"""
        url = self._manual_url_input.text().strip()
        if not url:
            self._status_label.setText("请输入 M3U 地址")
            return
        
        name = self._manual_name_input.text().strip() or url
        self._load_source(url, name, None)
    
    def _import_text(self):
        """导入文本"""
        text = self._text_input.toPlainText().strip()
        if not text:
            self._status_label.setText("请粘贴 M3U 内容")
            return
        
        try:
            groups = self._m3u_service.parse_and_group(text, "文本导入")
            self._status_label.setText(f"导入成功，共 {len(groups)} 个频道")
            self.channels_loaded.emit(groups)
        except Exception as e:
            self._status_label.setText(f"导入失败: {e}")
    
    def _load_source(self, url: str, source_name: str, user_agent: str | None):
        """加载直播源"""
        # 取消之前的加载
        if self._load_thread and self._load_thread.isRunning():
            self._load_thread.terminate()
            self._load_thread.wait()
        
        # 更新代理设置
        self._http_service.set_proxy(
            enabled=self._proxy_enabled.isChecked(),
            host=self._proxy_host.text(),
            port=self._proxy_port.value(),
        )
        
        # 开始加载
        self._set_loading(True)
        self._status_label.setText("正在加载...")
        self.loading_started.emit()
        
        self._load_thread = LoadSourceThread(
            self._m3u_service, url, source_name, user_agent
        )
        self._load_thread.finished.connect(self._on_load_finished)
        self._load_thread.error.connect(self._on_load_error)
        self._load_thread.progress.connect(lambda msg: self._status_label.setText(msg))
        self._load_thread.start()
    
    def _on_load_finished(self, groups: list):
        """加载完成"""
        self._set_loading(False)
        self._status_label.setText(f"加载成功，共 {len(groups)} 个频道")
        self.channels_loaded.emit(groups)
        self.loading_finished.emit()
    
    def _on_load_error(self, error: str):
        """加载错误"""
        self._set_loading(False)
        self._status_label.setText(f"加载失败: {error}")
        self.loading_finished.emit()
    
    def _set_loading(self, loading: bool):
        """设置加载状态"""
        self._btn_load_preset.setEnabled(not loading)
        self._btn_load_manual.setEnabled(not loading)
        self._btn_import_text.setEnabled(not loading)
    
    def _on_proxy_changed(self):
        """代理设置变化"""
        enabled = self._proxy_enabled.isChecked()
        self._proxy_host.setEnabled(enabled)
        self._proxy_port.setEnabled(enabled)
        
        self._http_service.set_proxy(
            enabled=enabled,
            host=self._proxy_host.text(),
            port=self._proxy_port.value(),
        )
    
    def get_epg_sources(self):
        """获取 EPG 源列表"""
        return getattr(self, '_epg_sources', [])
    
    def get_proxy_string(self) -> str | None:
        """获取代理字符串"""
        if self._proxy_enabled.isChecked():
            return f"{self._proxy_host.text()}:{self._proxy_port.value()}"
        return None
