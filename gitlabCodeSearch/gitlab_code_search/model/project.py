"""Project and related data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Project:
    """Represents a GitLab project."""

    id: int
    name: str
    path_with_namespace: str
    group: str = ""
    default_branch: str = "master"
    web_url: str = ""
    clone_url: str = ""
    branches: list[str] = field(default_factory=list)
    last_synced: Optional[str] = None
    local_path: str = ""

    @property
    def display_name(self) -> str:
        return self.path_with_namespace or self.name

    @classmethod
    def from_gitlab(cls, gl_project) -> Project:
        """Create from python-gitlab project object."""
        namespace = gl_project.namespace.get("full_path", "") if hasattr(gl_project, "namespace") else ""
        return cls(
            id=gl_project.id,
            name=gl_project.name,
            path_with_namespace=gl_project.path_with_namespace,
            group=namespace,
            default_branch=getattr(gl_project, "default_branch", "master") or "master",
            web_url=getattr(gl_project, "web_url", ""),
            clone_url=getattr(gl_project, "http_url_to_repo", ""),
        )


@dataclass
class Group:
    """Represents a GitLab group."""

    id: int
    name: str
    full_path: str

    @classmethod
    def from_gitlab(cls, gl_group) -> Group:
        return cls(
            id=gl_group.id,
            name=gl_group.name,
            full_path=gl_group.full_path,
        )
