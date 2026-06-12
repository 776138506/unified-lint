"""rule import subcommand: import rules from a JSON file."""

from __future__ import annotations

import json
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

console = Console()


IMPORT_FORMAT_VERSION = 1


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from a markdown rule file.

    Returns (frontmatter_dict, body). frontmatter is empty dict if missing.
    """
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---", 3)
    if end < 0:
        return {}, content
    fm_text = content[3:end].strip()
    body = content[end + 4 :].lstrip("\n")

    # Simple YAML-ish parser (avoids requiring PyYAML for trivial cases)
    fm: dict = {}
    current_list_key: Optional[str] = None
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
                # Strip surrounding quotes if present
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                fm[key] = value
                current_list_key = None
    return fm, body


def rule_import(
    source: Path = typer.Argument(
        ...,
        help="JSON file to import (created by `rule export`).",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    project: Path = typer.Option(
        ".", "--project", "-p", help="Project root directory."
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts."),
):
    """Import rule(s) from a JSON file into the project.

    Source JSON format (from `rule export`):
        {
          "version": 1,
          "rules": [
            {
              "id": "my_rule",
              "title": "My Rule",
              "description": "...",
              "severity": "warn",
              "tags": ["custom"],
              "pattern_markdown": "```grit\\n...\\n```"
            }
          ]
        }

    Each rule is written to `.grit/patterns/<id>.md`.
    """
    project = project.resolve()

    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON in {source}:[/red] {e}")
        raise typer.Exit(code=1)

    version = data.get("version", 0)
    if version != IMPORT_FORMAT_VERSION:
        console.print(
            f"[yellow]Warning: file version is {version}, "
            f"this tool expects {IMPORT_FORMAT_VERSION}.[/yellow]"
        )

    rules = data.get("rules", [])
    if not rules:
        console.print("[yellow]No rules found in source file.[/yellow]")
        raise typer.Exit(code=1)

    if not yes:
        console.print(
            f"About to import {len(rules)} rule(s) from [cyan]{source}[/cyan]:"
        )
        for r in rules:
            console.print(
                f"  - [cyan]{r.get('id', '?')}[/cyan] ({r.get('severity', '?')})"
            )
        if not typer.confirm("Proceed?", default=False):
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(code=0)

    ensure_patterns_dir(project)
    imported = 0
    skipped = 0

    for r in rules:
        rid = r.get("id")
        if not rid:
            console.print("[yellow]Skipping rule with no 'id' field[/yellow]")
            skipped += 1
            continue

        try:
            validate_rule_id(rid)
        except SystemExit:
            console.print(f"[yellow]Skipping invalid rule_id: '{rid}'[/yellow]")
            skipped += 1
            continue

        sev = r.get("severity", "warn")
        try:
            validate_severity(sev)
        except SystemExit:
            console.print(
                f"[yellow]Skipping '{rid}': invalid severity '{sev}'[/yellow]"
            )
            skipped += 1
            continue

        target = rule_file_path(project, rid)
        if target.exists() and not yes:
            if not typer.confirm(f"Overwrite existing rule '{rid}'?", default=False):
                console.print(f"[dim]Skipped '{rid}' (exists)[/dim]")
                skipped += 1
                continue

        # Reconstruct the markdown file from JSON fields
        title = r.get("title", rid.replace("_", " ").title())
        description = r.get("description", "")
        tags = r.get("tags", ["custom"])
        pattern_markdown = r.get("pattern_markdown", "")
        if not pattern_markdown:
            # Fallback: try to get pattern from full markdown body
            body = r.get("body", "")
            pattern_markdown = body

        tags_yaml = "\n".join(f"  - {t}" for t in tags)

        content = (
            f"---\n"
            f"name: {rid}\n"
            f'title: "{title}"\n'
            f'description: "{description}"\n'
            f"level: {sev}\n"
            f"tags:\n"
            f"{tags_yaml}\n"
            f"---\n"
            "\n"
            f"# {title}\n"
            "\n"
            f"{pattern_markdown}\n"
        )

        target.write_text(content, encoding="utf-8")
        console.print(f"[green]Imported:[/green] {rid}")
        imported += 1

    console.print(f"\n[bold]Done:[/bold] imported {imported}, skipped {skipped}")
