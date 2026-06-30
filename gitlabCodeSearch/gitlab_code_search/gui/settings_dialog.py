"""Settings dialog for application configuration."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QComboBox, QPushButton, QCheckBox,
    QLabel, QFileDialog, QGroupBox, QDialogButtonBox,
    QMessageBox,
)

from ..model.config import AppConfig
from ..service.search_service import SearchService


class SettingsDialog(QDialog):
    """Settings dialog for configuring GitLab connection and app preferences."""

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self._config = config
        self._setup_ui()
        self._load_values()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- GitLab Connection ---
        gitlab_group = QGroupBox("GitLab Connection")
        gitlab_layout = QFormLayout(gitlab_group)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://gitlab.example.com")
        gitlab_layout.addRow("GitLab URL:", self._url_input)

        self._token_input = QLineEdit()
        self._token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._token_input.setPlaceholderText("Personal Access Token")
        gitlab_layout.addRow("Token:", self._token_input)

        # Proxy
        self._proxy_enabled_cb = QCheckBox("Enable Proxy")
        gitlab_layout.addRow("", self._proxy_enabled_cb)

        self._proxy_input = QLineEdit()
        self._proxy_input.setPlaceholderText("http://127.0.0.1:7890")
        gitlab_layout.addRow("Proxy:", self._proxy_input)

        # Toggle proxy input enabled state based on checkbox
        self._proxy_enabled_cb.toggled.connect(self._proxy_input.setEnabled)

        # Show/hide token
        token_btn_layout = QHBoxLayout()
        self._show_token_btn = QPushButton("Show")
        self._show_token_btn.setCheckable(True)
        self._show_token_btn.setMaximumWidth(60)
        self._show_token_btn.toggled.connect(self._toggle_token_visibility)
        token_btn_layout.addStretch()
        token_btn_layout.addWidget(self._show_token_btn)
        gitlab_layout.addRow("", token_btn_layout)

        layout.addWidget(gitlab_group)

        # --- Paths ---
        paths_group = QGroupBox("Storage")
        paths_layout = QFormLayout(paths_group)

        clone_layout = QHBoxLayout()
        self._clone_dir_input = QLineEdit()
        self._clone_dir_input.setPlaceholderText("./cache")
        clone_layout.addWidget(self._clone_dir_input)
        browse_btn = QPushButton("Browse...")
        browse_btn.setMaximumWidth(80)
        browse_btn.clicked.connect(self._browse_clone_dir)
        clone_layout.addWidget(browse_btn)
        paths_layout.addRow("Clone Folder:", clone_layout)

        layout.addWidget(paths_group)

        # --- Performance ---
        perf_group = QGroupBox("Performance")
        perf_layout = QFormLayout(perf_group)

        self._thread_spin = QSpinBox()
        self._thread_spin.setRange(1, 32)
        self._thread_spin.setToolTip("Number of parallel search threads")
        perf_layout.addRow("Thread Count:", self._thread_spin)

        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(5, 300)
        self._timeout_spin.setSuffix(" sec")
        perf_layout.addRow("Search Timeout:", self._timeout_spin)

        self._max_results_spin = QSpinBox()
        self._max_results_spin.setRange(100, 10000)
        self._max_results_spin.setSingleStep(100)
        perf_layout.addRow("Max Results/Project:", self._max_results_spin)

        self._context_spin = QSpinBox()
        self._context_spin.setRange(3, 50)
        self._context_spin.setToolTip("Lines of context around match in preview")
        perf_layout.addRow("Context Lines:", self._context_spin)

        self._sync_interval_spin = QSpinBox()
        self._sync_interval_spin.setRange(5, 1440)
        self._sync_interval_spin.setSuffix(" min")
        perf_layout.addRow("Auto Sync Interval:", self._sync_interval_spin)

        layout.addWidget(perf_group)

        # --- Ripgrep ---
        rg_group = QGroupBox("Ripgrep")
        rg_layout = QFormLayout(rg_group)

        rg_path_layout = QHBoxLayout()
        self._rg_path_input = QLineEdit()
        self._rg_path_input.setPlaceholderText("rg")
        rg_path_layout.addWidget(self._rg_path_input)

        self._rg_test_btn = QPushButton("Test")
        self._rg_test_btn.setMaximumWidth(60)
        self._rg_test_btn.clicked.connect(self._test_ripgrep)
        rg_path_layout.addWidget(self._rg_test_btn)
        rg_layout.addRow("rg Path:", rg_path_layout)

        self._rg_status = QLabel("")
        rg_layout.addRow("", self._rg_status)

        layout.addWidget(rg_group)

        # --- Theme ---
        theme_group = QGroupBox("Appearance")
        theme_layout = QFormLayout(theme_group)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["dark", "light"])
        theme_layout.addRow("Theme:", self._theme_combo)

        layout.addWidget(theme_group)

        # --- Buttons ---
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_values(self) -> None:
        """Load current config values into fields."""
        self._url_input.setText(self._config.gitlab_url)
        self._token_input.setText(self._config.token)
        self._proxy_enabled_cb.setChecked(self._config.proxy_enabled)
        self._proxy_input.setText(self._config.proxy)
        self._proxy_input.setEnabled(self._config.proxy_enabled)
        self._clone_dir_input.setText(self._config.clone_folder)
        self._thread_spin.setValue(self._config.thread_count)
        self._timeout_spin.setValue(self._config.search_timeout)
        self._max_results_spin.setValue(self._config.max_results_per_project)
        self._context_spin.setValue(self._config.context_lines)
        self._sync_interval_spin.setValue(self._config.auto_sync_interval_minutes)
        self._rg_path_input.setText(self._config.rg_path)

        idx = self._theme_combo.findText(self._config.theme)
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)

    def _on_accept(self) -> None:
        """Save settings and close."""
        self._config.gitlab_url = self._url_input.text().strip().rstrip("/")
        self._config.token = self._token_input.text().strip()
        self._config.proxy_enabled = self._proxy_enabled_cb.isChecked()
        self._config.proxy = self._proxy_input.text().strip()
        self._config.clone_folder = self._clone_dir_input.text().strip() or "./cache"
        self._config.thread_count = self._thread_spin.value()
        self._config.search_timeout = self._timeout_spin.value()
        self._config.max_results_per_project = self._max_results_spin.value()
        self._config.context_lines = self._context_spin.value()
        self._config.auto_sync_interval_minutes = self._sync_interval_spin.value()
        self._config.rg_path = self._rg_path_input.text().strip() or "rg"
        self._config.theme = self._theme_combo.currentText()
        self.accept()

    def _toggle_token_visibility(self, checked: bool) -> None:
        if checked:
            self._token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_token_btn.setText("Hide")
        else:
            self._token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_token_btn.setText("Show")

    def _browse_clone_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Clone Directory")
        if path:
            self._clone_dir_input.setText(path)

    def _test_ripgrep(self) -> None:
        """Test if ripgrep is accessible."""
        rg_path = self._rg_path_input.text().strip() or "rg"
        if SearchService.check_rg_available(rg_path):
            self._rg_status.setText("✓ ripgrep found")
            self._rg_status.setStyleSheet("color: #4caf50;")
        else:
            self._rg_status.setText("✗ ripgrep not found")
            self._rg_status.setStyleSheet("color: #f44336;")
