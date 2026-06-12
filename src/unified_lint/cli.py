"""CLI entry point for unified-lint.

Top-level commands:
  - check:  Run all lint checks against the project.
  - fix:    Attempt to auto-fix fixable violations (currently a stub).
  - init:   Initialize unified-lint in a project.
  - rule:   Subcommand group for inspecting/managing rules
           (list / show / add / edit / delete).

Help output uses rich markup (Markdown, colors). Each command documents
exit codes and provides examples in its docstring.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .runner import format_results, load_config, run_check, run_fix
from .rules.registry import BUILTIN_RULES, discover_rules

app = typer.Typer(
    name="unified-lint",
    help=(
        "[bold]unified-lint[/bold] — 一个统一入口、六种引擎、一种配置与退出码。\n"
        "\n"
        "代码规则 + 文档规则 + 架构规则 + 规范链 + 自定义 AST 全部合并。\n"
        "\n"
        "[bold]引擎：[/bold]\n"
        "  • [cyan]grit[/cyan]        — GritQL 模式匹配（代码 + 文档）\n"
        "  • [cyan]python-ast[/cyan]  — Python ast 精确分析\n"
        "  • [cyan]markdown-ast[/cyan]— markdown-it-py 文档分析\n"
        "  • [cyan]tree-sitter[/cyan] — Rust / C# 代码分析\n"
        "  • [cyan]spec-chain[/cyan]  — PRD / 架构 / 代码 一致性\n"
        "  • [cyan]import-linter[/cyan]— 架构分层依赖约束\n"
        "\n"
        "[bold]退出码：[/bold]\n"
        "  [green]0[/green] = ALL PASS   "
        "[red]1[/red] = 至少一个 ERROR   "
        "[yellow]2[/yellow] = 只有 WARN   "
        "[red]4[/red] = 工具缺失\n"
        "\n"
        "[bold]示例：[/bold]\n"
        "  unified-lint init .                  初始化项目\n"
        "  unified-lint check .                 跑所有检查\n"
        "  unified-lint check . --engine grit   只跑 GritQL 引擎\n"
        "  unified-lint check . --severity error 只看 ERROR\n"
        "  unified-lint fix .                   尝试自动修复（当前是 stub）\n"
        "  unified-lint rule list               列出所有规则\n"
        "  unified-lint rule show <id>          显示规则详情\n"
        "  unified-lint rule add <id>           创建新规则 stub\n"
        "  unified-lint rule edit <id>          在 $EDITOR 中打开规则\n"
        "  unified-lint rule delete <id>        删除项目级规则 override\n"
        "\n"
        "[dim]仓库: https://github.com/776138506/unified-lint[/dim]"
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


def _discover_all_rules(project_root: Path) -> list[dict]:
    """Discover all rules from every engine + plugins.

    Returns a unified list of dicts. Each dict has:
      - id (str): rule identifier
      - engine (str): grit | python-ast | markdown-ast | tree-sitter |
                      spec-chain | import-linter
      - severity (str): error | warn | info
      - description (str)
      - source (str, optional): builtin | project
    """
    rules: list[dict] = []
    rules.extend(discover_rules(project_root))

    # python-ast rules
    from .engines.python_ast import PythonAstEngine

    rules.extend(PythonAstEngine().get_rules())

    # markdown-ast rules
    from .engines.markdown_ast import MarkdownAstEngine

    rules.extend(MarkdownAstEngine().get_rules())

    # tree-sitter rules (only if available; get_rules() returns fresh dicts
    # each call, so we build new dicts with the engine field instead of mutating)
    from .engines.tree_sitter_engine import TreeSitterEngine

    ts = TreeSitterEngine()
    if ts.is_available():
        rules.extend({**r, "engine": "tree-sitter"} for r in ts.get_rules())

    # spec-chain built-in rules
    rules.extend(
        [
            {
                "id": "prd_coverage",
                "engine": "spec-chain",
                "severity": "error",
                "description": "PRD requirements covered in business architecture",
            },
            {
                "id": "metrics_api_compliance",
                "engine": "spec-chain",
                "severity": "error",
                "description": "API endpoints meet performance metrics",
            },
            {
                "id": "api_code_compliance",
                "engine": "spec-chain",
                "severity": "error",
                "description": "Code implements all API endpoints",
            },
        ]
    )

    # spec-chain plugin rules
    from .engines.spec_chain import _CHAIN_RULES

    builtin_ids = {"prd_coverage", "metrics_api_compliance", "api_code_compliance"}
    for rule_id, rule_func in _CHAIN_RULES.items():
        if rule_id in builtin_ids:
            continue
        doc = rule_func.__doc__ or f"Custom chain rule: {rule_id}"
        rules.append(
            {
                "id": rule_id,
                "engine": "spec-chain",
                "severity": "error",
                "description": doc.strip().split("\n")[0],
            }
        )

    return rules


def _builtin_source_hint(rule_id: str, engine: str) -> str:
    """Return the source-file hint for a builtin rule."""
    hints = {
        "grit": f"src/unified_lint/rules/registry.py (entry id='{rule_id}')",
        "python-ast": f"src/unified_lint/engines/python_ast.py (rule '{rule_id}')",
        "markdown-ast": f"src/unified_lint/engines/markdown_ast.py (rule '{rule_id}')",
        "tree-sitter": (
            f"src/unified_lint/engines/tree_sitter_engine.py (rule '{rule_id}')"
        ),
        "spec-chain": "src/unified_lint/engines/spec_chain.py (_CHAIN_RULES)",
        "import-linter": "src/unified_lint/engines/import_linter.py",
    }
    return hints.get(engine, "unknown engine")


@app.command()
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

    [bold]Exit codes[/bold]:
      0 = ALL PASS, 1 = at least one ERROR, 2 = only WARN, 4 = missing tool.

    [bold]Examples[/bold]:

        unified-lint check .

        unified-lint check ./my-app --engine grit

        unified-lint check . --severity error
    """
    project = project.resolve()
    config = load_config(project)
    results, exit_code = run_check(project, config)

    # Post-hoc filters (don't change runner API)
    if engine:
        results = [r for r in results if r.engine_name == engine]
    if severity:
        for r in results:
            r.violations = [v for v in r.violations if v.severity.value == severity]

    # Re-compute exit_code from filtered results so --engine/--severity
    # don't trip on hidden violations in other engines or severity levels.
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


