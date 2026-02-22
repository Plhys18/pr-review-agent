from __future__ import annotations

from enum import Enum
from pydantic import BaseModel


class ChangeType(str, Enum):
    BUGFIX = "bugfix"
    FEATURE = "feature"
    REFACTOR = "refactor"
    DOCS = "docs"
    TEST = "test"
    CONFIG = "config"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    SUGGESTION = "suggestion"
    NITPICK = "nitpick"


class ReviewCategory(str, Enum):
    SECURITY = "security"
    LOGIC = "logic"
    PERFORMANCE = "performance"
    STYLE = "style"
    BEST_PRACTICE = "best_practice"


class FileDiff(BaseModel):
    filename: str
    patch: str
    status: str  # added, modified, removed, renamed
    additions: int
    deletions: int


class PRInfo(BaseModel):
    owner: str
    repo: str
    number: int
    title: str
    body: str | None
    base_branch: str
    head_branch: str
    files: list[FileDiff]


class ReviewFinding(BaseModel):
    file: str
    line: int | None = None
    severity: Severity
    category: ReviewCategory
    message: str
    suggestion: str | None = None


class ReviewResult(BaseModel):
    change_type: ChangeType
    summary: str
    findings: list[ReviewFinding]
    approved: bool
