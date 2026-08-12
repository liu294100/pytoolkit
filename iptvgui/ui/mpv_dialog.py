"""MPV 设置对话框 - 配置 DLL 路径、下载默认 DLL"""

import os
import sys
import shutil
import tempfile
from pathlib import Path
from threading import Thread

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton,
    QPushButton, QLabel, QLineEdit, QFileDialog, QProgressBar,
    QMessageBox, QButtonGroup, QFrame
)
from PySide6.QtCore import Qt, Signal, QObject

from ..services.cache_manager import cache_manager


# 下载相关配置
MPV_RELEASE_API = "https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/latest"
MPV_FALLBACK_URL = "https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20260610/mpv-dev-x86_64-v3-20260610-git-304426c.7z"
MPV_DLL_NAME = "libmpv-2.dll"


class DownloadSignals(QObject):
    """下载过程的信号"""
    progress = Signal(int, str)  # 进度百分比, 状态信息
    finished = Signal(bool, str)  # 成功与否, 消息


class MpvDialog(QDialog):
    """MPV 设置对话框"""
    
    # 配置变更信号（需要重启才能生效）
    config_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._download_thread: Thread | None = None
        self._download_signals = DownloadSignals()
        
        self._init_ui()
        self._load_config()
        self._connect_signals()
    
    def _init_ui(self):
        self.setWindowTitle("MPV 播放器设置")
        self.setMinimumWidth(550)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # ========== 当前状态 ==========
        status_group = QGroupBox("当前状态")
        status_layout = QVBoxLayout(status_group)
        
        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        status_layout.addWidget(self._status_label)
        
        layout.addWidget(status_group)
        
        # ========== DLL 路径选择 ==========
        path_group = QGroupBox("MPV DLL 路径")
        path_layout = QVBoxLayout(path_group)
        
        # 选项组
        self._path_button_group = QButtonGroup(self)
        
        # 选项 1：默认位置
        self._radio_default = QRadioButton("使用默认位置（推荐）")
        self._path_button_group.addButton(self._radio_default, 0)
        path_layout.addWidget(self._radio_default)
        
        # 默认位置说明
        default_dir = cache_manager.get_default_mpv_dir()
        default_label = QLabel(f"    路径: {default_dir}")
        default_label.setStyleSheet("color: #888; font-size: 11px;")
        path_layout.addWidget(default_label)
        
        path_layout.addSpacing(10)
        
        # 选项 2：自定义路径
        self._radio_custom = QRadioButton("使用自定义路径")
        self._path_button_group.addButton(self._radio_custom, 1)
        path_layout.addWidget(self._radio_custom)
        
        # 自定义路径输入
        custom_layout = QHBoxLayout()
        custom_layout.setContentsMargins(20, 5, 0, 0)
        
        self._custom_path_edit = QLineEdit()
        self._custom_path_edit.setPlaceholderText("选择 libmpv-2.dll 文件路径...")
        self._custom_path_edit.setEnabled(False)
        custom_layout.addWidget(self._custom_path_edit)
        
        self._btn_browse = QPushButton("浏览...")
        self._btn_browse.setEnabled(False)
        self._btn_browse.clicked.connect(self._browse_dll)
        custom_layout.addWidget(self._btn_browse)
        
        path_layout.addLayout(custom_layout)
        
        layout.addWidget(path_group)
        
        # ========== 下载 DLL ==========
        download_group = QGroupBox("下载 MPV DLL")
        download_layout = QVBoxLayout(download_group)
        
        download_desc = QLabel(
            '如果默认位置没有 DLL 文件，可以点击下方按钮自动下载。<br>'
            '下载源: <a href="https://github.com/shinchiro/mpv-winbuild-cmake/releases/" '
            'style="color: #60a5fa;">GitHub (shinchiro/mpv-winbuild-cmake)</a>'
        )
        download_desc.setWordWrap(True)
        download_desc.setOpenExternalLinks(True)  # 允许点击打开外部链接
        download_desc.setStyleSheet("color: #888;")
        download_layout.addWidget(download_desc)
        
        # 下载按钮和进度条
        download_btn_layout = QHBoxLayout()
        
        self._btn_download = QPushButton("下载到默认位置")
        self._btn_download.setMinimumWidth(150)
        self._btn_download.clicked.connect(self._start_download)
        download_btn_layout.addWidget(self._btn_download)
        
        download_btn_layout.addStretch()
        
        download_layout.addLayout(download_btn_layout)
        
        # 进度条
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        download_layout.addWidget(self._progress_bar)
        
        # 下载状态
        self._download_status = QLabel()
        self._download_status.setVisible(False)
        self._download_status.setStyleSheet("color: #888;")
        download_layout.addWidget(self._download_status)
        
        layout.addWidget(download_group)
        
        # ========== 提示 ==========
        hint_frame = QFrame()
        hint_frame.setStyleSheet("background-color: #2a2a3e; padding: 10px; border-radius: 5px;")
        hint_layout = QVBoxLayout(hint_frame)
        hint_layout.setContentsMargins(10, 10, 10, 10)
        
        hint_label = QLabel("⚠️ 修改 MPV 路径后需要重启程序才能生效")
        hint_label.setStyleSheet("color: #ffa500;")
        hint_layout.addWidget(hint_label)
        
        layout.addWidget(hint_frame)
        
        # ========== 按钮 ==========
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self._btn_save = QPushButton("保存")
        self._btn_save.setMinimumWidth(80)
        self._btn_save.clicked.connect(self._save_config)
        btn_layout.addWidget(self._btn_save)
        
        self._btn_cancel = QPushButton("取消")
        self._btn_cancel.setMinimumWidth(80)
        self._btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self._btn_cancel)
        
        layout.addLayout(btn_layout)
    
    def _connect_signals(self):
        # 路径选项变化
        self._path_button_group.idToggled.connect(self._on_path_option_changed)
        
        # 下载信号
        self._download_signals.progress.connect(self._on_download_progress)
        self._download_signals.finished.connect(self._on_download_finished)
    
    def _load_config(self):
        """加载当前配置"""
        config = cache_manager.load_mpv_config()
        
        # 更新状态标签
        effective_path = config.get("effective_dll_path")
        if effective_path and Path(effective_path).exists():
            size_mb = Path(effective_path).stat().st_size / 1024 / 1024
            self._status_label.setText(
                f"✅ MPV 已配置\n"
                f"当前使用: {effective_path}\n"
                f"文件大小: {size_mb:.1f} MB"
            )
            self._status_label.setStyleSheet("color: #4ade80;")
        else:
            self._status_label.setText(
                "❌ MPV 未配置\n"
                "请下载或选择 libmpv-2.dll 文件"
            )
            self._status_label.setStyleSheet("color: #f87171;")
        
        # 设置路径选项
        custom_path = config.get("custom_dll_path")
        if custom_path and config.get("using_custom"):
            self._radio_custom.setChecked(True)
            self._custom_path_edit.setText(custom_path)
        else:
            self._radio_default.setChecked(True)
            if custom_path:
                self._custom_path_edit.setText(custom_path)
    
    def _on_path_option_changed(self, button_id: int, checked: bool):
        """路径选项变化"""
        if not checked:
            return
        
        is_custom = (button_id == 1)
        self._custom_path_edit.setEnabled(is_custom)
        self._btn_browse.setEnabled(is_custom)
    
    def _browse_dll(self):
        """浏览选择 DLL 文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 libmpv-2.dll",
            "",
            "DLL 文件 (libmpv-2.dll);;所有文件 (*.*)"
        )
        
        if file_path:
            # 验证文件名
            if not file_path.lower().endswith("libmpv-2.dll"):
                QMessageBox.warning(
                    self, "文件错误",
                    "请选择名为 libmpv-2.dll 的文件"
                )
                return
            
            self._custom_path_edit.setText(file_path)
    
    def _save_config(self):
        """保存配置"""
        if self._radio_custom.isChecked():
            custom_path = self._custom_path_edit.text().strip()
            
            if not custom_path:
                QMessageBox.warning(self, "错误", "请选择自定义 DLL 路径")
                return
            
            if not Path(custom_path).exists():
                QMessageBox.warning(self, "错误", f"文件不存在: {custom_path}")
                return
            
            cache_manager.save_mpv_config(custom_path)
        else:
            # 使用默认位置
            cache_manager.save_mpv_config(None)
        
        self.config_changed.emit()
        
        QMessageBox.information(
            self, "保存成功",
            "MPV 配置已保存。\n请重启程序使配置生效。"
        )
        
        self.accept()
    
    # ========== 下载功能 ==========
    
    def _start_download(self):
        """开始下载"""
        if self._download_thread and self._download_thread.is_alive():
            return
        
        # 确认下载
        default_dir = cache_manager.get_default_mpv_dir()
        reply = QMessageBox.question(
            self, "确认下载",
            f"将下载 libmpv-2.dll 到:\n{default_dir}\n\n"
            "文件约 110MB，是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 显示进度
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        self._download_status.setVisible(True)
        self._download_status.setText("准备下载...")
        self._btn_download.setEnabled(False)
        
        # 启动下载线程
        self._download_thread = Thread(target=self._download_worker, daemon=True)
        self._download_thread.start()
    
    def _download_worker(self):
        """下载工作线程"""
        try:
            # 安装依赖
            self._download_signals.progress.emit(0, "检查依赖...")
            
            try:
                import requests
            except ImportError:
                self._download_signals.progress.emit(0, "安装 requests...")
                os.system(f"{sys.executable} -m pip install requests -q")
                import requests
            
            try:
                import py7zr
            except ImportError:
                self._download_signals.progress.emit(0, "安装 py7zr...")
                os.system(f"{sys.executable} -m pip install py7zr -q")
                import py7zr
            
            # 获取下载 URL
            self._download_signals.progress.emit(5, "获取最新版本...")
            download_url = self._get_latest_release_url() or MPV_FALLBACK_URL
            
            # 下载到临时目录
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir = Path(tmpdir)
                archive_path = tmpdir / "mpv-dev.7z"
                
                # 下载
                self._download_signals.progress.emit(10, "下载中...")
                
                resp = requests.get(download_url, stream=True, timeout=60)
                resp.raise_for_status()
                
                total = int(resp.headers.get('content-length', 0))
                downloaded = 0
                
                with open(archive_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            # 下载进度 10% - 80%
                            pct = 10 + int(downloaded * 70 / total)
                            self._download_signals.progress.emit(
                                pct, 
                                f"下载中... {downloaded // 1024 // 1024}MB / {total // 1024 // 1024}MB"
                            )
                
                # 解压
                self._download_signals.progress.emit(85, "解压中...")
                
                target_dir = cache_manager.get_default_mpv_dir()
                target_dir.mkdir(parents=True, exist_ok=True)
                
                with py7zr.SevenZipFile(archive_path, 'r') as z:
                    # 找到 libmpv-2.dll
                    names = z.getnames()
                    target_file = None
                    for name in names:
                        if name.endswith(MPV_DLL_NAME):
                            target_file = name
                            break
                    
                    if not target_file:
                        self._download_signals.finished.emit(False, "压缩包中未找到 libmpv-2.dll")
                        return
                    
                    # 解压到临时目录
                    z.extract(path=tmpdir, targets=[target_file])
                    
                    # 移动到目标位置
                    extracted = tmpdir / target_file
                    dest = target_dir / MPV_DLL_NAME
                    
                    if dest.exists():
                        dest.unlink()
                    
                    shutil.move(str(extracted), str(dest))
                
                self._download_signals.progress.emit(100, "完成！")
                
                # 验证
                dll_path = target_dir / MPV_DLL_NAME
                if dll_path.exists():
                    size_mb = dll_path.stat().st_size / 1024 / 1024
                    self._download_signals.finished.emit(
                        True, 
                        f"下载完成！\n文件: {dll_path}\n大小: {size_mb:.1f} MB"
                    )
                else:
                    self._download_signals.finished.emit(False, "下载完成但文件未找到")
        
        except Exception as e:
            self._download_signals.finished.emit(False, f"下载失败: {e}")
    
    def _get_latest_release_url(self) -> str | None:
        """获取最新版本下载地址"""
        try:
            import requests
            resp = requests.get(MPV_RELEASE_API, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if "mpv-dev-x86_64" in name and name.endswith(".7z"):
                    return asset.get("browser_download_url")
        except Exception:
            pass
        return None
    
    def _on_download_progress(self, percent: int, status: str):
        """下载进度更新"""
        self._progress_bar.setValue(percent)
        self._download_status.setText(status)
    
    def _on_download_finished(self, success: bool, message: str):
        """下载完成"""
        self._btn_download.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "下载成功", message)
            # 刷新状态
            self._load_config()
            # 自动选择默认位置
            self._radio_default.setChecked(True)
        else:
            QMessageBox.warning(self, "下载失败", message)
        
        # 隐藏进度条（延迟一下让用户看到 100%）
        self._progress_bar.setVisible(False)
        self._download_status.setVisible(False)
