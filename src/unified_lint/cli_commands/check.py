"""check subcommand: run all lint checks."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..runner import format_results, load_config, run_check

console = Console()


def check(
    project: Path = typer.Argument(
        ".", help="Project root directory. Default: current directory."
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show per-rule match counts and timing details.",
    ),
    engine: Optional[str] = typer.Option(
        None,
        "--engine",
        "-e",
        help=(
            "Run only one engine. Names: "
            "grit | python-ast | markdown-ast | tree-sitter | spec-chain | import-linter"
        ),
    ),
    severity: Optional[str] = typer.Option(
        None,
        "--severity",
        "-s",
        help="Show only violations at this level. Names: error | warn | info",
    ),
):
    """Run all lint checks against the project.

    Loads `.unified-lint/config.toml`, runs every enabled engine, and
    aggregates results into a unified report.

    Exit codes: 0 = ALL PASS, 1 = ERROR, 2 = WARN only, 4 = missing tool.
    """
    project = project.resolve()
    config = load_config(project)
    results, exit_code = run_check(project, config)

    # Post-hoc filters
    if engine:
        results = [r for r in results if r.engine_name == engine]
    if severity:
        for r in results:
            r.violations = [v for v in r.violations if v.severity.value == severity]

    # Re-compute exit_code from filtered results
    if engine or severity:
        new_exit = 0
        for r in results:
            if r.error:
                new_exit = max(new_exit, 4)
            if r.has_errors:
                new_exit = max(new_exit, 1)
            elif r.violations:
                best = min(v.severity.exit_priority for v in r.violations)
                new_exit = max(new_exit, best)
        exit_code = new_exit

    output = format_results(results)
    console.print(output)

    if exit_code == 0:
        console.print("\n[bold green]ALL PASS[/bold green]")
    elif exit_code == 1:
        console.print("\n[bold red]FAILED - errors found[/bold red]")
    elif exit_code == 2:
        console.print("\n[bold yellow]WARNINGS[/bold yellow]")
    elif exit_code >= 4:
        console.print("\n[bold red]TOOLS MISSING - install dependencies[/bold red]")

    raise typer.Exit(code=exit_code)
