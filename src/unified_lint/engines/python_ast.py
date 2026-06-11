"""Python AST engine: uses Python's own ast module for precise code analysis.

This engine handles rules that GritQL's Alpha Python parser cannot,
such as function signature checks, return type analysis, and import graph analysis.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Callable

from .base import EngineResult, LintEngine, Severity, Violation


# Rule function signature: takes file path + AST, returns violations
RuleFn = Callable[[Path, ast.Module], list[Violation]]

_REGISTRY: dict[str, tuple[RuleFn, Severity, str]] = {}


def rule(rule_id: str, severity: Severity, description: str):
    """Decorator to register a Python AST rule."""

    def decorator(fn: RuleFn):
        _REGISTRY[rule_id] = (fn, severity, description)
        return fn

    return decorator


# ── Rules ─────────────────────────────────────────────────────


@rule(
    "service_ctx_first",
    Severity.WARN,
    "Service class methods must have ctx as first parameter after self",
)
def check_service_ctx_first(path: Path, tree: ast.Module) -> list[Violation]:
    """Check that Service class methods have ctx as first param."""
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not node.name.endswith("Service"):
            continue
        for method in node.body:
            if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if method.name.startswith("_"):
                continue
            args = method.args
            # Skip if no params or only self
            all_args = args.args
            if len(all_args) < 2:
                continue
            # First arg after self
            first_after_self = all_args[1]
            if first_after_self.arg not in ("ctx", "context"):
                violations.append(
                    Violation(
                        rule_id="service_ctx_first",
                        message=(
                            f"Service method '{method.name}' first param should be "
                            f"ctx, got '{first_after_self.arg}'"
                        ),
                        file=str(path),
                        line=method.lineno,
                        col=method.col_offset + 1,
                        severity=Severity.WARN,
                        engine="python-ast",
                        fixable=False,
                    )
                )
    return violations


@rule(
    "api_result_wrapper",
    Severity.ERROR,
    "API functions must not return raw dicts/lists",
)
def check_api_result_wrapper(path: Path, tree: ast.Module) -> list[Violation]:
    """Check that API layer functions don't return raw dicts.

    Only checks top-level functions (not class methods), and excludes
    methods in wrapper/serializer classes or methods named to_dict/to_json.
    """
    violations = []
    # Only check files in api/ directory
    if "api" not in str(path).replace("\\", "/").split("/"):
        return violations

    # Find all classes that are wrappers/serializers
    wrapper_classes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Check if class name suggests it's a wrapper/serializer
            name_lower = node.name.lower()
            if any(
                keyword in name_lower
                for keyword in ["result", "response", "wrapper", "serializer"]
            ):
                wrapper_classes.add(node.name)

    # Only check top-level functions (not methods inside classes)
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # Check all return statements in this function
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and isinstance(
                child.value, (ast.Dict, ast.List)
            ):
                violations.append(
                    Violation(
                        rule_id="api_result_wrapper",
                        message=(
                            f"Function '{node.name}' returns raw "
                            f"{'dict' if isinstance(child.value, ast.Dict) else 'list'}, "
                            f"use Result(data=...) wrapper"
                        ),
                        file=str(path),
                        line=child.lineno,
                        col=child.col_offset + 1,
                        severity=Severity.ERROR,
                        engine="python-ast",
                        fixable=False,
                    )
                )
    return violations


@rule(
    "no_bare_except",
    Severity.WARN,
    "Use specific exception types instead of bare except",
)
def check_no_bare_except(path: Path, tree: ast.Module) -> list[Violation]:
    """Check for bare except clauses."""
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            violations.append(
                Violation(
                    rule_id="no_bare_except",
                    message="Bare except clause, use specific exception type",
                    file=str(path),
                    line=node.lineno,
                    col=node.col_offset + 1,
                    severity=Severity.WARN,
                    engine="python-ast",
                    fixable=False,
                )
            )
    return violations


@rule("no_hardcoded_secret", Severity.ERROR, "No hardcoded passwords or API keys")
def check_no_hardcoded_secret(path: Path, tree: ast.Module) -> list[Violation]:
    """Check for hardcoded secrets using AST (more precise than regex)."""
    violations = []
    secret_names = {
        "password",
        "passwd",
        "pwd",
        "secret",
        "api_key",
        "apikey",
        "token",
        "private_key",
    }
    safe_calls = {"getenv", "environ", "get"}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            name = ""
            if isinstance(target, ast.Name):
                name = target.id
            elif isinstance(target, ast.Attribute):
                name = target.attr
            if not name:
                continue
            if name.lower() not in secret_names:
                continue
            # Check if value is a safe call (os.getenv etc)
            if isinstance(node.value, ast.Call):
                func = node.value.func
                func_name = ""
                if isinstance(func, ast.Attribute):
                    func_name = func.attr
                elif isinstance(func, ast.Name):
                    func_name = func.id
                if func_name in safe_calls:
                    continue
            # Check if value is a constant string
            if isinstance(node.value, ast.Constant) and isinstance(
                node.value.value, str
            ):
                if node.value.value == "":
                    continue  # Empty string is ok
                violations.append(
                    Violation(
                        rule_id="no_hardcoded_secret",
                        message=f"Hardcoded secret in '{name}', use os.getenv()",
                        file=str(path),
                        line=node.lineno,
                        col=node.col_offset + 1,
                        severity=Severity.ERROR,
                        engine="python-ast",
                        fixable=False,
                    )
                )
    return violations


@rule("no_n_plus_one", Severity.ERROR, "No database queries inside loops (N+1 problem)")
def check_no_n_plus_one(path: Path, tree: ast.Module) -> list[Violation]:
    """Check for database queries inside for loops."""
    violations = []
    query_methods = {"execute", "executemany", "raw", "extra", "select"}

    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                method_name = ""
                if isinstance(child.func, ast.Attribute):
                    method_name = child.func.attr
                if method_name in query_methods:
                    # Check if any arg contains SELECT
                    for arg in child.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            if "SELECT" in arg.value.upper():
                                violations.append(
                                    Violation(
                                        rule_id="no_n_plus_one",
                                        message=(
                                            f"Database query '{method_name}()' "
                                            f"inside for loop (N+1 problem)"
                                        ),
                                        file=str(path),
                                        line=child.lineno,
                                        col=child.col_offset + 1,
                                        severity=Severity.ERROR,
                                        engine="python-ast",
                                        fixable=False,
                                    )
                                )
    return violations


# ── Engine class ──────────────────────────────────────────────


class PythonAstEngine(LintEngine):
    """Engine that uses Python's ast module for precise code analysis."""

    name = "python-ast"

    def is_available(self) -> bool:
        """Always available (uses stdlib)."""
        return True

    def check(self, project_root: Path, config: dict) -> EngineResult:
        """Run all registered AST rules on Python files."""
        result = EngineResult(engine_name=self.name)
        paths = config.get("grit_paths", ["."])

        py_files = []
        for p in paths:
            target = project_root / p
            if target.is_file() and target.suffix == ".py":
                py_files.append(target)
            elif target.is_dir():
                py_files.extend(target.rglob("*.py"))

        for py_file in py_files:
            # Skip __pycache__, tests, etc.
            if "__pycache__" in str(py_file):
                continue
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError:
                continue  # Skip files that can't be parsed

            rel_path = py_file.relative_to(project_root)
            for rule_id, (fn, severity, desc) in _REGISTRY.items():
                violations = fn(rel_path, tree)
                # Fix file paths to be relative to project root
                for v in violations:
                    v.file = str(rel_path)
                result.violations.extend(violations)

        return result

    def get_rules(self) -> list[dict]:
        """Return info about registered rules."""
        return [
            {
                "id": rule_id,
                "engine": "python-ast",
                "severity": sev.value,
                "description": desc,
            }
            for rule_id, (_, sev, desc) in _REGISTRY.items()
        ]
