"""fix subcommand: attempt auto-fix (currently stub)."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from ..runner import format_results, load_config, run_fix

console = Console()


def fix(
    project: Path = typer.Argument(".", help="Project root directory."),
):
    """Attempt to auto-fix fixable violations.

    WARNING: Currently a stub. engine.fix() is a no-op in every engine —
    no files are modified. Use check + manual editing until rules implement
    real file modification.
    """
    project = project.resolve()
    config = load_config(project)

    console.print("[bold]Running auto-fix...[/bold]")
    console.print(
        "[yellow]Note: fix() is currently a stub in all engines "
        "(no file modification).[/yellow]"
    )
    results, exit_code = run_fix(project, config)

    output = format_results(results)
    console.print(output)

    if exit_code == 0:
        console.print("\n[bold green]All fixed![/bold green]")
    else:
        console.print(
            f"\n[bold yellow]Some issues remain (exit {exit_code})[/bold yellow]"
        )

    raise typer.Exit(code=exit_code)
