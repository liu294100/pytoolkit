"""主窗口 - 菜单化、简化布局"""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QStatusBar, QMessageBox, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QIcon

from .player_widget import PlayerWidget
from .channel_list import ChannelListWidget
from .epg_panel import EpgPanel
from .source_dialog import SourceDialog
from .proxy_dialog import ProxyDialog
from .mpv_dialog import MpvDialog
from ..models import ChannelGroup
from ..services import HttpService, SourceService
from ..services.cache_manager import cache_manager


def _get_icon_path() -> Path | None:
    """获取图标路径"""
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent.parent
    
    icon_path = base / "resources" / "icon.ico"
    if icon_path.exists():
        return icon_path
    return None


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self._current_channel: ChannelGroup | None = None
        self._http_service = HttpService()
        self._source_service = SourceService()
        
        # 代理设置
        self._proxy_enabled = False
        self._proxy_host = "127.0.0.1"
        self._proxy_port = 7890
        
        self._init_window()
        self._init_ui()
        self._init_menu()
        self._init_statusbar()
        self._connect_signals()
        self._load_settings()
        self._load_cached_channels()
    
    def _init_window(self):
        self.setWindowTitle("IPTV Player")
        self.setMinimumSize(1100, 650)
        self.resize(1280, 720)
        
        # 设置窗口图标（标题栏和任务栏）
        icon_path = _get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # 居中
        screen = self.screen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # 主分割器
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：频道列表
        self._channel_list = ChannelListWidget()
        self._splitter.addWidget(self._channel_list)
        
        # 中间：播放器
        self._player = PlayerWidget()
        self._splitter.addWidget(self._player)
        
        # 右侧：EPG
        self._epg_panel = EpgPanel()
        self._splitter.addWidget(self._epg_panel)
        
        # 分割比例
        self._splitter.setSizes([220, 700, 260])
        
        main_layout.addWidget(self._splitter)
    
    def _init_menu(self):
        menubar = self.menuBar()
        
        # ========== 文件菜单 ==========
        file_menu = menubar.addMenu("文件(&F)")
        
        # 加载直播源
        load_source_action = QAction("加载直播源(&L)...", self)
        load_source_action.setShortcut(QKeySequence("Ctrl+O"))
        load_source_action.triggered.connect(self._show_source_dialog)
        file_menu.addAction(load_source_action)
        
        # 刷新频道
        refresh_action = QAction("刷新频道列表(&R)", self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self._show_source_dialog)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        # 清除缓存
        clear_cache_action = QAction("清除缓存(&C)", self)
        clear_cache_action.triggered.connect(self._clear_cache)
        file_menu.addAction(clear_cache_action)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # ========== 设置菜单 ==========
        settings_menu = menubar.addMenu("设置(&S)")
        
        # 代理设置
        proxy_action = QAction("代理设置(&P)...", self)
        proxy_action.triggered.connect(self._show_proxy_dialog)
        settings_menu.addAction(proxy_action)
        
        # MPV 播放器设置
        mpv_action = QAction("MPV 播放器设置(&M)...", self)
        mpv_action.triggered.connect(self._show_mpv_dialog)
        settings_menu.addAction(mpv_action)
        
        # ========== 播放菜单 ==========
        play_menu = menubar.addMenu("播放(&P)")
        
        play_action = QAction("播放/暂停", self)
        play_action.setShortcut(QKeySequence("Space"))
        play_action.triggered.connect(lambda: self._player._toggle_play())
        play_menu.addAction(play_action)
        
        stop_action = QAction("停止", self)
        stop_action.setShortcut(QKeySequence("S"))
        stop_action.triggered.connect(self._player.stop)
        play_menu.addAction(stop_action)
        
        play_menu.addSeparator()
        
        prev_action = QAction("上一个信号源", self)
        prev_action.setShortcut(QKeySequence("Left"))
        prev_action.triggered.connect(self._prev_source)
        play_menu.addAction(prev_action)
        
        next_action = QAction("下一个信号源", self)
        next_action.setShortcut(QKeySequence("Right"))
        next_action.triggered.connect(self._next_source)
        play_menu.addAction(next_action)
        
        play_menu.addSeparator()
        
        fullscreen_action = QAction("全屏(&F)", self)
        fullscreen_action.setShortcut(QKeySequence("F11"))
        fullscreen_action.triggered.connect(self._player.toggle_fullscreen)
        play_menu.addAction(fullscreen_action)
        
        # ========== 帮助菜单 ==========
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _init_statusbar(self):
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("就绪 - 按 Ctrl+O 加载直播源")
    
    def _connect_signals(self):
        # 频道列表
        self._channel_list.channel_selected.connect(self._on_channel_selected)
        self._channel_list.channel_double_clicked.connect(self._on_channel_play)
        
        # 播放器
        self._player.playback_error.connect(self._on_playback_error)
        self._player.fullscreen_toggled.connect(self._on_fullscreen_toggled)
    
    def _load_settings(self):
        """加载设置"""
        settings = cache_manager.load_settings()
        self._proxy_enabled = settings.get("proxy_enabled", False)
        self._proxy_host = settings.get("proxy_host", "127.0.0.1")
        self._proxy_port = settings.get("proxy_port", 7890)
        
        # 应用代理设置
        self._apply_proxy_settings()
    
    def _save_settings(self):
        """保存设置"""
        cache_manager.save_settings({
            "proxy_enabled": self._proxy_enabled,
            "proxy_host": self._proxy_host,
            "proxy_port": self._proxy_port,
        })
    
    def _apply_proxy_settings(self):
        """应用代理设置"""
        self._http_service.set_proxy(self._proxy_enabled, self._proxy_host, self._proxy_port)
        if self._proxy_enabled:
            self._player.set_proxy(f"{self._proxy_host}:{self._proxy_port}")
        else:
            self._player.set_proxy(None)
    
    def _load_cached_channels(self):
        """加载缓存的频道列表"""
        if cache_manager.has_channels_cache():
            groups, source_info = cache_manager.load_channels()
            if groups:
                self._channel_list.set_channels(groups)
                source_name = source_info.get("name", "缓存")
                self._statusbar.showMessage(f"已从缓存加载 {len(groups)} 个频道 ({source_name})")
                
                # 加载 EPG 源
                epg_sources = self._source_service.get_epg_sources()
                self._epg_panel.set_epg_sources(epg_sources)
    
    # ========== 菜单操作 ==========
    
    def _show_source_dialog(self):
        """显示加载直播源对话框"""
        dialog = SourceDialog(self._http_service, self)
        dialog.channels_loaded.connect(self._on_channels_loaded)
        dialog.exec()
    
    def _show_proxy_dialog(self):
        """显示代理设置对话框"""
        dialog = ProxyDialog(
            self,
            enabled=self._proxy_enabled,
            host=self._proxy_host,
            port=self._proxy_port,
        )
        dialog.settings_changed.connect(self._on_proxy_changed)
        dialog.exec()
    
    def _show_mpv_dialog(self):
        """显示 MPV 设置对话框"""
        dialog = MpvDialog(self)
        dialog.exec()
    
    def _on_proxy_changed(self, enabled: bool, host: str, port: int):
        """代理设置变更"""
        self._proxy_enabled = enabled
        self._proxy_host = host
        self._proxy_port = port
        self._apply_proxy_settings()
        self._save_settings()
        
        if enabled:
            self._statusbar.showMessage(f"代理已启用: {host}:{port}")
        else:
            self._statusbar.showMessage("代理已禁用")
    
    def _clear_cache(self):
        """清除缓存"""
        reply = QMessageBox.question(
            self, "清除缓存",
            "确定要清除所有缓存吗？\n包括频道列表和 EPG 数据。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            cache_manager.clear_channels_cache()
            cache_manager.clear_epg_cache()
            self._channel_list.set_channels([])
            self._epg_panel.clear()
            self._statusbar.showMessage("缓存已清除")
    
    # ========== 频道操作 ==========
    
    def _on_channels_loaded(self, groups: list[ChannelGroup], source_name: str):
        """频道加载完成"""
        self._channel_list.set_channels(groups)
        self._statusbar.showMessage(f"已加载 {len(groups)} 个频道 ({source_name})")
        
        # 保存到缓存
        cache_manager.save_channels(groups, {"name": source_name})
        
        # 加载 EPG 源
        epg_sources = self._source_service.get_epg_sources()
        self._epg_panel.set_epg_sources(epg_sources)
    
    def _on_channel_selected(self, group: ChannelGroup):
        """频道选中"""
        self._current_channel = group
        self._epg_panel.set_current_channel(group.name, group.tvg_id)
        self._statusbar.showMessage(f"选中: {group.name} ({group.source_count} 个信号源)")
    
    def _on_channel_play(self, group: ChannelGroup):
        """双击播放频道"""
        self._current_channel = group
        sources = [(ch.source_name, ch.url) for ch in group.channels]
        self._player.set_sources(sources, 0)
        self._epg_panel.set_current_channel(group.name, group.tvg_id)
        self._statusbar.showMessage(f"正在播放: {group.name}")
    
    def _on_playback_error(self, error: str):
        self._statusbar.showMessage(f"播放错误: {error}")
    
    def _on_fullscreen_toggled(self, is_fullscreen: bool):
        """全屏状态变化"""
        if is_fullscreen:
            # 全屏时隐藏其他面板
            self._channel_list.hide()
            self._epg_panel.hide()
            self.menuBar().hide()
            self._statusbar.hide()
        else:
            # 退出全屏时恢复
            self._channel_list.show()
            self._epg_panel.show()
            self.menuBar().show()
            self._statusbar.show()
            
            # 重新将播放器添加到布局
            self._splitter.insertWidget(1, self._player)
            self._splitter.setSizes([220, 700, 260])
    
    def _prev_source(self):
        if self._player.source_count > 1:
            index = (self._player.current_source_index - 1) % self._player.source_count
            self._player.switch_source(index)
    
    def _next_source(self):
        if self._player.source_count > 1:
            index = (self._player.current_source_index + 1) % self._player.source_count
            self._player.switch_source(index)
    
    def _show_about(self):
        QMessageBox.about(
            self,
            "关于 IPTV Player",
            "<h3>IPTV Player</h3>"
            "<p>基于 PySide6 + MPV 的 IPTV 桌面客户端</p>"
            "<p><b>功能特性:</b></p>"
            "<ul>"
            "<li>支持 M3U/M3U8 直播源</li>"
            "<li>支持 H.264/H.265/AV1 编码</li>"
            "<li>支持 EPG 节目单</li>"
            "<li>多信号源切换</li>"
            "<li>频道/EPG 本地缓存</li>"
            "<li>代理支持</li>"
            "<li>全屏播放 (F11/双击)</li>"
            "</ul>"
            "<p><b>快捷键:</b></p>"
            "<ul>"
            "<li>Ctrl+O - 加载直播源</li>"
            "<li>Space - 播放/暂停</li>"
            "<li>←/→ - 切换信号源</li>"
            "<li>F11 - 全屏</li>"
            "<li>ESC - 退出全屏</li>"
            "</ul>"
            "<p>版本: 1.0.0</p>"
        )
    
    def closeEvent(self, event):
        self._player.stop()
        super().closeEvent(event)
