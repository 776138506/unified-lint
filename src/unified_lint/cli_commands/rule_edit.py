"""rule edit subcommand: open rule file in $EDITOR."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console

from ._discovery import builtin_source_hint, discover_all_rules
from ._helpers import console, rule_file_path

console = Console()


def rule_edit(
    rule_id: str = typer.Argument(..., help="Rule ID to edit."),
    project: Path = typer.Option(
        ".", "--project", "-p", help="Project root directory."
    ),
):
    """Open an existing rule's source file in $EDITOR.

    For project-level GritQL rules (override files at
    `.grit/patterns/<id>.md`), opens the override file.

    For builtin rules, prints the engine source file path (read-only hint).

    Editor resolution: $EDITOR → $VISUAL → notepad (Windows) / vi (Unix).
    """
    project = project.resolve()
    override = rule_file_path(project, rule_id)

    if override.exists():
        editor = (
            os.environ.get("EDITOR")
            or os.environ.get("VISUAL")
            or ("notepad" if os.name == "nt" else "vi")
        )
        editor_parts = editor.split()
        editor_bin = editor_parts[0]
        if not shutil.which(editor_bin):
            console.print(
                f"[yellow]Editor not found:[/yellow] {editor_bin} "
                f"(set $EDITOR or edit manually: {override})"
            )
            raise typer.Exit(code=1)
        console.print(f"[cyan]Opening {override} in {editor}[/cyan]")
        subprocess.run([*editor_parts, str(override)])
        return

    rules = discover_all_rules(project)
    engines = sorted({r["engine"] for r in rules if r["id"] == rule_id})

    if not engines:
        console.print(f"[red]Rule '{rule_id}' not found.[/red]")
        raise typer.Exit(code=1)

    console.print(
        f"[yellow]No project-level override for '{rule_id}' "
        f"(builtin rule in: {', '.join(engines)})[/yellow]"
    )
    console.print("\nBuiltin source locations:")
    for eng in engines:
        console.print(f"  - {eng}: [dim]{builtin_source_hint(rule_id, eng)}[/dim]")
    console.print(
        f"\nTo make this rule editable, create an override first:\n"
        f"  [cyan]unified-lint rule add {rule_id}[/cyan]\n"
        f"Then re-run [cyan]unified-lint rule edit {rule_id}[/cyan]."
    )
