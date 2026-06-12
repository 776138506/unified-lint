"""rule show subcommand."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ..rules.registry import BUILTIN_RULES
from ._discovery import discover_all_rules

console = Console()


def rule_show(
    rule_id: str = typer.Argument(..., help="Rule ID (e.g. no_hardcoded_password)."),
    project: Path = typer.Option(
        ".", "--project", "-p", help="Project root directory."
    ),
):
    """Show full definition of one rule.

    Displays: ID, engine, severity, source, description, and the full rule
    content (GritQL pattern, or engine source location for non-GritQL rules).
    """
    project = project.resolve()
    rules = discover_all_rules(project)

    matches = [r for r in rules if r["id"] == rule_id]
    if not matches:
        console.print(f"[red]Rule '{rule_id}' not found.[/red]")
        console.print("Use 'unified-lint rule list' to see available rules.")
        raise typer.Exit(code=1)

    for r in matches:
        meta = (
            f"[cyan]ID:[/cyan] {r['id']}\n"
            f"[magenta]Engine:[/magenta] {r['engine']}\n"
            f"[yellow]Severity:[/yellow] {r['severity']}\n"
            f"[white]Source:[/white] {r.get('source', 'engine')}\n"
            f"\n[white]Description:[/white] {r['description']}"
        )
        console.print(
            Panel(meta, title=f"Rule: {r['id']} ({r['engine']})", border_style="cyan")
        )

        if r["engine"] == "grit":
            content = next(
                (b["content"] for b in BUILTIN_RULES if b["id"] == r["id"]), None
            )
            if content:
                console.print("\n[bold]Definition:[/bold]")
                console.print(Markdown(content))
        elif r["engine"] in ("python-ast", "markdown-ast"):
            console.print(
                f"\n[dim]Definition: see "
                f"src/unified_lint/engines/"
                f"{r['engine'].replace('-', '_')}.py "
                f"(rule '{r['id']}')[/dim]"
            )
        elif r["engine"] == "spec-chain":
            from ..engines.spec_chain import _CHAIN_RULES

            if r["id"] in _CHAIN_RULES:
                console.print(
                    "\n[dim]Definition: spec-chain plugin rule "
                    "(see _CHAIN_RULES in spec_chain.py)[/dim]"
                )
            else:
                console.print(
                    "\n[dim]Definition: built-in spec-chain rule "
                    "(prd_coverage / metrics_api_compliance / api_code_compliance)[/dim]"
                )
        else:
            console.print(
                "\n[dim]Definition: no embedded content; "
                "see engine implementation.[/dim]"
            )

        if r.get("source") == "project":
            console.print(
                f"\n[green]Override file:[/green] {project}/.grit/patterns/{r['id']}.md"
            )
