#!/usr/bin/env python3
"""IPTV Desktop Client - 基于 PySide6 + MPV 的桌面客户端"""

import os
import sys
from pathlib import Path


def get_base_path() -> Path:
    """获取基础路径，支持 PyInstaller 打包"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后
        return Path(sys._MEIPASS)
    else:
        # 开发模式
        return Path(__file__).parent


def get_app_path() -> Path:
    """获取应用程序所在目录（用于写入数据）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，使用 exe 所在目录
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent


# 设置基础路径
BASE_PATH = get_base_path()
APP_PATH = get_app_path()

# 确保包可以导入
if str(BASE_PATH) not in sys.path:
    sys.path.insert(0, str(BASE_PATH))
if str(BASE_PATH.parent) not in sys.path:
    sys.path.insert(0, str(BASE_PATH.parent))

# 设置 MPV DLL 路径（打包后需要）
mpv_path = BASE_PATH / "mpv"
if mpv_path.exists():
    os.environ["PATH"] = str(mpv_path) + os.pathsep + os.environ.get("PATH", "")

# Windows 任务栏图标支持
if sys.platform == "win32":
    try:
        import ctypes
        # 设置 AppUserModelID，让 Windows 识别为独立应用
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("IPTV.Player.1.0")
    except Exception:
        pass

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon

from iptvgui.ui.main_window import MainWindow


def main():
    # 高 DPI 支持 (PySide6 默认启用)
    app = QApplication(sys.argv)
    app.setApplicationName("IPTV Player")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("IPTV")
    
    # 设置应用图标（窗口和任务栏）
    icon_path = BASE_PATH / "resources" / "icon.ico"
    if icon_path.exists():
        icon = QIcon(str(icon_path))
        app.setWindowIcon(icon)
    
    # 设置默认字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    # 加载样式表
    style_path = BASE_PATH / "resources" / "style.qss"
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding="utf-8"))
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
