"""Git operations service for clone, fetch, and branch management."""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Optional, Callable

import git
from git import Repo, GitCommandError

from ..model.project import Project

logger = logging.getLogger(__name__)


class GitService:
    """Manages local git repositories - clone, fetch, checkout."""

    def __init__(self, cache_dir: str | Path, token: str = "", gitlab_url: str = "", proxy: str = ""):
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._token = token
        self._gitlab_url = gitlab_url.rstrip("/")
        self._proxy = proxy

    def _get_git_env(self) -> dict[str, str]:
        """Build environment variables for git commands (proxy, ssl)."""
        env = os.environ.copy()
        if self._proxy:
            env["http_proxy"] = self._proxy
            env["https_proxy"] = self._proxy
            env["GIT_SSL_NO_VERIFY"] = "1"
        return env

    def _get_auth_url(self, clone_url: str) -> str:
        """Inject token into clone URL for authentication."""
        if self._token and "://" in clone_url:
            # https://oauth2:TOKEN@gitlab.com/...
            proto, rest = clone_url.split("://", 1)
            return f"{proto}://oauth2:{self._token}@{rest}"
        return clone_url

    def get_local_path(self, project: Project) -> Path:
        """Get local path for a project repo."""
        # Use path_with_namespace to avoid collisions
        safe_path = project.path_with_namespace.replace("/", os.sep)
        return self._cache_dir / safe_path

    def is_cloned(self, project: Project) -> bool:
        """Check if project is already cloned locally."""
        local_path = self.get_local_path(project)
        return (local_path / ".git").exists()

    def clone(self, project: Project, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Clone a project repository. Returns True on success."""
        local_path = self.get_local_path(project)

        if self.is_cloned(project):
            logger.info("Already cloned: %s", project.name)
            return True

        local_path.mkdir(parents=True, exist_ok=True)
        auth_url = self._get_auth_url(project.clone_url)

        try:
            if progress_callback:
                progress_callback(f"Cloning {project.name}...")

            Repo.clone_from(
                auth_url,
                str(local_path),
                multi_options=["--depth=1", "--no-single-branch"],
                env=self._get_git_env(),
            )
            logger.info("Cloned: %s", project.name)
            return True
        except GitCommandError as e:
            logger.error("Clone failed for %s: %s", project.name, e)
            # Clean up failed clone
            if local_path.exists():
                shutil.rmtree(local_path, ignore_errors=True)
            return False

    def fetch(self, project: Project, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Fetch latest changes for a cloned project."""
        local_path = self.get_local_path(project)

        if not self.is_cloned(project):
            return self.clone(project, progress_callback)

        try:
            if progress_callback:
                progress_callback(f"Fetching {project.name}...")

            repo = Repo(str(local_path))
            # Fetch all branches with proxy env
            with repo.git.custom_environment(**{k: v for k, v in self._get_git_env().items() if k.startswith(("http", "https", "GIT_"))}):
                repo.git.fetch("--all", "--prune")
            logger.info("Fetched: %s", project.name)
            return True
        except GitCommandError as e:
            logger.error("Fetch failed for %s: %s", project.name, e)
            return False

    def checkout_branch(self, project: Project, branch: str) -> bool:
        """Checkout a specific branch."""
        local_path = self.get_local_path(project)

        if not self.is_cloned(project):
            return False

        try:
            repo = Repo(str(local_path))
            # Try local branch first, then remote tracking
            if branch in [b.name for b in repo.branches]:
                repo.git.checkout(branch)
            else:
                repo.git.checkout("-b", branch, f"origin/{branch}")
            return True
        except GitCommandError as e:
            logger.error("Checkout failed for %s/%s: %s", project.name, branch, e)
            return False

    def get_local_branches(self, project: Project) -> list[str]:
        """Get all available branches (remote tracking)."""
        local_path = self.get_local_path(project)

        if not self.is_cloned(project):
            return []

        try:
            repo = Repo(str(local_path))
            branches = []
            for ref in repo.references:
                if hasattr(ref, "remote_head"):
                    branches.append(ref.remote_head)
            # Deduplicate and sort
            return sorted(set(branches))
        except Exception:
            return []

    def get_file_content(self, project: Project, branch: str, file_path: str) -> Optional[str]:
        """Read file content from a specific branch without checkout.
        
        Uses git show for speed - no need to checkout.
        """
        local_path = self.get_local_path(project)

        if not self.is_cloned(project):
            return None

        try:
            repo = Repo(str(local_path))
            # Use git show to read file at specific branch without checkout
            content = repo.git.show(f"origin/{branch}:{file_path}")
            return content
        except GitCommandError:
            try:
                # Fallback: try without origin/ prefix
                content = repo.git.show(f"{branch}:{file_path}")
                return content
            except GitCommandError:
                return None
