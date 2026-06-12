"""rule delete subcommand: delete project-level rule override."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from ._helpers import console, rule_file_path

console = Console()


def rule_delete(
    rule_id: str = typer.Argument(..., help="Rule ID to delete (project override)."),
    project: Path = typer.Option(
        ".", "--project", "-p", help="Project root directory."
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
):
    """Delete a project-level GritQL rule override.

    Only deletes the override at `.grit/patterns/<id>.md`. Builtin rules
    cannot be deleted (they live in the package source).
    """
    project = project.resolve()
    target = rule_file_path(project, rule_id)

    if not target.exists():
        console.print(f"[yellow]No project-level rule '{rule_id}' to delete.[/yellow]")
        console.print(
            "Builtin rules cannot be deleted (they live in package source).\n"
            "Use 'unified-lint rule list' to see all available rules."
        )
        raise typer.Exit(code=1)

    if not yes:
        console.print(f"About to delete: [cyan]{target}[/cyan]")
        if not typer.confirm("Are you sure?", default=False):
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(code=0)

    target.unlink()
    console.print(f"[green]Deleted:[/green] {target}")
    console.print(
        f"\nThe builtin rule (if any) is now active again. "
        f"Run [cyan]unified-lint rule show {rule_id}[/cyan] to verify."
    )
