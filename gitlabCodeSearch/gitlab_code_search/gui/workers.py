"""Background worker threads for non-blocking operations."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal, QObject
from typing import Optional

from ..model.project import Project
from ..model.result import SearchQuery, SearchResult, SearchResultItem
from ..service.gitlab_service import GitLabService
from ..service.git_service import GitService
from ..service.search_service import SearchService
from ..model.config import AppConfig

from pathlib import Path


class SearchWorker(QThread):
    """Background search thread that streams results to UI."""

    # Signals for UI updates
    project_started = Signal(str)          # project name
    results_ready = Signal(list)           # batch of SearchResultItem
    project_done = Signal(str, int)        # project name, match count
    search_finished = Signal(object)       # SearchResult
    error_occurred = Signal(str)           # error message

    def __init__(self, search_service: SearchService, query: SearchQuery,
                 projects: list[Project], cache_dir: Path, parent=None):
        super().__init__(parent)
        self._search_service = search_service
        self._query = query
        self._projects = projects
        self._cache_dir = cache_dir

    def run(self) -> None:
        try:
            result = self._search_service.search(
                query=self._query,
                projects=self._projects,
                cache_dir=self._cache_dir,
                on_project_start=lambda name: self.project_started.emit(name),
                on_results_ready=lambda items: self.results_ready.emit(items),
                on_project_done=lambda name, count: self.project_done.emit(name, count),
            )
            self.search_finished.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def cancel(self) -> None:
        self._search_service.cancel()


class SyncWorker(QThread):
    """Background worker for git clone/fetch operations (parallel)."""

    progress = Signal(str, int, int)  # message, current, total
    finished = Signal(bool, str)      # success, message

    def __init__(self, git_service: GitService, projects: list[Project],
                 max_workers: int = 8, parent=None):
        super().__init__(parent)
        self._git_service = git_service
        self._projects = projects
        self._max_workers = max_workers
        self._cancelled = False

    def run(self) -> None:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        total = len(self._projects)
        success_count = 0
        done_count = 0

        def sync_one(project: Project) -> bool:
            if self._cancelled:
                return False
            if self._git_service.is_cloned(project):
                return self._git_service.fetch(project)
            else:
                return self._git_service.clone(project)

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {executor.submit(sync_one, p): p for p in self._projects}
            for future in as_completed(futures):
                if self._cancelled:
                    break
                project = futures[future]
                done_count += 1
                try:
                    if future.result():
                        success_count += 1
                except Exception:
                    pass
                self.progress.emit(
                    f"Syncing... ({done_count}/{total})",
                    done_count, total
                )

        if self._cancelled:
            self.finished.emit(False, "Sync cancelled")
        else:
            self.finished.emit(True, f"Synced {success_count}/{total} projects")

    def cancel(self) -> None:
        self._cancelled = True


class ConnectWorker(QThread):
    """Background worker for GitLab connection and data fetching."""

    progress = Signal(str)
    finished = Signal(bool, str, list, list)  # success, message, groups, projects

    def __init__(self, gitlab_service: GitLabService, parent=None):
        super().__init__(parent)
        self._gitlab_service = gitlab_service

    def run(self) -> None:
        self.progress.emit("Connecting to GitLab...")
        if not self._gitlab_service.connect():
            self.finished.emit(False, "Connection failed", [], [])
            return

        self.progress.emit("Fetching groups...")
        groups = self._gitlab_service.get_groups()

        self.progress.emit("Fetching projects...")
        projects = self._gitlab_service.get_projects()

        self.finished.emit(
            True,
            f"Connected. Found {len(groups)} groups, {len(projects)} projects.",
            groups, projects,
        )
