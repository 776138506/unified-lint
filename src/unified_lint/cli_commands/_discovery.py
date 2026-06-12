"""Shared rule discovery and source-location helpers.

Used by rule_list, rule_show, rule_edit.
"""

from __future__ import annotations

from pathlib import Path

from ..rules.registry import BUILTIN_RULES, discover_rules


def builtin_source_hint(rule_id: str, engine: str) -> str:
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


def discover_all_rules(project_root: Path) -> list[dict]:
    """Discover all rules from every engine + plugins.

    Returns a unified list of dicts. Each dict has:
      - id (str)
      - engine (str)
      - severity (str)
      - description (str)
      - source (str, optional): builtin | project
    """
    rules: list[dict] = []
    rules.extend(discover_rules(project_root))

    from ..engines.python_ast import PythonAstEngine
    from ..engines.markdown_ast import MarkdownAstEngine
    from ..engines.tree_sitter_engine import TreeSitterEngine
    from ..engines.spec_chain import _CHAIN_RULES

    rules.extend(PythonAstEngine().get_rules())
    rules.extend(MarkdownAstEngine().get_rules())

    ts = TreeSitterEngine()
    if ts.is_available():
        rules.extend({**r, "engine": "tree-sitter"} for r in ts.get_rules())

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
