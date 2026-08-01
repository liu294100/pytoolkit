"""代理设置对话框"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QCheckBox, QLineEdit, QSpinBox, QPushButton, QLabel
)
from PySide6.QtCore import Signal


class ProxyDialog(QDialog):
    """代理设置对话框"""
    
    # 设置变更信号
    settings_changed = Signal(bool, str, int)  # (enabled, host, port)
    
    def __init__(self, parent=None, enabled: bool = False, host: str = "127.0.0.1", port: int = 7890):
        super().__init__(parent)
        self._enabled = enabled
        self._host = host
        self._port = port
        
        self.setWindowTitle("代理设置")
        self.setFixedSize(350, 180)
        self.setModal(True)
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 启用开关
        self._chk_enabled = QCheckBox("启用代理")
        self._chk_enabled.setChecked(self._enabled)
        self._chk_enabled.stateChanged.connect(self._on_enabled_changed)
        layout.addWidget(self._chk_enabled)
        
        # 代理地址
        form_layout = QFormLayout()
        
        self._input_host = QLineEdit(self._host)
        self._input_host.setPlaceholderText("127.0.0.1")
        self._input_host.setEnabled(self._enabled)
        form_layout.addRow("主机:", self._input_host)
        
        self._input_port = QSpinBox()
        self._input_port.setRange(1, 65535)
        self._input_port.setValue(self._port)
        self._input_port.setEnabled(self._enabled)
        form_layout.addRow("端口:", self._input_port)
        
        layout.addLayout(form_layout)
        
        # 说明
        hint = QLabel("代理适用于上游源有地域限制或需要翻墙的情况")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        
        layout.addStretch()
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_ok = QPushButton("确定")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._on_ok)
        btn_layout.addWidget(btn_ok)
        
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)
    
    def _on_enabled_changed(self, state):
        enabled = self._chk_enabled.isChecked()
        self._input_host.setEnabled(enabled)
        self._input_port.setEnabled(enabled)
    
    def _on_ok(self):
        enabled = self._chk_enabled.isChecked()
        host = self._input_host.text().strip() or "127.0.0.1"
        port = self._input_port.value()
        
        self.settings_changed.emit(enabled, host, port)
        self.accept()
    
    def get_settings(self) -> tuple[bool, str, int]:
        """获取当前设置"""
        return (
            self._chk_enabled.isChecked(),
            self._input_host.text().strip() or "127.0.0.1",
            self._input_port.value(),
        )
