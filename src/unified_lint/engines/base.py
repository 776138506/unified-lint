"""Engine abstraction layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


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
