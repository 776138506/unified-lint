"""Spec-chain engine: validates consistency between documentation stages.

This engine checks that downstream documents properly reference and satisfy
requirements from upstream documents (e.g., PRD -> Architecture -> API).
"""

from pathlib import Path
from typing import Callable, Optional
import importlib.util
import sys
import yaml

from .base import EngineResult, LintEngine, Violation, Severity


# Registry for chain rules
_CHAIN_RULES: dict[str, Callable] = {}


def _load_plugins(project_root: Path) -> None:
    """Load custom rule plugins from .unified-lint/rules/ directory."""
    rules_dir = project_root / ".unified-lint" / "rules"
    if not rules_dir.exists():
        return

    for rule_file in rules_dir.glob("*.py"):
        if rule_file.name.startswith("_"):
            continue  # Skip private files

        try:
            # Load the module
            spec = importlib.util.spec_from_file_location(
                f"unified_lint.rules.{rule_file.stem}", 
                rule_file
            )
            if spec is None or spec.loader is None:
                continue
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
        except Exception as e:
            print(f"Warning: Failed to load rule plugin {rule_file.name}: {e}")


def chain_rule(rule_id: str):
    """Decorator to register a chain validation rule."""

    def decorator(func):
        _CHAIN_RULES[rule_id] = func
        return func

    return decorator


