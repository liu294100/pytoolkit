"""High-performance search service using ripgrep with parallel execution."""
from __future__ import annotations

import logging
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Callable

from ..model.project import Project
from ..model.result import SearchQuery, SearchResult, SearchResultItem

logger = logging.getLogger(__name__)


class SearchService:
    """Ripgrep-based search engine with parallel project scanning.
    
    Performance optimizations:
    - Uses ripgrep (rg) for blazing fast file search
    - Parallel execution across projects via ThreadPoolExecutor
    - Streaming results back to UI as they arrive
    - Fixed-string mode when regex isn't needed (faster)
    - Memory-mapped I/O via ripgrep internals
    """

    def __init__(self, rg_path: str = "rg", thread_count: int = 8, timeout: int = 30):
        # Resolve rg path relative to project root for portable config
        rg = Path(rg_path)
        if not rg.is_absolute():
            # Resolve relative to the directory containing config (project root)
            candidate = Path(__file__).parent.parent.parent / rg_path
            if candidate.exists():
                rg = candidate.resolve()
        self._rg_path = str(rg)
        self._thread_count = thread_count
        self._timeout = timeout
        self._cancelled = False

    def cancel(self) -> None:
        """Cancel ongoing search."""
        self._cancelled = True

    def reset(self) -> None:
        """Reset cancel flag for new search."""
        self._cancelled = False

    def search(
        self,
        query: SearchQuery,
        projects: list[Project],
        cache_dir: Path,
        on_project_start: Optional[Callable[[str], None]] = None,
        on_results_ready: Optional[Callable[[list[SearchResultItem]], None]] = None,
        on_project_done: Optional[Callable[[str, int], None]] = None,
    ) -> SearchResult:
        """Execute parallel search across all projects.
        
        Args:
            query: Search parameters
            projects: Projects to search
            cache_dir: Base cache directory
            on_project_start: Callback when a project search begins
            on_results_ready: Callback with batch results (for streaming UI updates)
            on_project_done: Callback(project_name, match_count) when project finishes
            
        Returns:
            Aggregated SearchResult
        """
        self._cancelled = False
        start_time = time.perf_counter()
        final_result = SearchResult()

        # Determine branches to search per project
        search_tasks = []
        for project in projects:
            local_path = self._get_project_path(project, cache_dir)
            if not local_path or not local_path.exists():
                continue

            if query.search_all_branches:
                branches = self._get_branches(local_path)
            else:
                branches = [query.branch]

            for branch in branches:
                search_tasks.append((project, branch, local_path))

        # Parallel search with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self._thread_count) as executor:
            futures = {}
            for project, branch, local_path in search_tasks:
                if self._cancelled:
                    break
                future = executor.submit(
                    self._search_project, query, project, branch, local_path
                )
                futures[future] = (project.name, branch)

            for future in as_completed(futures):
                if self._cancelled:
                    # Cancel remaining futures
                    for f in futures:
                        f.cancel()
                    break

                project_name, branch = futures[future]
                try:
                    items = future.result()
                    if items:
                        final_result.items.extend(items)
                        final_result.total_count += len(items)
                        if on_results_ready:
                            on_results_ready(items)
                    if on_project_done:
                        on_project_done(project_name, len(items) if items else 0)
                except Exception as e:
                    final_result.errors.append(f"{project_name}: {str(e)}")
                    logger.error("Search error in %s: %s", project_name, e)

        final_result.search_time_ms = (time.perf_counter() - start_time) * 1000
        final_result.projects_searched = len(set(p.name for p, _, _ in search_tasks))
        return final_result

    def _search_project(
        self, query: SearchQuery, project: Project, branch: str, local_path: Path
    ) -> list[SearchResultItem]:
        """Search a single project/branch using ripgrep. Returns results list."""
        if self._cancelled:
            return []

        # Checkout branch using git
        try:
            self._checkout_branch(local_path, branch)
        except Exception as e:
            logger.warning("Cannot checkout %s/%s: %s", project.name, branch, e)
            # Still try to search current state
            pass

        # Build ripgrep command
        rg_args = query.to_rg_args()
        # Use "." as search path so output contains relative paths (avoids Windows drive letter colon issue)
        cmd = [self._rg_path] + rg_args + ["--", "."]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self._timeout,
                cwd=str(local_path),
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except subprocess.TimeoutExpired:
            logger.warning("Search timeout for %s/%s", project.name, branch)
            return []
        except FileNotFoundError:
            logger.error("ripgrep not found at: %s", self._rg_path)
            return []

        if proc.returncode not in (0, 1):  # 1 = no matches (normal)
            if proc.stderr:
                logger.warning("rg error in %s: %s", project.name, proc.stderr[:200])
            return []

        logger.debug("rg cmd: %s | returncode=%d | stdout_len=%d | stderr=%s",
                     " ".join(cmd), proc.returncode, len(proc.stdout), proc.stderr[:200] if proc.stderr else "")

        # Parse ripgrep output
        return self._parse_rg_output(proc.stdout, project, branch, local_path)

    def _parse_rg_output(
        self, output: str, project: Project, branch: str, local_path: Path
    ) -> list[SearchResultItem]:
        """Parse ripgrep output into SearchResultItems.
        
        Format: file:line:column:content
        Optimized for speed with minimal allocations.
        """
        if not output:
            return []

        items = []
        base_path = str(local_path)

        for line in output.split("\n"):
            if not line or self._cancelled:
                continue

            # Parse: filepath:linenum:colnum:content
            parts = line.split(":", 3)
            if len(parts) < 4:
                continue

            file_path_raw, line_num_str, col_str, content = parts

            try:
                line_num = int(line_num_str)
                col = int(col_str)
            except ValueError:
                continue

            # Make file path relative: strip leading .\ or ./
            rel_path = file_path_raw.lstrip(".").lstrip(os.sep).lstrip("/")

            # Skip .git directory files
            if rel_path.startswith(".git"):
                continue

            file_name = os.path.basename(rel_path)

            items.append(SearchResultItem(
                project=project.name,
                branch=branch,
                file=file_name,
                line_number=line_num,
                line_content=content,
                match_start=col - 1,
                match_end=col - 1 + len(content),  # Approximate
                file_path_full=rel_path,
            ))

        return items

    def _get_project_path(self, project: Project, cache_dir: Path) -> Optional[Path]:
        """Get local filesystem path for a project."""
        safe_path = project.path_with_namespace.replace("/", os.sep)
        path = cache_dir / safe_path
        return path if path.exists() else None

    def _checkout_branch(self, repo_path: Path, branch: str) -> None:
        """Fast branch checkout using git command directly."""
        try:
            subprocess.run(
                ["git", "checkout", branch],
                cwd=str(repo_path),
                capture_output=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except Exception:
            # Try remote branch
            try:
                subprocess.run(
                    ["git", "checkout", "-b", branch, f"origin/{branch}"],
                    cwd=str(repo_path),
                    capture_output=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            except Exception:
                pass

    def _get_branches(self, repo_path: Path) -> list[str]:
        """Get remote branch list quickly."""
        try:
            result = subprocess.run(
                ["git", "branch", "-r", "--format=%(refname:short)"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            branches = []
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line and not line.endswith("/HEAD"):
                    # Remove 'origin/' prefix
                    branch = line.replace("origin/", "", 1)
                    branches.append(branch)
            return branches or ["master"]
        except Exception:
            return ["master"]

    @staticmethod
    def check_rg_available(rg_path: str = "rg") -> bool:
        """Check if ripgrep is installed and accessible."""
        try:
            result = subprocess.run(
                [rg_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
