"""rule export subcommand: export rule(s) to a JSON file for sharing."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from ._discovery import discover_all_rules
from ._helpers import console, rule_file_path

console = Console()

EXPORT_FORMAT_VERSION = 1


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter (simple key:value/list parser)."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---", 3)
    if end < 0:
        return {}, content
    fm_text = content[3:end].strip()
    body = content[end + 4 :].lstrip("\n")

    fm: dict = {}
    current_list_key = None
    for line in fm_text.splitlines():
        if line.startswith("  - "):
            if current_list_key:
                fm[current_list_key].append(line[4:].strip())
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if not value:
                fm[key] = []
                current_list_key = key
            else:
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                fm[key] = value
                current_list_key = None
    return fm, body


def rule_export(
    rule_id: str = typer.Argument(
        ...,
        help="Rule ID to export. Ignored if --all is specified.",
    ),
    output: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Output JSON file path.",
    ),
    project: Path = typer.Option(
        ".", "--project", "-p", help="Project root directory."
    ),
    all_rules: bool = typer.Option(
        False, "--all", help="Export all project-level rules (ignores rule_id)."
    ),
):
    """Export rule(s) to a JSON file for cross-project sharing.

    Output JSON format (consumed by `rule import`):
        {
          "version": 1,
          "rules": [
            {
              "id": "my_rule",
              "title": "...",
              "description": "...",
              "severity": "warn",
              "tags": ["custom"],
              "pattern_markdown": "```grit\\n...\\n```"
            }
          ]
        }

    Use `unified-lint rule import <file>` to import into another project.
    """
    project = project.resolve()

    if all_rules:
        if rule_id:
            console.print(
                "[yellow]Both rule_id and --all specified; using --all[/yellow]"
            )

        rules_meta = [
            r for r in discover_all_rules(project) if r.get("source") == "project"
        ]
        targets = []
        for r in rules_meta:
            target = rule_file_path(project, r["id"])
            if target.exists():
                targets.append((r["id"], target))

        if not targets:
            console.print(
                "[yellow]No project-level rules to export.[/yellow]\n"
                "Run 'unified-lint rule list' to see all rules."
            )
            raise typer.Exit(code=1)
    else:
        target = rule_file_path(project, rule_id)
        if not target.exists():
            console.print(
                f"[yellow]No project-level rule '{rule_id}' to export.[/yellow]"
            )
            console.print(
                "Only project overrides can be exported. Builtin rules "
                "live in the package source."
            )
            raise typer.Exit(code=1)
        targets = [(rule_id, target)]

    rules_data = []
    for rid, path in targets:
        content = path.read_text(encoding="utf-8")
        fm, body = _parse_frontmatter(content)

        tags_value = fm.get("tags", ["custom"])
        if not isinstance(tags_value, list):
            tags_value = ["custom"]

        rules_data.append(
            {
                "id": rid,
                "title": fm.get("title", rid.replace("_", " ").title()),
                "description": fm.get("description", ""),
                "severity": fm.get("level", "warn"),
                "tags": tags_value,
                "pattern_markdown": body.strip(),
            }
        )

    payload = {
        "version": EXPORT_FORMAT_VERSION,
        "rules": rules_data,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    console.print(f"[green]Exported {len(rules_data)} rule(s) to:[/green] {output}")
    for r in rules_data:
        console.print(f"  - [cyan]{r['id']}[/cyan] ({r['severity']})")
