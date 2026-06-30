"""Search result models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class SearchResultItem:
    """A single search match line.

    Using __slots__ for memory efficiency when handling thousands of results.
    """

    project: str
    branch: str
    file: str
    line_number: int
    line_content: str
    match_start: int = 0
    match_end: int = 0
    file_path_full: str = ""

    @property
    def web_url(self) -> str:
        """Generate GitLab web URL for this result."""
        return ""  # Set by caller with gitlab_url context

    def to_row(self) -> list[str]:
        """Convert to table row data."""
        return [self.project, self.branch, self.file, str(self.line_number), self.line_content.strip()]


@dataclass
class SearchResult:
    """Aggregated search results."""

    items: list[SearchResultItem] = field(default_factory=list)
    total_count: int = 0
    search_time_ms: float = 0.0
    projects_searched: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.items) == 0

    def add_item(self, item: SearchResultItem) -> None:
        self.items.append(item)
        self.total_count += 1

    def merge(self, other: SearchResult) -> None:
        """Merge another result into this one (thread-safe merge at end)."""
        self.items.extend(other.items)
        self.total_count += other.total_count
        self.errors.extend(other.errors)


@dataclass
class SearchQuery:
    """Represents a search query with all parameters."""

    keyword: str
    group: Optional[str] = None  # None means all
    project: Optional[str] = None  # None means all
    branch: str = "master"
    search_all_branches: bool = False
    file_pattern: str = ""  # e.g., "*.java"
    use_regex: bool = False
    whole_word: bool = False
    ignore_case: bool = True

    def to_rg_args(self) -> list[str]:
        """Convert query to ripgrep arguments for maximum speed."""
        args = []

        if self.ignore_case:
            args.append("-i")

        if self.use_regex:
            args.append("-e")
            args.append(self.keyword)
        elif self.whole_word:
            args.append("-w")
            args.append(self.keyword)
        else:
            args.append("-F")  # Fixed string (faster than regex)
            args.append(self.keyword)

        if self.file_pattern:
            # Support multiple patterns separated by comma
            for pattern in self.file_pattern.split(","):
                pattern = pattern.strip()
                if pattern:
                    args.extend(["-g", pattern])

        # Performance flags
        args.extend([
            "--line-number",
            "--column",
            "--no-heading",
            "--color=never",
            "--max-count=500",  # Limit per file
            "-j", "4",  # Threads per rg process
        ])

        return args
