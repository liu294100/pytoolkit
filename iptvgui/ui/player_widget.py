"""MPV 播放器组件 - 支持全屏"""

import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QSlider, QPushButton,
    QLabel, QComboBox, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer, QPoint
from PySide6.QtGui import QMouseEvent, QKeyEvent, QIcon, QCursor

# 设置 mpv DLL 路径
if getattr(sys, 'frozen', False):
    MPV_DIR = Path(sys._MEIPASS) / "mpv"
else:
    MPV_DIR = Path(__file__).parent.parent / "mpv"

if MPV_DIR.exists():
    os.environ["PATH"] = str(MPV_DIR) + os.pathsep + os.environ.get("PATH", "")
    if sys.platform == "win32":
        try:
            os.add_dll_directory(str(MPV_DIR))
        except Exception:
            pass

try:
    import mpv
    MPV_AVAILABLE = True
except (ImportError, FileNotFoundError, OSError) as e:
    mpv = None
    MPV_AVAILABLE = False


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


class VideoFrame(QFrame):
    """视频渲染区域，支持双击全屏和鼠标移动检测"""
    
    double_clicked = Signal()
    mouse_moved = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        self.mouse_moved.emit()
        super().mouseMoveEvent(event)


class PlayerWidget(QWidget):
    """MPV 视频播放器组件"""
    
    # 信号
    playback_started = Signal()
    playback_stopped = Signal()
    playback_error = Signal(str)
    source_changed = Signal(int)
    fullscreen_toggled = Signal(bool)
    
    # 控制栏自动隐藏延迟（毫秒）
    CONTROL_BAR_HIDE_DELAY = 3000
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_url = ""
        self._sources: list[tuple[str, str]] = []
        self._current_source_index = 0
        self._proxy: str | None = None
        self._is_fullscreen = False
        self._parent_widget = None
        self._original_geometry = None
        
        self._player = None
        
        # 鼠标跟踪
        self.setMouseTracking(True)
        
        self._init_ui()
        self._init_mpv()
        self._init_timers()
    
    def _init_ui(self):
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        
        # 视频渲染区域
        self._video_frame = VideoFrame()
        self._video_frame.setStyleSheet("background-color: #1a1a2e;")
        self._video_frame.setMinimumSize(640, 360)
        self._video_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._video_frame.double_clicked.connect(self.toggle_fullscreen)
        self._video_frame.mouse_moved.connect(self._on_mouse_activity)
        self._video_frame.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        if not MPV_AVAILABLE:
            no_mpv_label = QLabel(
                "未找到 MPV 播放器\n\n"
                "请运行 download_mpv.bat 下载\n"
                "或手动下载 mpv 到 iptvgui/mpv/ 目录"
            )
            no_mpv_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_mpv_label.setStyleSheet("color: #888; font-size: 14px;")
            frame_layout = QVBoxLayout(self._video_frame)
            frame_layout.addWidget(no_mpv_label)
        
        self._main_layout.addWidget(self._video_frame, 1)
        
        # 控制栏
        self._control_bar = self._create_control_bar()
        self._main_layout.addWidget(self._control_bar)
    
    def _init_mpv(self):
        if not MPV_AVAILABLE:
            return
        
        try:
            self._player = mpv.MPV(
                wid=str(int(self._video_frame.winId())),
                vo="gpu",
                hwdec="auto",
                keep_open=True,
                idle=True,
                input_default_bindings=True,
                input_vo_keyboard=True,
                osc=False,
            )
            
            @self._player.event_callback("end-file")
            def on_end_file(event):
                try:
                    reason = getattr(event, 'reason', None) or getattr(event, 'event', {}).get('reason')
                    if reason == "error":
                        self.playback_error.emit("播放错误")
                except Exception:
                    pass
            
        except Exception as e:
            print(f"MPV 初始化失败: {e}")
            self._player = None
    
    def _create_control_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(40)
        bar.setStyleSheet("background-color: rgba(22, 33, 62, 0.9);")
        
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # 音量
        volume_label = QLabel("🔊")
        volume_label.setStyleSheet("color: #fff;")
        layout.addWidget(volume_label)
        
        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(80)
        self._volume_slider.setFixedWidth(100)
        self._volume_slider.valueChanged.connect(self._set_volume)
        layout.addWidget(self._volume_slider)
        
        layout.addStretch()
        
        # 信号源
        source_label = QLabel("信号源:")
        source_label.setStyleSheet("color: #fff;")
        layout.addWidget(source_label)
        
        self._source_combo = QComboBox()
        self._source_combo.setMinimumWidth(150)
        self._source_combo.currentIndexChanged.connect(self._on_source_changed)
        layout.addWidget(self._source_combo)
        
        # 全屏按钮
        self._btn_fullscreen = QPushButton("⛶ 全屏")
        self._btn_fullscreen.setMinimumWidth(70)
        self._btn_fullscreen.setToolTip("全屏 (F11 / 双击)")
        self._btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        layout.addWidget(self._btn_fullscreen)
        
        # 状态
        self._status_label = QLabel("就绪")
        self._status_label.setStyleSheet("color: #888; margin-left: 10px;")
        layout.addWidget(self._status_label)
        
        return bar
    
    def _init_timers(self):
        # 状态更新定时器
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_status)
        self._timer.start(1000)
        
        # 控制栏隐藏定时器
        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_control_bar)
    
    def _on_mouse_activity(self):
        """鼠标活动时显示控制栏"""
        if self._is_fullscreen:
            self._show_control_bar()
            self._hide_timer.start(self.CONTROL_BAR_HIDE_DELAY)
    
    def _show_control_bar(self):
        """显示控制栏"""
        if not self._control_bar.isVisible():
            self._control_bar.show()
        # 显示鼠标
        self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def _hide_control_bar(self):
        """隐藏控制栏（仅在全屏时）"""
        if self._is_fullscreen:
            self._control_bar.hide()
            # 隐藏鼠标
            self.setCursor(Qt.CursorShape.BlankCursor)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动事件"""
        self._on_mouse_activity()
        super().mouseMoveEvent(event)
    
    def _update_status(self):
        if not self._player:
            return
        try:
            idle = self._player.core_idle
            paused = self._player.pause
            
            if idle:
                if not self._current_url:
                    self._status_label.setText("就绪")
            elif paused:
                self._status_label.setText("已暂停")
            else:
                self._status_label.setText("播放中")
        except Exception:
            pass
    
    def play(self, url: str):
        if not self._player or not MPV_AVAILABLE:
            self.playback_error.emit("MPV 未初始化")
            return
        
        self._current_url = url
        self._status_label.setText("正在加载...")
        
        try:
            if self._proxy:
                self._player["http-proxy"] = self._proxy
            
            self._player["cache"] = "yes"
            self._player["cache-secs"] = 10
            self._player["demuxer-max-bytes"] = "50MiB"
            
            self._player.play(url)
            self.playback_started.emit()
        except Exception as e:
            self.playback_error.emit(f"播放失败: {e}")
    
    def stop(self):
        if self._player:
            try:
                self._player.stop()
            except Exception:
                pass
        self._current_url = ""
        self._status_label.setText("已停止")
        self.playback_stopped.emit()
    
    def _toggle_play(self):
        if not self._player:
            return
        try:
            if self._player.core_idle:
                if self._current_url:
                    self.play(self._current_url)
            else:
                self._player.pause = not self._player.pause
        except Exception:
            pass
    
    def _set_volume(self, value: int):
        if self._player:
            try:
                self._player.volume = value
            except Exception:
                pass
    
    def set_sources(self, sources: list[tuple[str, str]], play_index: int = 0):
        self._sources = sources
        self._current_source_index = play_index
        
        self._source_combo.blockSignals(True)
        self._source_combo.clear()
        for i, (name, url) in enumerate(sources):
            display_name = f"[{i+1}] {name}" if name else f"信号源 {i+1}"
            self._source_combo.addItem(display_name, url)
        
        if sources and 0 <= play_index < len(sources):
            self._source_combo.setCurrentIndex(play_index)
        self._source_combo.blockSignals(False)
        
        if sources and 0 <= play_index < len(sources):
            _, url = sources[play_index]
            self.play(url)
    
    def _on_source_changed(self, index: int):
        if 0 <= index < len(self._sources):
            self._current_source_index = index
            _, url = self._sources[index]
            self.play(url)
            self.source_changed.emit(index)
    
    def switch_source(self, index: int):
        if 0 <= index < len(self._sources):
            self._source_combo.setCurrentIndex(index)
    
    @property
    def current_source_index(self) -> int:
        return self._current_source_index
    
    @property
    def source_count(self) -> int:
        return len(self._sources)
    
    def set_proxy(self, proxy: str | None):
        self._proxy = f"http://{proxy}" if proxy else None
    
    # ========== 全屏相关 ==========
    
    def toggle_fullscreen(self):
        """切换全屏"""
        if self._is_fullscreen:
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()
    
    def enter_fullscreen(self):
        """进入全屏"""
        if self._is_fullscreen:
            return
        
        self._is_fullscreen = True
        self._parent_widget = self.parent()
        
        # 设置为独立窗口并全屏
        self.setParent(None)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        
        # 设置全屏窗口图标
        icon_path = _get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(str(icon_path)))
        
        self.showFullScreen()
        
        self._btn_fullscreen.setText("退出全屏")
        self._btn_fullscreen.setToolTip("退出全屏 (ESC / F11 / 双击)")
        
        # 启动隐藏定时器
        self._hide_timer.start(self.CONTROL_BAR_HIDE_DELAY)
        
        self.fullscreen_toggled.emit(True)
    
    def exit_fullscreen(self):
        """退出全屏"""
        if not self._is_fullscreen:
            return
        
        self._is_fullscreen = False
        
        # 停止隐藏定时器
        self._hide_timer.stop()
        
        # 显示控制栏和鼠标
        self._control_bar.show()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        
        # 恢复为子组件
        self.setWindowFlags(Qt.WindowType.Widget)
        self.showNormal()
        
        self._btn_fullscreen.setText("⛶ 全屏")
        self._btn_fullscreen.setToolTip("全屏 (F11 / 双击)")
        
        self.fullscreen_toggled.emit(False)
    
    @property
    def is_fullscreen(self) -> bool:
        return self._is_fullscreen
    
    def keyPressEvent(self, event: QKeyEvent):
        """键盘事件"""
        key = event.key()
        
        # 任何按键都触发鼠标活动（显示控制栏）
        self._on_mouse_activity()
        
        if key == Qt.Key.Key_Escape:
            if self._is_fullscreen:
                self.exit_fullscreen()
        elif key == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        elif key == Qt.Key.Key_Space:
            self._toggle_play()
        elif key == Qt.Key.Key_Left:
            # 上一个信号源
            if self.source_count > 1:
                index = (self._current_source_index - 1) % self.source_count
                self.switch_source(index)
        elif key == Qt.Key.Key_Right:
            # 下一个信号源
            if self.source_count > 1:
                index = (self._current_source_index + 1) % self.source_count
                self.switch_source(index)
        elif key == Qt.Key.Key_Up:
            # 增加音量
            new_vol = min(100, self._volume_slider.value() + 5)
            self._volume_slider.setValue(new_vol)
        elif key == Qt.Key.Key_Down:
            # 减少音量
            new_vol = max(0, self._volume_slider.value() - 5)
            self._volume_slider.setValue(new_vol)
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        if self._is_fullscreen:
            self.exit_fullscreen()
        if self._player:
            try:
                self._player.terminate()
            except Exception:
                pass
        super().closeEvent(event)

