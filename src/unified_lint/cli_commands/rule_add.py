"""rule add subcommand with interactive wizard support."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ._helpers import (
    console,
    ensure_patterns_dir,
    rule_file_path,
    validate_rule_id,
    validate_severity,
)
from ._templates import TEMPLATE_CHOICES, TEMPLATES, render_rule_file

console = Console()


def _run_wizard() -> tuple[str, str, str]:
    """Interactive wizard for rule creation.

    Returns: (rule_id, severity, title, template_name)
    """
    from rich.prompt import Prompt

    console.print("\n[bold cyan]unified-lint rule add — Interactive Wizard[/bold cyan]")
    console.print("[dim]Press Ctrl+C to cancel at any time.[/dim]\n")

    # 1. rule_id
    while True:
        rule_id = Prompt.ask(
            "[bold]Rule ID[/bold] (snake_case, e.g. [cyan]no_print[/cyan])"
        )
        if rule_id:
            try:
                validate_rule_id(rule_id)
                break
            except SystemExit:
                continue
        console.print("[red]Rule ID required.[/red]")

    # 2. title
    default_title = rule_id.replace("_", " ").title()
    title = Prompt.ask("[bold]Title[/bold]", default=default_title)
    if not title:
        title = default_title

    # 3. severity
    severity = Prompt.ask(
        "[bold]Severity[/bold]",
        choices=["error", "warn", "info"],
        default="warn",
    )

    # 4. template
    console.print("\n[bold]Pattern template:[/bold]")
    template_list = list(TEMPLATES.items())
    for i, (key, tpl) in enumerate(template_list, 1):
        console.print(f"  [cyan]{i}[/cyan]. {key:20s} — {tpl['description']}")
    console.print()

    choice = Prompt.ask(
        "[bold]Choose template[/bold]",
        choices=[str(i) for i in range(1, len(template_list) + 1)],
        default="1",
    )
    template_name = template_list[int(choice) - 1][0]

    return rule_id, title, severity, template_name


def rule_add(
    rule_id: Optional[str] = typer.Argument(
        None,
        help="Rule ID (snake_case). If omitted, enters interactive wizard.",
    ),
    project: Path = typer.Option(
        ".", "--project", "-p", help="Project root directory."
    ),
    severity: Optional[str] = typer.Option(
        None,
        "--severity",
        "-s",
        help="Initial severity: error | warn | info (default: warn)",
    ),
    title: Optional[str] = typer.Option(
        None,
        "--title",
        "-t",
        help="Human-readable rule title. Default: derived from rule_id.",
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        help=(
            f"Pattern template. Choices: {', '.join(TEMPLATE_CHOICES)}. "
            f"Default (no flag): sensitive_field"
        ),
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Force interactive wizard even if rule_id is provided.",
    ),
):
    """Create a new GritQL rule stub at `.grit/patterns/<id>.md`.

    Without rule_id (or with --interactive), enters wizard mode that asks
    for title, severity, and pattern template.

    With --template=<name>, generates a rule with a complete working
    GritQL pattern (sensitive_field | func_signature | naming | no_print
    | custom).

    Examples:

        unified-lint rule add                      # wizard

        unified-lint rule add my_rule              # custom stub (TODO)

        unified-lint rule add no_print --template=no_print

        unified-lint rule add my_rule -i           # wizard even with id
    """
    project = project.resolve()

    # Determine inputs: wizard if no rule_id or --interactive
    if rule_id is None or interactive:
        if rule_id is not None and title is None:
            # If id given but no title, use it as default in wizard
            pass
        rule_id, title, severity, template = _run_wizard()
    else:
        # CLI mode: validate or use defaults
        validate_rule_id(rule_id)
        if title is None:
            title = rule_id.replace("_", " ").title()
        if severity is None:
            severity = "warn"
        else:
            validate_severity(severity)
        if template is None:
            template = "sensitive_field"  # default to a working template
        elif template not in TEMPLATE_CHOICES:
            console.print(
                f"[red]Unknown template: '{template}'[/red]\n"
                f"Choices: {', '.join(TEMPLATE_CHOICES)}"
            )
            raise typer.Exit(code=1)

    validate_rule_id(rule_id)
    validate_severity(severity)

    target = rule_file_path(project, rule_id)
    if target.exists():
        console.print(f"[yellow]Rule file already exists: {target}[/yellow]")
        console.print("Edit it directly or pick a different rule_id.")
        raise typer.Exit(code=1)

    ensure_patterns_dir(project)

    content = render_rule_file(
        rule_id=rule_id,
        title=title,
        severity=severity,
        template_name=template,
    )
    target.write_text(content, encoding="utf-8")

    console.print(f"\n[green]Created rule stub:[/green] {target}")
    console.print(f"  Template: [cyan]{template}[/cyan]")
    console.print(f"  Severity: [yellow]{severity}[/yellow]")
    console.print("\n[bold]Next steps:[/bold]")
    console.print(f"  1. Edit [cyan]{target}[/cyan] to customize the pattern")
    console.print(f"  2. Run [cyan]unified-lint rule show {rule_id}[/cyan] to preview")
    console.print(f"  3. Run [cyan]unified-lint check .[/cyan] to verify it works")
