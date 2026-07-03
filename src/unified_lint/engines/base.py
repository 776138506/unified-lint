"""Engine abstraction layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


# Default directories/files that engines must skip during project scans.
# These are generated artifacts, dependencies, or version-control metadata
# that should never be linted. Engines should call ``should_skip_path()``
# before processing any file discovered by rglob/walk.
DEFAULT_EXCLUDES: tuple[str, ...] = (
    ".venv",
    "venv",
    "env",
    "ENV",
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "dist",
    "build",
    ".eggs",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".cache",
    ".import_linter_cache",
    ".grimp_cache",
    ".grit/.gritmodules",
    ".grit/modules",
    ".unified-lint/cache",
    # setuptools/sdist artifacts
    "*.egg-info",
    "*.egg",
)


def should_skip_path(path: Path, project_root: Optional[Path] = None) -> bool:
    """Return True if ``path`` lies under any of DEFAULT_EXCLUDES.

    Engines should call this for every candidate file so the same
    exclusion set applies across python_ast / markdown_ast / spec_chain.
    """
    parts = path.parts
    for exclude in DEFAULT_EXCLUDES:
        if exclude in parts:
            return True
        if "*" in exclude and any(_glob_match(exclude, p) for p in parts):
            return True
    return False


def _glob_match(pattern: str, name: str) -> bool:
    """Minimal fnmatch-style match supporting a single leading ``*``."""
    if pattern.startswith("*") and not pattern.count("*") - 1:
        return name.endswith(pattern[1:])
    return False


class Severity(Enum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"

    @property
    def exit_priority(self) -> int:
        return {"error": 1, "warn": 2, "info": 3}[self.value]


@dataclass
class Violation:
    rule_id: str
    message: str
    file: str
    line: int = 0
    col: int = 0
    severity: Severity = Severity.ERROR
    engine: str = ""
    fixable: bool = False


@dataclass
class EngineResult:
    engine_name: str
    violations: list[Violation] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return not self.violations and not self.error

    @property
    def has_errors(self) -> bool:
        return any(v.severity == Severity.ERROR for v in self.violations)


class LintEngine(ABC):
    """Abstract base for all lint engines."""

    name: str = "unknown"

    @abstractmethod
    def check(self, project_root: Path, config: dict) -> EngineResult:
        """Run checks and return violations."""
        ...

    def fix(self, project_root: Path, config: dict) -> EngineResult:
        """Auto-fix fixable violations. Default: no-op."""
        return self.check(project_root, config)

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the engine binary/deps are installed."""
        ...