class SpecChainEngine(LintEngine):
    """Validates consistency between documentation stages."""

    name = "spec-chain"

    def __init__(self):
        self.config_path = None

    def is_available(self) -> bool:
        return True  # Always available, no external dependencies

    def configure(self, project_root: Path):
        """Load spec-chain configuration and plugins."""
        # Load custom rule plugins
        _load_plugins(project_root)
        
        # Load configuration
        config_file = project_root / ".unified-lint" / "spec-chain.toml"
        if config_file.exists():
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib
            with open(config_file, "rb") as f:
                self.config_path = tomllib.load(f)

    def check(self, project_root: Path, config: dict) -> EngineResult:
        """Run all chain validation rules."""
        if self.config_path is None:
            self.configure(project_root)

        if not self.config_path:
            return EngineResult(engine_name=self.name, violations=[])

        violations = []

        for chain in self.config_path.get("chains", []):
            source_path = project_root / chain["source"]
            target_path = project_root / chain["target"]
            rule_id = chain["rule"]

            if not source_path.exists():
                violations.append(
                    Violation(
                        rule_id="spec_chain_missing_source",
                        message=f"Chain source not found: {chain['source']}",
                        file=str(source_path),
                        severity=Severity.ERROR,
                        engine=self.name,
                    )
                )
                continue

            if not target_path.exists():
                violations.append(
                    Violation(
                        rule_id="spec_chain_missing_target",
                        message=f"Chain target not found: {chain['target']}",
                        file=str(target_path),
                        severity=Severity.ERROR,
                        engine=self.name,
                    )
                )
                continue

            # Load YAML frontmatter from both files
            source_data = self._load_frontmatter(source_path)
            target_data = self._load_frontmatter(target_path)

            if source_data is None:
                violations.append(
                    Violation(
                        rule_id="spec_chain_invalid_frontmatter",
                        message=f"Invalid or missing frontmatter in {chain['source']}",
                        file=str(source_path),
                        severity=Severity.ERROR,
                        engine=self.name,
                    )
                )
                continue

            if target_data is None:
                violations.append(
                    Violation(
                        rule_id="spec_chain_invalid_frontmatter",
                        message=f"Invalid or missing frontmatter in {chain['target']}",
                        file=str(target_path),
                        severity=Severity.ERROR,
                        engine=self.name,
                    )
                )
                continue

            # Run the chain rule
            if rule_id not in _CHAIN_RULES:
                violations.append(
                    Violation(
                        rule_id="spec_chain_unknown_rule",
                        message=f"Unknown chain rule: {rule_id}",
                        file=str(project_root / ".unified-lint" / "spec-chain.toml"),
                        severity=Severity.ERROR,
                        engine=self.name,
                    )
                )
                continue

            # Get params from config
            params = chain.get("params", {})
            
            try:
                rule_func = _CHAIN_RULES[rule_id]
                rule_violations = rule_func(
                    source_data, target_data, str(source_path), str(target_path),
                    params=params
                )
            except TypeError as e:
                # Handle case where rule doesn't accept params
                if "params" in str(e):
                    rule_func = _CHAIN_RULES[rule_id]
                    rule_violations = rule_func(
                        source_data, target_data, str(source_path), str(target_path)
                    )
                else:
                    violations.append(
                        Violation(
                            rule_id="spec_chain_rule_error",
                            message=f"Rule '{rule_id}' execution failed: {e}",
                            file=str(source_path),
                            severity=Severity.ERROR,
                            engine=self.name,
                        )
                    )
                    continue
            except Exception as e:
                violations.append(
                    Violation(
                        rule_id="spec_chain_rule_error",
                        message=f"Rule '{rule_id}' execution failed: {e}",
                        file=str(source_path),
                        severity=Severity.ERROR,
                        engine=self.name,
                    )
                )
                continue
            violations.extend(rule_violations)

        return EngineResult(engine_name=self.name, violations=violations)

    def _load_frontmatter(self, file_path: Path) -> dict | None:
        """Extract YAML frontmatter from a Markdown file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            if not content.startswith("---"):
                return None

            # Find the second ---
            end_idx = content.find("---", 3)
            if end_idx == -1:
                return None

            frontmatter_text = content[3:end_idx]
            return yaml.safe_load(frontmatter_text)
        except Exception:
            return None


# ─── Chain Rules ─────────────────────────────────────────────


@chain_rule("prd_coverage")
def check_prd_coverage(
    source: dict, target: dict, source_file: str, target_file: str,
    params: Optional[dict] = None
) -> list[Violation]:
    """Check that business architecture covers all PRD requirements."""
    violations = []

    prd_reqs = {r["id"] for r in source.get("requirements", [])}
    covered = set(target.get("covers_requirements", []))

    missing = prd_reqs - covered
    for req_id in missing:
        violations.append(
            Violation(
                rule_id="prd_coverage",
                message=f"PRD requirement '{req_id}' not covered in business architecture",
                file=target_file,
                severity=Severity.ERROR,
                engine="spec-chain",
            )
        )

    return violations


@chain_rule("metrics_api_compliance")
def check_metrics_api_compliance(
    source: dict, target: dict, source_file: str, target_file: str,
    params: Optional[dict] = None
) -> list[Violation]:
    """Check that API endpoints meet performance metrics."""
    violations = []

    core_metrics = source.get("core_metrics", {})
    endpoints = target.get("endpoints", [])

    for endpoint in endpoints:
        path = endpoint.get("path", "unknown")
        estimated_latency = endpoint.get("estimated_latency_ms")
        target_availability = endpoint.get("target_availability")

        # Check latency
        if estimated_latency is not None:
            max_latency = core_metrics.get("latency_p95_ms")
            if max_latency and estimated_latency > max_latency:
                violations.append(
                    Violation(
                        rule_id="metrics_api_compliance",
                        message=(
                            f"Endpoint {path} estimated latency {estimated_latency}ms "
                            f"exceeds P95 target {max_latency}ms"
                        ),
                        file=target_file,
                        severity=Severity.ERROR,
                        engine="spec-chain",
                    )
                )

        # Check availability
        if target_availability is not None:
            required_availability = core_metrics.get("availability")
            if required_availability and target_availability < required_availability:
                violations.append(
                    Violation(
                        rule_id="metrics_api_compliance",
                        message=(
                            f"Endpoint {path} target availability {target_availability}% "
                            f"below requirement {required_availability}%"
                        ),
                        file=target_file,
                        severity=Severity.ERROR,
                        engine="spec-chain",
                    )
                )

    return violations


@chain_rule("api_code_compliance")
def check_api_code_compliance(
    source: dict, target: dict, source_file: str, target_file: str,
    params: Optional[dict] = None
) -> list[Violation]:
    """Check that code implements all API endpoints."""
    violations = []

    api_endpoints = {ep["path"] for ep in source.get("endpoints", [])}
    implemented_paths = set(target.get("implemented_paths", []))

    missing = api_endpoints - implemented_paths
    for path in missing:
        violations.append(
            Violation(
                rule_id="api_code_compliance",
                message=f"API endpoint '{path}' not implemented in code",
                file=target_file,
                severity=Severity.ERROR,
                engine="spec-chain",
            )
        )

    return violations
