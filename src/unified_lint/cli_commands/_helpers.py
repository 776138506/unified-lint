"""Shared helpers for CLI subcommands."""

from __future__ import annotations

import re
from pathlib import Path

from rich.console import Console

console = Console()

VALID_SEVERITIES = ("error", "warn", "info")
RULE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_rule_id(rule_id: str) -> None:
    """Raise SystemExit with friendly message if rule_id is invalid."""
    if not RULE_ID_PATTERN.match(rule_id):
        console.print(f"[red]Invalid rule_id: '{rule_id}'[/red]")
        console.print(
            "Must be snake_case: lowercase letters, digits, underscore; "
            "starting with a letter."
        )
        raise SystemExit(1)


def validate_severity(severity: str) -> None:
    """Raise SystemExit with friendly message if severity is invalid."""
    if severity not in VALID_SEVERITIES:
        console.print(f"[red]Invalid severity: '{severity}'[/red]")
        console.print(f"Must be one of: {', '.join(VALID_SEVERITIES)}")
        raise SystemExit(1)


def patterns_dir(project_root: Path) -> Path:
    """Return the .grit/patterns/ directory for a project."""
    return project_root / ".grit" / "patterns"


def rule_file_path(project_root: Path, rule_id: str) -> Path:
    """Return the path to .grit/patterns/<rule_id>.md."""
    return patterns_dir(project_root) / f"{rule_id}.md"


def ensure_patterns_dir(project_root: Path) -> Path:
    """Create .grit/patterns/ if missing; return the directory."""
    pdir = patterns_dir(project_root)
    pdir.mkdir(parents=True, exist_ok=True)
    return pdir
