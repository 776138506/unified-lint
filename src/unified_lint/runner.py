"""Runner: orchestrates engines and aggregates results."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .engines.base import EngineResult, Severity
from .engines.grit import GritEngine
from .engines.import_linter import ImportLinterEngine

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
    """Get enabled engines based on config."""
    engines = []

    if config.get("code", {}).get("enabled", True) or config.get("docs", {}).get(
        "enabled", True
    ):
        engines.append(GritEngine())

    if config.get("layers", {}).get("enabled", True):
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
    # Track worst exit code. Lower severity number = more severe.
    # 0=pass, 1=error, 2=warn, 3=info, 4=missing
    worst_exit = 0

    for engine in engines:
        if not engine.is_available():
            results.append(
                EngineResult(
                    engine_name=engine.name, error=f"{engine.name} not available"
                )
            )
            worst_exit = 4  # missing tool is always worst-case signal
            continue

        grit_paths = []
        if config.get("code", {}).get("enabled", True):
            grit_paths.extend(config.get("code", {}).get("paths", ["."]))
        if config.get("docs", {}).get("enabled", True):
            grit_paths.extend(config.get("docs", {}).get("paths", ["docs"]))

        engine_config = {"grit_paths": grit_paths}
        result = engine.check(project_root, engine_config)
        results.append(result)

        if result.error:
            worst_exit = 4
        elif result.has_errors:
            # ERROR is the most severe - set to 1 unless already missing
            if worst_exit != 4:
                worst_exit = 1
        elif result.violations:
            # Find the most severe violation
            best_sev = min(v.severity.exit_priority for v in result.violations)
            # Only upgrade: don't overwrite error(1) with warn(2)
            if worst_exit == 0 or best_sev < worst_exit:
                worst_exit = best_sev

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
