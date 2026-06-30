"""Search panel widget - left side controls."""
from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QRadioButton,
    QButtonGroup, QGroupBox, QCompleter,
)


class SearchPanel(QWidget):
    """Left panel with search controls and filters."""

    search_requested = Signal()  # Emitted when user clicks Search or presses Enter
    sync_requested = Signal()   # Emitted when user clicks Sync

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(280)
        self.setMaximumWidth(350)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # --- Keyword ---
        keyword_label = QLabel("Keyword")
        keyword_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(keyword_label)

        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("Enter search term...")
        self.keyword_input.setClearButtonEnabled(True)
        self.keyword_input.returnPressed.connect(self.search_requested.emit)
        layout.addWidget(self.keyword_input)

        # Search button
        btn_layout = QHBoxLayout()
        self.search_btn = QPushButton("Search")
        self.search_btn.setMinimumHeight(32)
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                padding: 6px 16px;
            }
            QPushButton:hover { background-color: #0b5ed7; }
            QPushButton:pressed { background-color: #0a58ca; }
            QPushButton:disabled { background-color: #6c757d; }
        """)
        self.search_btn.clicked.connect(self.search_requested.emit)
        btn_layout.addWidget(self.search_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumHeight(32)
        self.cancel_btn.setVisible(False)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        # --- Filters ---
        filter_group = QGroupBox("Filters")
        filter_layout = QVBoxLayout(filter_group)
        filter_layout.setSpacing(8)

        # Group filter
        filter_layout.addWidget(QLabel("Group"))
        self.group_combo = QComboBox()
        self.group_combo.addItem("All", None)
        self.group_combo.setMinimumHeight(28)
        filter_layout.addWidget(self.group_combo)

        # Project filter
        filter_layout.addWidget(QLabel("Project"))
        self.project_combo = QComboBox()
        self.project_combo.addItem("All", None)
        self.project_combo.setMinimumHeight(28)
        self.project_combo.setEditable(True)
        self.project_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        filter_layout.addWidget(self.project_combo)

        # Branch
        filter_layout.addWidget(QLabel("Branch"))
        self.branch_combo = QComboBox()
        self.branch_combo.addItem("master")
        self.branch_combo.setEditable(True)
        self.branch_combo.setMinimumHeight(28)
        filter_layout.addWidget(self.branch_combo)

        # Branch mode
        branch_mode_layout = QHBoxLayout()
        self.branch_group = QButtonGroup(self)
        self.radio_current = QRadioButton("Current")
        self.radio_all = QRadioButton("All Branches")
        self.radio_current.setChecked(True)
        self.branch_group.addButton(self.radio_current, 0)
        self.branch_group.addButton(self.radio_all, 1)
        branch_mode_layout.addWidget(self.radio_current)
        branch_mode_layout.addWidget(self.radio_all)
        filter_layout.addLayout(branch_mode_layout)

        # File type
        filter_layout.addWidget(QLabel("File Pattern"))
        self.filetype_combo = QComboBox()
        self.filetype_combo.setEditable(True)
        self.filetype_combo.setMinimumHeight(28)
        self.filetype_combo.addItems([
            "", "*.java", "*.py", "*.ts", "*.js", "*.xml",
            "*.sql", "*.go", "*.yml", "*.yaml", "*.json",
            "*.kt", "*.scala", "*.rs", "*.cpp", "*.h",
        ])
        filter_layout.addWidget(self.filetype_combo)

        layout.addWidget(filter_group)

        # --- Options ---
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)

        self.regex_check = QCheckBox("Regex")
        self.whole_word_check = QCheckBox("Whole Word")
        self.ignore_case_check = QCheckBox("Ignore Case")
        self.ignore_case_check.setChecked(True)

        options_layout.addWidget(self.regex_check)
        options_layout.addWidget(self.whole_word_check)
        options_layout.addWidget(self.ignore_case_check)

        layout.addWidget(options_group)

        # --- Sync button ---
        self.sync_btn = QPushButton("⟳ Sync (filtered)")
        self.sync_btn.setMinimumHeight(30)
        self.sync_btn.setToolTip("Sync repos matching the Group/Project filter above.\nSelect 'All' to sync everything.")
        self.sync_btn.clicked.connect(self.sync_requested.emit)
        layout.addWidget(self.sync_btn)

        # Spacer
        layout.addStretch()

    def set_searching(self, searching: bool) -> None:
        """Toggle UI state between searching and idle."""
        self.search_btn.setVisible(not searching)
        self.cancel_btn.setVisible(searching)
        self.keyword_input.setEnabled(not searching)

    def get_keyword(self) -> str:
        return self.keyword_input.text().strip()

    def get_group(self) -> str | None:
        return self.group_combo.currentData()

    def get_project(self) -> str | None:
        data = self.project_combo.currentData()
        if data:
            return data
        # If user typed a name, try to match
        text = self.project_combo.currentText()
        if text and text != "All":
            return text
        return None

    def get_branch(self) -> str:
        return self.branch_combo.currentText() or "master"

    def is_all_branches(self) -> bool:
        return self.radio_all.isChecked()

    def get_file_pattern(self) -> str:
        return self.filetype_combo.currentText().strip()

    def is_regex(self) -> bool:
        return self.regex_check.isChecked()

    def is_whole_word(self) -> bool:
        return self.whole_word_check.isChecked()

    def is_ignore_case(self) -> bool:
        return self.ignore_case_check.isChecked()

    def set_groups(self, groups: list[tuple[str, int]]) -> None:
        """Populate group combo. groups: list of (name, id)."""
        self.group_combo.clear()
        self.group_combo.addItem("All", None)
        for name, gid in groups:
            self.group_combo.addItem(name, gid)

    def set_projects(self, projects: list[tuple[str, str]]) -> None:
        """Populate project combo. projects: list of (display_name, path_with_namespace)."""
        self.project_combo.clear()
        self.project_combo.addItem("All", None)
        for display, path in projects:
            self.project_combo.addItem(display, path)

    def set_branches(self, branches: list[str]) -> None:
        """Populate branch combo."""
        current = self.branch_combo.currentText()
        self.branch_combo.clear()
        self.branch_combo.addItems(branches)
        # Restore selection if possible
        idx = self.branch_combo.findText(current)
        if idx >= 0:
            self.branch_combo.setCurrentIndex(idx)

    def set_history_completer(self, keywords: list[str]) -> None:
        """Set autocomplete from search history."""
        completer = QCompleter(keywords, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.keyword_input.setCompleter(completer)
