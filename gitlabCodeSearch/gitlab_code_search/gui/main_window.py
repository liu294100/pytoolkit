"""Main application window."""
from __future__ import annotations

import logging
import webbrowser
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QStatusBar, QLabel, QMenuBar, QMessageBox,
    QProgressBar,
)

from ..model.config import AppConfig
from ..model.project import Project, Group
from ..model.result import SearchQuery, SearchResult, SearchResultItem
from ..service.gitlab_service import GitLabService
from ..service.git_service import GitService
from ..service.search_service import SearchService
from ..service.db_service import DBService
from .search_panel import SearchPanel
from .result_table import ResultTable
from .preview_panel import PreviewPanel
from .settings_dialog import SettingsDialog
from .workers import SearchWorker, SyncWorker, ConnectWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window with three-panel layout."""

    def __init__(self, config: AppConfig):
        super().__init__()
        self._config = config
        self._projects: list[Project] = []
        self._groups: list[Group] = []
        self._search_worker: Optional[SearchWorker] = None
        self._sync_worker: Optional[SyncWorker] = None

        # Initialize services
        _proxy = config.proxy if config.proxy_enabled else ""
        self._gitlab_service = GitLabService(config.gitlab_url, config.token, _proxy)
        self._git_service = GitService(config.cache_dir, config.token, config.gitlab_url, _proxy)
        self._search_service = SearchService(
            rg_path=config.rg_path,
            thread_count=config.thread_count,
            timeout=config.search_timeout,
        )
        self._db_service = DBService(config.db_path)

        self._setup_ui()
        self._setup_menu()
        self._setup_shortcuts()
        self._load_cached_data()
        self._apply_theme()

    def _setup_ui(self) -> None:
        self.setWindowTitle("GitLab Code Search")
        self.setMinimumSize(1200, 700)
        self.resize(1400, 800)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Three-panel splitter
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Search Panel
        self._search_panel = SearchPanel()
        self._search_panel.search_requested.connect(self._on_search)
        self._search_panel.sync_requested.connect(self._on_sync)
        self._search_panel.cancel_btn.clicked.connect(self._on_cancel_search)
        self._splitter.addWidget(self._search_panel)

        # Center: Results Table
        self._result_table = ResultTable()
        self._result_table.row_selected.connect(self._on_result_selected)
        self._result_table.row_double_clicked.connect(self._on_result_double_clicked)
        self._splitter.addWidget(self._result_table)

        # Right: Preview Panel
        self._preview_panel = PreviewPanel()
        self._splitter.addWidget(self._preview_panel)

        # Set splitter proportions
        self._splitter.setSizes([280, 500, 400])
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 2)
        self._splitter.setStretchFactor(2, 1)

        main_layout.addWidget(self._splitter)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._status_label = QLabel("Ready")
        self._status_bar.addWidget(self._status_label, 1)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumWidth(200)
        self._progress_bar.setVisible(False)
        self._status_bar.addPermanentWidget(self._progress_bar)

        self._result_count_label = QLabel("")
        self._status_bar.addPermanentWidget(self._result_count_label)

    def _setup_menu(self) -> None:
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        settings_action = QAction("Settings...", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._on_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        connect_action = QAction("Connect to GitLab", self)
        connect_action.triggered.connect(self._on_connect)
        file_menu.addAction(connect_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Search menu
        search_menu = menubar.addMenu("Search")

        focus_search_action = QAction("Focus Search", self)
        focus_search_action.setShortcut(QKeySequence("Ctrl+L"))
        focus_search_action.triggered.connect(
            lambda: self._search_panel.keyword_input.setFocus()
        )
        search_menu.addAction(focus_search_action)

        export_action = QAction("Export Results to CSV...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._result_table.export_csv)
        search_menu.addAction(export_action)

        # View menu
        view_menu = menubar.addMenu("View")

        dark_action = QAction("Dark Theme", self)
        dark_action.triggered.connect(lambda: self._set_theme("dark"))
        view_menu.addAction(dark_action)

        light_action = QAction("Light Theme", self)
        light_action.triggered.connect(lambda: self._set_theme("light"))
        view_menu.addAction(light_action)

    def _setup_shortcuts(self) -> None:
        """Global keyboard shortcuts."""
        pass  # Shortcuts are set in menu actions

    def _apply_theme(self) -> None:
        """Apply dark or light theme."""
        if self._config.theme == "dark":
            self._set_theme("dark")
        else:
            self._set_theme("light")

    def _set_theme(self, theme: str) -> None:
        """Apply theme stylesheet."""
        self._config.theme = theme
        if theme == "dark":
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #1e1e1e; color: #d4d4d4; }
                QLineEdit, QComboBox, QPlainTextEdit, QTextEdit {
                    background-color: #2d2d2d; color: #d4d4d4;
                    border: 1px solid #3c3c3c; border-radius: 3px; padding: 4px;
                }
                QLineEdit:focus, QComboBox:focus {
                    border-color: #0d6efd;
                }
                QTableView {
                    background-color: #1e1e1e; color: #d4d4d4;
                    gridline-color: #2d2d2d; selection-background-color: #264f78;
                }
                QTableView::item:hover { background-color: #2a2d2e; }
                QHeaderView::section {
                    background-color: #2d2d2d; color: #d4d4d4;
                    border: 1px solid #3c3c3c; padding: 4px;
                }
                QGroupBox { border: 1px solid #3c3c3c; border-radius: 4px; margin-top: 8px; padding-top: 8px; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
                QMenuBar { background-color: #2d2d2d; color: #d4d4d4; }
                QMenuBar::item:selected { background-color: #094771; }
                QMenu { background-color: #2d2d2d; color: #d4d4d4; border: 1px solid #3c3c3c; }
                QMenu::item:selected { background-color: #094771; }
                QStatusBar { background-color: #007acc; color: white; }
                QSplitter::handle { background-color: #3c3c3c; }
                QProgressBar { border: 1px solid #3c3c3c; border-radius: 2px; text-align: center; }
                QProgressBar::chunk { background-color: #0d6efd; }
                QScrollBar:vertical { background: #1e1e1e; width: 12px; }
                QScrollBar::handle:vertical { background: #424242; border-radius: 6px; min-height: 20px; }
                QScrollBar:horizontal { background: #1e1e1e; height: 12px; }
                QScrollBar::handle:horizontal { background: #424242; border-radius: 6px; min-width: 20px; }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #ffffff; color: #1e1e1e; }
                QLineEdit, QComboBox, QPlainTextEdit, QTextEdit {
                    background-color: #ffffff; color: #1e1e1e;
                    border: 1px solid #d0d0d0; border-radius: 3px; padding: 4px;
                }
                QTableView {
                    background-color: #ffffff; color: #1e1e1e;
                    gridline-color: #e0e0e0; selection-background-color: #cce5ff;
                }
                QHeaderView::section {
                    background-color: #f5f5f5; color: #1e1e1e;
                    border: 1px solid #d0d0d0; padding: 4px;
                }
                QGroupBox { border: 1px solid #d0d0d0; border-radius: 4px; margin-top: 8px; padding-top: 8px; }
                QStatusBar { background-color: #007acc; color: white; }
                QSplitter::handle { background-color: #e0e0e0; }
            """)

    def _load_cached_data(self) -> None:
        """Load cached groups/projects from SQLite."""
        if self._db_service.has_cached_data():
            self._groups = self._db_service.get_groups()
            self._projects = self._db_service.get_projects()
            self._update_filter_combos()
            self._status_label.setText(f"Loaded {len(self._projects)} cached projects")

            # Load search history for autocomplete
            history = self._db_service.get_history(50)
            keywords = list(set(h["keyword"] for h in history))
            self._search_panel.set_history_completer(keywords)

    def _update_filter_combos(self) -> None:
        """Update group/project/branch combos from loaded data."""
        # Groups
        group_items = [(g.name, g.id) for g in self._groups]
        self._search_panel.set_groups(group_items)

        # Projects
        project_items = [(p.name, p.path_with_namespace) for p in self._projects]
        self._search_panel.set_projects(project_items)

        # Branches - collect unique branches from all projects
        all_branches = set()
        for p in self._projects:
            if p.branches:
                all_branches.update(p.branches)
            all_branches.add(p.default_branch)
        self._search_panel.set_branches(sorted(all_branches) or ["master"])

    # --- Actions ---

    def _on_search(self) -> None:
        """Execute search."""
        keyword = self._search_panel.get_keyword()
        if not keyword:
            return

        # Build query
        query = SearchQuery(
            keyword=keyword,
            group=self._search_panel.get_group(),
            project=self._search_panel.get_project(),
            branch=self._search_panel.get_branch(),
            search_all_branches=self._search_panel.is_all_branches(),
            file_pattern=self._search_panel.get_file_pattern(),
            use_regex=self._search_panel.is_regex(),
            whole_word=self._search_panel.is_whole_word(),
            ignore_case=self._search_panel.is_ignore_case(),
        )

        # Filter projects
        projects = self._get_filtered_projects(query)
        if not projects:
            self._status_label.setText("No projects to search. Sync first.")
            return

        # Save to history
        self._db_service.add_history(keyword, query.file_pattern, query.use_regex, query.ignore_case)

        # Clear previous results
        self._result_table.clear()
        self._preview_panel.clear()
        self._search_panel.set_searching(True)
        self._status_label.setText("Searching...")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, len(projects))
        self._progress_bar.setValue(0)

        # Start search worker
        self._search_service.reset()
        self._search_worker = SearchWorker(
            self._search_service, query, projects, self._config.cache_dir
        )
        self._search_worker.project_started.connect(self._on_search_project_start)
        self._search_worker.results_ready.connect(self._on_search_results_batch)
        self._search_worker.project_done.connect(self._on_search_project_done)
        self._search_worker.search_finished.connect(self._on_search_finished)
        self._search_worker.error_occurred.connect(self._on_search_error)
        self._search_worker.start()

    def _get_filtered_projects(self, query: SearchQuery) -> list[Project]:
        """Filter projects based on query parameters."""
        projects = self._projects

        if query.project:
            projects = [p for p in projects if
                        p.path_with_namespace == query.project or p.name == query.project]
        elif query.group:
            group_name = None
            for g in self._groups:
                if g.id == query.group:
                    group_name = g.full_path
                    break
            if group_name:
                projects = [p for p in projects if p.group.startswith(group_name)]

        # Only include cloned projects
        projects = [p for p in projects if self._git_service.is_cloned(p)]
        return projects

    def _on_search_project_start(self, name: str) -> None:
        self._status_label.setText(f"Searching {name}...")

    def _on_search_results_batch(self, items: list) -> None:
        """Stream results to table as they arrive."""
        self._result_table.add_items(items)
        self._result_count_label.setText(f"{self._result_table.row_count()} results")

    def _on_search_project_done(self, name: str, count: int) -> None:
        self._progress_bar.setValue(self._progress_bar.value() + 1)

    def _on_search_finished(self, result: SearchResult) -> None:
        self._search_panel.set_searching(False)
        self._progress_bar.setVisible(False)
        time_sec = result.search_time_ms / 1000
        self._status_label.setText(
            f"Done. {result.total_count} results in {time_sec:.2f}s "
            f"({result.projects_searched} projects)"
        )
        self._result_count_label.setText(f"{result.total_count} results")
        self._search_worker = None

    def _on_search_error(self, error: str) -> None:
        self._search_panel.set_searching(False)
        self._progress_bar.setVisible(False)
        self._status_label.setText(f"Error: {error}")
        self._search_worker = None

    def _on_cancel_search(self) -> None:
        if self._search_worker:
            self._search_worker.cancel()
            self._status_label.setText("Cancelling...")

    def _on_result_selected(self, item: SearchResultItem) -> None:
        """Show code preview for selected result."""
        # Find the project
        project = next((p for p in self._projects if p.name == item.project), None)
        if not project:
            return

        # Read file directly from disk (more reliable than git show for shallow clones)
        local_path = self._git_service.get_local_path(project)
        file_full = local_path / item.file_path_full
        
        content = None
        if file_full.exists():
            try:
                content = file_full.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass

        # Fallback to git show
        if not content:
            content = self._git_service.get_file_content(project, item.branch, item.file_path_full)

        if content:
            self._preview_panel.show_code(
                content, item.line_number, item.line_content,
                file_path=item.file_path_full
            )

    def _on_result_double_clicked(self, item: SearchResultItem) -> None:
        """Open in browser or editor on double-click."""
        project = next((p for p in self._projects if p.name == item.project), None)
        if not project:
            return

        url = self._gitlab_service.get_file_url(
            project.path_with_namespace, item.branch, item.file_path_full, item.line_number
        )
        webbrowser.open(url)

    # --- Sync ---

    def _on_sync(self) -> None:
        """Sync (clone/fetch) projects based on current filter selection."""
        if not self._projects:
            self._status_label.setText("No projects loaded. Connect to GitLab first.")
            return

        # Filter by current Group/Project selection
        projects_to_sync = self._get_sync_projects()
        if not projects_to_sync:
            self._status_label.setText("No projects match the current filter.")
            return

        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, len(projects_to_sync))
        self._progress_bar.setValue(0)
        self._status_label.setText(f"Syncing {len(projects_to_sync)} projects...")

        self._sync_worker = SyncWorker(self._git_service, projects_to_sync, self._config.thread_count)
        self._sync_worker.progress.connect(self._on_sync_progress)
        self._sync_worker.finished.connect(self._on_sync_finished)
        self._sync_worker.start()

    def _get_sync_projects(self) -> list[Project]:
        """Get projects to sync based on current Group/Project filter."""
        projects = self._projects

        # Filter by selected project
        selected_project = self._search_panel.get_project()
        if selected_project:
            projects = [p for p in projects if
                        p.path_with_namespace == selected_project or p.name == selected_project]
            return projects

        # Filter by selected group
        selected_group = self._search_panel.get_group()
        if selected_group:
            group_name = None
            for g in self._groups:
                if g.id == selected_group:
                    group_name = g.full_path
                    break
            if group_name:
                projects = [p for p in projects if p.group.startswith(group_name)]

        return projects

    def _on_sync_progress(self, msg: str, current: int, total: int) -> None:
        self._status_label.setText(msg)
        self._progress_bar.setValue(current)

    def _on_sync_finished(self, success: bool, message: str) -> None:
        self._progress_bar.setVisible(False)
        self._status_label.setText(message)
        self._sync_worker = None

    # --- Connect ---

    def _on_connect(self) -> None:
        """Connect to GitLab and fetch groups/projects."""
        if not self._config.gitlab_url or not self._config.token:
            QMessageBox.warning(self, "Configuration Required",
                                "Please set GitLab URL and Token in Settings first.")
            self._on_settings()
            return

        _proxy = self._config.proxy if self._config.proxy_enabled else ""
        self._gitlab_service = GitLabService(self._config.gitlab_url, self._config.token, _proxy)
        self._git_service = GitService(self._config.cache_dir, self._config.token, self._config.gitlab_url, _proxy)

        worker = ConnectWorker(self._gitlab_service)
        worker.progress.connect(lambda msg: self._status_label.setText(msg))
        worker.finished.connect(self._on_connect_finished)
        # Keep reference to prevent GC
        self._connect_worker = worker
        worker.start()

    def _on_connect_finished(self, success: bool, message: str, groups: list, projects: list) -> None:
        self._status_label.setText(message)
        if success:
            self._groups = groups
            self._projects = projects
            # Cache to SQLite
            self._db_service.save_groups(groups)
            self._db_service.save_projects(projects)
            self._update_filter_combos()
        else:
            QMessageBox.critical(self, "Connection Failed", message)

    # --- Settings ---

    def _on_settings(self) -> None:
        dialog = SettingsDialog(self._config, self)
        if dialog.exec():
            # Reload config
            self._config.save()
            self._search_service = SearchService(
                rg_path=self._config.rg_path,
                thread_count=self._config.thread_count,
                timeout=self._config.search_timeout,
            )
            self._apply_theme()

    def closeEvent(self, event) -> None:
        """Clean up on close."""
        if self._search_worker:
            self._search_worker.cancel()
            self._search_worker.wait(2000)
        if self._sync_worker:
            self._sync_worker.cancel()
            self._sync_worker.wait(2000)
        self._db_service.close()
        self._config.save()
        super().closeEvent(event)
