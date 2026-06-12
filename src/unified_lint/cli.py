"""CLI entry point for unified-lint.

Thin shell: registers typer commands and delegates to cli_commands/ modules.

Adding a new subcommand = add a file to cli_commands/ + 3 lines here.
"""

from __future__ import annotations

import typer

from .cli_commands import (
    check as check_cmd,
    fix as fix_cmd,
    init as init_cmd,
    rule_add as rule_add_cmd,
    rule_delete as rule_delete_cmd,
    rule_edit as rule_edit_cmd,
    rule_export as rule_export_cmd,
    rule_import as rule_import_cmd,
    rule_list as rule_list_cmd,
    rule_show as rule_show_cmd,
)

app = typer.Typer(
    name="unified-lint",
    help="Unified linter: code + docs + architecture in one CLI.",
    no_args_is_help=True,
)


# ---------------------------------------------------------------------------
# Top-level commands
# ---------------------------------------------------------------------------
app.command()(check_cmd.check)
app.command()(fix_cmd.fix)
app.command()(init_cmd.init)


# ---------------------------------------------------------------------------
# rule subcommand group
# ---------------------------------------------------------------------------
rule_app = typer.Typer(
    name="rule",
    help="Inspect and manage rules.",
    no_args_is_help=True,
)

rule_app.command("list")(rule_list_cmd.rule_list)
rule_app.command("show")(rule_show_cmd.rule_show)
rule_app.command("add")(rule_add_cmd.rule_add)
rule_app.command("edit")(rule_edit_cmd.rule_edit)
rule_app.command("delete")(rule_delete_cmd.rule_delete)
rule_app.command("export")(rule_export_cmd.rule_export)
rule_app.command("import")(rule_import_cmd.rule_import)

app.add_typer(rule_app, name="rule")


def main() -> None:
    """Entry point for `python -m unified_lint.cli`."""
    app()


if __name__ == "__main__":
    main()
