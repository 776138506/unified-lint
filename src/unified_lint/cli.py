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
    help=(
        "[bold]unified-lint[/bold] — 一个统一入口、六种引擎、一种配置与退出码。\n"
        "\n"
        "代码规则 + 文档规则 + 架构规则 + 规范链 + 自定义 AST 全部合并。\n"
        "\n"
        "[bold]引擎：[/bold]\n"
        "  - [cyan]grit[/cyan]        - GritQL 模式匹配（代码 + 文档）\n"
        "  - [cyan]python-ast[/cyan]  - Python ast 精确分析\n"
        "  - [cyan]markdown-ast[/cyan]- markdown-it-py 文档分析\n"
        "  - [cyan]tree-sitter[/cyan] - Rust / C# 代码分析\n"
        "  - [cyan]spec-chain[/cyan]  - PRD / 架构 / 代码 一致性\n"
        "  - [cyan]import-linter[/cyan]- 架构分层依赖约束\n"
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
        "  unified-lint rule add                交互式向导创建规则\n"
        "  unified-lint rule add <id> --template=<name>  用模板创建\n"
        "  unified-lint rule edit <id>          在 $EDITOR 中打开规则\n"
        "  unified-lint rule delete <id>        删除项目级规则 override\n"
        "  unified-lint rule export <id> -o f.json  导出规则\n"
        "  unified-lint rule import f.json      导入规则\n"
        "\n"
        "[dim]仓库: https://github.com/776138506/unified-lint[/dim]"
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
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
    help=(
        "Inspect and manage rules.\n"
        "\n"
        "[bold]Subcommands[/bold]:\n"
        "  [cyan]list[/cyan]    List all available rules.\n"
        "  [cyan]show[/cyan]    Show full definition of one rule.\n"
        "  [cyan]add[/cyan]     Create a new GritQL rule (wizard or --template).\n"
        "  [cyan]edit[/cyan]    Open an existing rule's source file in $EDITOR.\n"
        "  [cyan]delete[/cyan]  Delete a project-level rule override.\n"
        "  [cyan]export[/cyan]  Export rule(s) to JSON for sharing.\n"
        "  [cyan]import[/cyan]  Import rule(s) from JSON.\n"
        "\n"
        "[bold]Examples[/bold]:\n"
        "  unified-lint rule list\n"
        "  unified-lint rule show no_hardcoded_password\n"
        "  unified-lint rule add                       # interactive wizard\n"
        "  unified-lint rule add my_rule --template=sensitive_field\n"
        "  unified-lint rule export my_rule -o rule.json\n"
        "  unified-lint rule import rule.json"
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
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
