"""init subcommand: initialize unified-lint in a project."""

from __future__ import annotations

from pathlib import Path

import typer


def init(
    project: Path = typer.Argument(".", help="Project root directory."),
    root_package: str = typer.Option(
        "myapp",
        "--root-package",
        "-r",
        help="Root Python package name (used by import-linter contract).",
    ),
):
    """Initialize unified-lint in a project.

    Detects primary language, generates `.unified-lint/config.toml`,
    `.importlinter`, copies builtin rules, updates `.gitignore`.

    Will NOT overwrite existing `.importlinter` (manual merge required).
    """
    from ..installer import run_init

    project = project.resolve()
    run_init(project, root_package)
