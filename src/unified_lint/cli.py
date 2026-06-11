"""CLI entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .runner import load_config, run_check, run_fix, format_results

app = typer.Typer(
    name="unified-lint",
    help="Unified linter: code (GritQL) + docs (GritQL) + architecture (import-linter)",
    no_args_is_help=True,
)
console = Console()


@app.command()
def check(
    project: Path = typer.Argument(".", help="Project root directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Run all lint checks."""
    project = project.resolve()
    config = load_config(project)
    results, exit_code = run_check(project, config)

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


@app.command()
def fix(
    project: Path = typer.Argument(".", help="Project root directory"),
):
    """Auto-fix fixable violations."""
    project = project.resolve()
    config = load_config(project)

    console.print("[bold]Running auto-fix...[/bold]")
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


@app.command()
def init(
    project: Path = typer.Argument(".", help="Project root directory"),
    root_package: str = typer.Option("myapp", help="Root Python package name"),
):
    """Initialize unified-lint in a project."""
    from .installer import run_init

    project = project.resolve()
    run_init(project, root_package)


@app.command(name="rule")
def rule_list(
    project: Path = typer.Argument(".", help="Project root directory"),
):
    """List available rules."""
    project = project.resolve()
    from .rules.registry import discover_rules
    from .engines.python_ast import PythonAstEngine
    from .engines.markdown_ast import MarkdownAstEngine
    from .engines.tree_sitter_engine import TreeSitterEngine
    from .engines.spec_chain import SpecChainEngine

    rules = discover_rules(project)

    # Add python-ast rules
    ast_engine = PythonAstEngine()
    rules.extend(ast_engine.get_rules())

    # Add markdown-ast rules
    md_engine = MarkdownAstEngine()
    rules.extend(md_engine.get_rules())

    # Add tree-sitter rules
    ts_engine = TreeSitterEngine()
    if ts_engine.is_available():
        ts_rules = ts_engine.get_rules()
        for rule in ts_rules:
            rule["engine"] = "tree-sitter"
        rules.extend(ts_rules)

    # Add spec-chain rules
    sc_engine = SpecChainEngine()
    sc_engine.configure(project)
    rules.extend([
        {"id": "prd_coverage", "engine": "spec-chain", "severity": "error",
         "description": "PRD requirements covered in business architecture"},
        {"id": "metrics_api_compliance", "engine": "spec-chain", "severity": "error",
         "description": "API endpoints meet performance metrics"},
        {"id": "api_code_compliance", "engine": "spec-chain", "severity": "error",
         "description": "Code implements all API endpoints"},
    ])
    
    # Discover and add custom plugin rules
    from .engines.spec_chain import _CHAIN_RULES
    builtin_rules = {"prd_coverage", "metrics_api_compliance", "api_code_compliance"}
    for rule_id, rule_func in _CHAIN_RULES.items():
        if rule_id not in builtin_rules:
            rules.append({
                "id": rule_id,
                "engine": "spec-chain",
                "severity": "error",
                "description": rule_func.__doc__ or f"Custom chain rule: {rule_id}",
            })

    table = Table(title="Available Rules")
    table.add_column("Rule ID", style="cyan")
    table.add_column("Engine", style="magenta")
    table.add_column("Severity", style="yellow")
    table.add_column("Description")

    for rule in rules:
        table.add_row(rule["id"], rule["engine"], rule["severity"], rule["description"])

    console.print(table)


def main():
    app()


if __name__ == "__main__":
    main()
