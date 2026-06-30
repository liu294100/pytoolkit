"""GitLab API service for fetching groups, projects, and branches."""
from __future__ import annotations

import logging
import urllib3
from typing import Optional

import gitlab
from gitlab.v4.objects import Project as GLProject

from ..model.project import Project, Group

# Suppress SSL warnings for self-signed certs behind proxy
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class GitLabService:
    """Handles all GitLab API interactions with caching support."""

    def __init__(self, url: str, token: str, proxy: str = ""):
        self._url = url.rstrip("/")
        self._token = token
        self._proxy = proxy
        self._gl: Optional[gitlab.Gitlab] = None

    def connect(self) -> bool:
        """Establish connection to GitLab. Returns True on success."""
        try:
            session = None
            if self._proxy:
                import requests
                session = requests.Session()
                session.proxies = {
                    "http": self._proxy,
                    "https": self._proxy,
                }
                session.verify = False

            self._gl = gitlab.Gitlab(
                self._url,
                private_token=self._token,
                session=session,
                ssl_verify=False,
            )
            self._gl.auth()
            logger.info("Connected to GitLab: %s", self._url)
            return True
        except Exception as e:
            logger.error("Failed to connect to GitLab: %s", e)
            self._gl = None
            return False

    @property
    def is_connected(self) -> bool:
        return self._gl is not None

    def get_groups(self) -> list[Group]:
        """Fetch all accessible groups."""
        if not self._gl:
            return []
        try:
            gl_groups = self._gl.groups.list(all=True, min_access_level=10)
            return [Group.from_gitlab(g) for g in gl_groups]
        except Exception as e:
            logger.error("Failed to fetch groups: %s", e)
            return []

    def get_projects(self, group_id: Optional[int] = None) -> list[Project]:
        """Fetch projects, optionally filtered by group."""
        if not self._gl:
            return []
        try:
            if group_id:
                group = self._gl.groups.get(group_id)
                gl_projects = group.projects.list(all=True, include_subgroups=True)
                # Group projects are lightweight, need to fetch full object for clone url
                projects = []
                for gp in gl_projects:
                    try:
                        full_project = self._gl.projects.get(gp.id)
                        projects.append(Project.from_gitlab(full_project))
                    except Exception:
                        pass
                return projects
            else:
                gl_projects = self._gl.projects.list(all=True, membership=True, min_access_level=10)
                return [Project.from_gitlab(p) for p in gl_projects]
        except Exception as e:
            logger.error("Failed to fetch projects: %s", e)
            return []

    def get_branches(self, project_id: int) -> list[str]:
        """Fetch branch names for a project."""
        if not self._gl:
            return []
        try:
            project = self._gl.projects.get(project_id)
            branches = project.branches.list(all=True)
            return [b.name for b in branches]
        except Exception as e:
            logger.error("Failed to fetch branches for project %d: %s", project_id, e)
            return []

    def get_file_url(self, project_path: str, branch: str, file_path: str, line: int) -> str:
        """Generate web URL for a specific file and line."""
        return f"{self._url}/{project_path}/-/blob/{branch}/{file_path}#L{line}"
