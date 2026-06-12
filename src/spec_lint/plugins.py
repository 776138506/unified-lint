"""Decorator for defining custom chain rules.

Usage in plugins:

    from spec_lint.plugins import chain_rule

    @chain_rule("my_custom_rule")
    def check_my_rule(index, specs_dir):
        violations = []
        ...
        return violations
"""

from __future__ import annotations

from typing import Callable

from .validator import Violation


def chain_rule(rule_id: str, severity: str = "error"):
    """Decorator to register a custom chain rule.

    The wrapped function must accept (index: dict, specs_dir: Path) and
    return a list[Violation].
    """

    def decorator(func: Callable) -> Callable:
        func._is_chain_rule = True
        func._rule_id = rule_id
        func._severity = severity
        return func

    return decorator
