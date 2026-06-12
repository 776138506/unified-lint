"""rule list subcommand."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ._discovery import discover_all_rules

console = Console()


def rule_list(
    project: Path = typer.Argument(".", help="Project root directory."),
    engine: Optional[str] = typer.Option(
        None,
        "--engine",
        "-e",
        help=(
            "Filter by engine: grit | python-ast | markdown-ast | "
            "tree-sitter | spec-chain | import-linter"
        ),
    ),
):
    """List all available rules in a rich table."""
    project = project.resolve()
    rules = discover_all_rules(project)

    if engine:
        rules = [r for r in rules if r["engine"] == engine]

    table = Table(title=f"Available Rules ({len(rules)})")
    table.add_column("Rule ID", style="cyan")
    table.add_column("Engine", style="magenta")
    table.add_column("Severity", style="yellow")
    table.add_column("Description")

    for rule in rules:
        table.add_row(rule["id"], rule["engine"], rule["severity"], rule["description"])

    console.print(table)