@app.command()
def fix(
    project: Path = typer.Argument(".", help="Project root directory."),
):
    """Attempt to auto-fix fixable violations.

    [bold yellow]WARNING[/bold yellow]: Currently a stub. `engine.fix()` is a
    no-op in every engine — no files are modified. Re-runs `check` after the
    (no-op) fix attempt. Use `check` + manual editing until a rule implements
    real file modification.

    [bold]Examples[/bold]:

        unified-lint fix .
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


@app.command()
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

    Detects the primary language, generates `.unified-lint/config.toml`
    and `.importlinter`, copies builtin rules to `.grit/patterns/`, and
    updates `.gitignore` to exclude `grit.exe` etc.

    [bold]Will NOT[/bold] overwrite an existing `.importlinter` (manual
    merge required).

    [bold]Examples[/bold]:

        unified-lint init .

        unified-lint init ./my-app --root-package myproject
    """
    from .installer import run_init

    project = project.resolve()
    run_init(project, root_package)


# ---------------------------------------------------------------------------
# rule subcommand group
# ---------------------------------------------------------------------------
rule_app = typer.Typer(
    name="rule",
    help=(
        "Inspect and manage rules.\n"
        "\n"
        "[bold]Subcommands[/bold]:\n"
        "  [cyan]list[/cyan]    List all available rules from every engine.\n"
        "  [cyan]show[/cyan]    Show full definition of one rule "
        "(id, engine, severity, source, content).\n"
        "  [cyan]add[/cyan]     Create a new GritQL rule stub at "
        "`.grit/patterns/<id>.md` for editing.\n"
        "  [cyan]edit[/cyan]    Open an existing rule's source file in $EDITOR.\n"
        "  [cyan]delete[/cyan]  Delete a project-level rule override.\n"
        "\n"
        "[bold]Examples[/bold]:\n"
        "  unified-lint rule list\n"
        "  unified-lint rule list --engine grit\n"
        "  unified-lint rule show no_hardcoded_password\n"
        "  unified-lint rule add my_custom_check\n"
        "  unified-lint rule edit my_custom_check\n"
        "  unified-lint rule delete my_custom_check --yes\n"
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
)


@rule_app.command("list")
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
    """List all available rules in a rich table.

    Use `--engine` to filter by a specific engine.

    [bold]Examples[/bold]:

        unified-lint rule list

        unified-lint rule list --engine python-ast
    """
    project = project.resolve()
    rules = _discover_all_rules(project)

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


@rule_app.command("show")
def rule_show(
    rule_id: str = typer.Argument(..., help="Rule ID (e.g. no_hardcoded_password)."),
    project: Path = typer.Option(
        ".", "--project", "-p", help="Project root directory."
    ),
):
    """Show full definition of one rule.

    Displays: ID, engine, severity, source (builtin / project / plugin),
    description, and the full rule content (GritQL pattern, or 'definition
    not embedded' notice for engine-defined rules).

    [bold]Example[/bold]:

        unified-lint rule show no_hardcoded_password
    """
    project = project.resolve()
    rules = _discover_all_rules(project)

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
            from .engines.spec_chain import _CHAIN_RULES

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


@rule_app.command("add")
def rule_add(
    rule_id: str = typer.Argument(
        ...,
        help="Rule ID (snake_case). Becomes filename: .grit/patterns/<id>.md",
    ),
    project: Path = typer.Option(
        ".", "--project", "-p", help="Project root directory."
    ),
    severity: str = typer.Option(
        "warn",
        "--severity",
        "-s",
        help="Initial severity: error | warn | info",
    ),
    title: Optional[str] = typer.Option(
        None,
        "--title",
        "-t",
        help="Human-readable rule title. Default: derived from rule_id.",
    ),
):
    """Create a new GritQL rule stub at `.grit/patterns/<id>.md`.

    Generates a markdown file with YAML frontmatter and an empty GritQL
    pattern block for you to edit. Pattern names must use underscore
    (not hyphen, per GritQL requirements).

    For python-ast / markdown-ast / spec-chain rules, write the Python
    function manually in `.unified-lint/rules/<id>.py` instead.

    [bold]Example[/bold]:

        unified-lint rule add no_print_in_prod
    """
    project = project.resolve()

    if not re.match(r"^[a-z][a-z0-9_]*$", rule_id):
        console.print(f"[red]Invalid rule_id: '{rule_id}'[/red]")
        console.print(
            "Must be snake_case: lowercase letters, digits, underscore; "
            "starting with a letter."
        )
        raise typer.Exit(code=1)

    if severity not in ("error", "warn", "info"):
        console.print(f"[red]Invalid severity: '{severity}'[/red]")
        console.print("Must be: error | warn | info")
        raise typer.Exit(code=1)

    patterns_dir = project / ".grit" / "patterns"
    target = patterns_dir / f"{rule_id}.md"

    if target.exists():
        console.print(f"[yellow]Rule file already exists: {target}[/yellow]")
        console.print("Edit it directly or pick a different rule_id.")
        raise typer.Exit(code=1)

    if title is None:
        title = rule_id.replace("_", " ").title()

    content = f"""---
name: {rule_id}
title: "{title}"
description: "TODO: describe what this rule checks"
level: {severity}
tags:
  - custom
---

# {title}

```grit
language python

// TODO: write your GritQL pattern here.
// See https://docs.grit.io for syntax.
//
// Example:
// `$name = $value` where {{
//   $name <: r"(?i)password",
//   $value <: not r"os\\.getenv",
// }}
```
"""

    patterns_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    console.print(f"[green]Created rule stub:[/green] {target}")
    console.print("\n[bold]Next steps:[/bold]")
    console.print(f"  1. Edit [cyan]{target}[/cyan] and add your GritQL pattern")
    console.print(f"  2. Run [cyan]unified-lint rule show {rule_id}[/cyan] to preview")
    console.print(f"  3. Run [cyan]unified-lint check .[/cyan] to verify it works")


@rule_app.command("edit")
def rule_edit(
    rule_id: str = typer.Argument(..., help="Rule ID to edit."),
    project: Path = typer.Option(
        ".", "--project", "-p", help="Project root directory."
    ),
):
    """Open an existing rule's source file in $EDITOR.

    For project-level GritQL rules (override files at
    `.grit/patterns/<id>.md`), opens the override file.

    For builtin rules, prints the engine source file path (read-only hint —
    edit the package source to change builtin behavior, or use
    `rule add` first to create an editable override).

    [bold]Editor resolution[/bold]:
      1. `$EDITOR` env var (e.g. `vim`, `code --wait`)
      2. `$VISUAL` env var
      3. Windows: `notepad`,  macOS / Linux: `vi`

    [bold]Examples[/bold]:

        unified-lint rule edit no_hardcoded_password

        EDITOR="code --wait" unified-lint rule edit my_rule
    """
    project = project.resolve()
    override = project / ".grit" / "patterns" / f"{rule_id}.md"

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

    # No project override — locate builtin definition
    rules = _discover_all_rules(project)
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
        console.print(f"  • {eng}: [dim]{_builtin_source_hint(rule_id, eng)}[/dim]")
    console.print(
        f"\nTo make this rule editable, create an override first:\n"
        f"  [cyan]unified-lint rule add {rule_id}[/cyan]\n"
        f"Then re-run [cyan]unified-lint rule edit {rule_id}[/cyan]."
    )


@rule_app.command("delete")
def rule_delete(
    rule_id: str = typer.Argument(..., help="Rule ID to delete (project override)."),
    project: Path = typer.Option(
        ".", "--project", "-p", help="Project root directory."
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
):
    """Delete a project-level GritQL rule override.

    Only deletes the project-level override at `.grit/patterns/<id>.md`.
    Builtin rules cannot be deleted (they live in the package source).
    To restore builtin behavior after a project override, delete the
    override file.

    [bold]Examples[/bold]:

        unified-lint rule delete my_custom_rule

        unified-lint rule delete my_custom_rule --yes
    """
    project = project.resolve()
    target = project / ".grit" / "patterns" / f"{rule_id}.md"

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


# Register rule subcommand group under main app
app.add_typer(rule_app, name="rule")


def main() -> None:
    """Module entry point used by `python -m unified_lint.cli`."""
    app()


if __name__ == "__main__":
    main()
