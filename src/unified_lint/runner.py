"""Runner: orchestrates engines and aggregates results."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .engines.base import EngineResult, Severity
from .engines.grit import GritEngine
from .engines.import_linter import ImportLinterEngine
from .engines.python_ast import PythonAstEngine
from .engines.markdown_ast import MarkdownAstEngine
from .engines.tree_sitter_engine import TreeSitterEngine
from .engines.spec_chain import SpecChainEngine

# Try tomllib (3.11+) or tomli
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


def load_config(project_root: Path) -> dict:
    """Load .unified-lint/config.toml."""
    config_path = project_root / ".unified-lint" / "config.toml"
    if not config_path.exists():
        return {
            "layers": {"enabled": True},
            "code": {"enabled": True},
            "docs": {"enabled": True},
        }
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def get_engines(config: dict) -> list:
    """Get enabled engines based on config.

    Per-engine opt-out via [engines] section (e.g. ``gritql = false``)
    takes precedence over the legacy [code]/[docs]/[layers] coarse flags.
    Missing per-engine keys default to True so an [engines] block that
    lists only one engine still keeps the rest enabled.
    """
    engines_flags = config.get("engines", {})

    # Legacy coarse-grained flags. Kept for backward compatibility — when
    # [engines] is absent, behavior is unchanged from pre-2026-07 versions.
    code_enabled = config.get("code", {}).get("enabled", True)
    docs_enabled = config.get("docs", {}).get("enabled", True)
    layers_enabled = config.get("layers", {}).get("enabled", True)

    engines = []
    if engines_flags.get("gritql", code_enabled or docs_enabled):
        engines.append(GritEngine())
    if engines_flags.get("python_ast", code_enabled):
        engines.append(PythonAstEngine())
    if engines_flags.get("markdown_ast", docs_enabled):
        engines.append(MarkdownAstEngine())
    if engines_flags.get("tree_sitter", code_enabled):
        engines.append(TreeSitterEngine())
    if engines_flags.get("spec_chain", docs_enabled):
        engines.append(SpecChainEngine())
    if engines_flags.get("import_linter", layers_enabled):
        engines.append(ImportLinterEngine())

    return engines


def run_check(
    project_root: Path, config: Optional[dict] = None
) -> tuple[list[EngineResult], int]:
    """Run all enabled engines and return (results, exit_code).

    Exit codes: 0=pass, 1=error, 2=warn, 3=info, 4=missing tool.
    When multiple engines report different severities, the most severe wins.
    """
    if config is None:
        config = load_config(project_root)

    engines = get_engines(config)
    results: list[EngineResult] = []
    worst_exit = 0

    for engine in engines:
        if not engine.is_available():
            results.append(
                EngineResult(
                    engine_name=engine.name, error=f"{engine.name} not available"
                )
            )
            worst_exit = 4
            continue

        grit_paths = []
        if config.get("code", {}).get("enabled", True):
            grit_paths.extend(config.get("code", {}).get("paths", ["."]))
        if config.get("docs", {}).get("enabled", True):
            grit_paths.extend(config.get("docs", {}).get("paths", ["docs"]))

        engine_config = {"grit_paths": grit_paths}
        result = engine.check(project_root, engine_config)
        results.append(result)

        if result.has_errors:
            # Severity.ERROR violations take highest priority
            worst_exit = 1
        elif result.violations:
            # Warnings or info violations
            best_sev = min(v.severity.exit_priority for v in result.violations)
            if worst_exit == 0 or (worst_exit != 1 and best_sev < worst_exit):
                worst_exit = best_sev
        elif result.error and worst_exit == 0:
            # Engine error, but only if no violations found yet
            worst_exit = 4

    return results, worst_exit


def run_fix(
    project_root: Path, config: Optional[dict] = None
) -> tuple[list[EngineResult], int]:
    """Run fix on all engines, then re-check."""
    if config is None:
        config = load_config(project_root)

    engines = get_engines(config)
    for engine in engines:
        if engine.is_available():
            grit_paths = config.get("code", {}).get("paths", ["."])
            engine.fix(project_root, {"grit_paths": grit_paths})

    return run_check(project_root, config)


def format_results(results: list[EngineResult]) -> str:
    """Format results for terminal output."""
    lines = []
    total_violations = 0

    for result in results:
        lines.append(f"\n--- {result.engine_name} ---")

        if result.error:
            lines.append(f"  ERROR: {result.error}")
            continue

        if result.ok:
            lines.append("  OK - no violations")
            continue

        for v in result.violations:
            sev_icon = {"error": "x", "warn": "!", "info": "i"}[v.severity.value]
            lines.append(f"  [{sev_icon}] {v.file}:{v.line} {v.rule_id}: {v.message}")
            total_violations += 1

    if total_violations > 0:
        lines.append(f"\nTotal: {total_violations} violation(s)")

    return "\n".join(lines)
