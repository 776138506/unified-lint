"""Tests for spec-chain engine with plugin support."""

import tempfile
from pathlib import Path

from unified_lint.engines.spec_chain import SpecChainEngine


def test_plugin_loading():
    """Test that plugins are loaded from .unified-lint/rules/ directory."""
    engine = SpecChainEngine()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create plugin file
        rules_dir = tmpdir / ".unified-lint" / "rules"
        rules_dir.mkdir(parents=True)
        
        plugin_code = """from unified_lint.engines.spec_chain import chain_rule, Violation, Severity
from typing import Optional

@chain_rule("custom_check")
def check_custom(
    source: dict, target: dict, source_file: str, target_file: str,
    params: Optional[dict] = None
) -> list[Violation]:
    violations = []
    if source.get("name") != target.get("name"):
        violations.append(Violation(
            rule_id="custom_check",
            message="Name mismatch: {} vs {}".format(source.get("name"), target.get("name")),
            file=target_file,
            severity=Severity.ERROR,
            engine="spec-chain",
        ))
    return violations
"""
        (rules_dir / "custom_check.py").write_text(plugin_code, encoding="utf-8")
        
        # Create test documents
        spec_dir = tmpdir / "specs"
        spec_dir.mkdir()
        
        (spec_dir / "source.md").write_text("""---
stage: test
id: source-v1
name: "TestName"
---
# Source
""", encoding="utf-8")
        
        (spec_dir / "target.md").write_text("""---
stage: test
id: target-v1
name: "DifferentName"
---
# Target
""", encoding="utf-8")
        
        # Create config
        config_dir = tmpdir / ".unified-lint"
        (config_dir / "spec-chain.toml").write_text("""
[[chains]]
source = "specs/source.md"
target = "specs/target.md"
rule = "custom_check"
""", encoding="utf-8")
        
        # Configure and run
        engine.configure(tmpdir)
        result = engine.check(tmpdir, {})
        
        violations = [v for v in result.violations if v.rule_id == "custom_check"]
        assert len(violations) == 1
        assert "Name mismatch" in violations[0].message


def test_params_support():
    """Test that params are passed to rule functions."""
    engine = SpecChainEngine()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create plugin with params support
        rules_dir = tmpdir / ".unified-lint" / "rules"
        rules_dir.mkdir(parents=True)
        
        plugin_code = """from unified_lint.engines.spec_chain import chain_rule, Violation, Severity
from typing import Optional

@chain_rule("param_check")
def check_with_params(
    source: dict, target: dict, source_file: str, target_file: str,
    params: Optional[dict] = None
) -> list[Violation]:
    violations = []
    threshold = params.get("threshold", 100) if params else 100
    actual = target.get("value", 0)
    if actual > threshold:
        violations.append(Violation(
            rule_id="param_check",
            message="Value {} exceeds threshold {}".format(actual, threshold),
            file=target_file,
            severity=Severity.ERROR,
            engine="spec-chain",
        ))
    return violations
"""
        (rules_dir / "param_check.py").write_text(plugin_code, encoding="utf-8")
        
        # Create test documents
        spec_dir = tmpdir / "specs"
        spec_dir.mkdir()
        
        (spec_dir / "source.md").write_text("""---
stage: test
id: source-v1
---
# Source
""", encoding="utf-8")
        
        (spec_dir / "target.md").write_text("""---
stage: test
id: target-v1
value: 150
---
# Target
""", encoding="utf-8")
        
        # Create config with params
        config_dir = tmpdir / ".unified-lint"
        (config_dir / "spec-chain.toml").write_text("""
[[chains]]
source = "specs/source.md"
target = "specs/target.md"
rule = "param_check"

[chains.params]
threshold = 100
""", encoding="utf-8")
        
        # Configure and run
        engine.configure(tmpdir)
        result = engine.check(tmpdir, {})
        
        violations = [v for v in result.violations if v.rule_id == "param_check"]
        assert len(violations) == 1
        assert "Value 150 exceeds threshold 100" in violations[0].message


def test_builtin_rules_still_work():
    """Test that built-in rules still work with plugin system."""
    engine = SpecChainEngine()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        spec_dir = tmpdir / "specs"
        spec_dir.mkdir()

        # PRD with 3 requirements
        (spec_dir / "prd.md").write_text("""---
stage: prd
id: prd-v1
requirements:
  - id: REQ-001
    name: 用户登录
  - id: REQ-002
    name: 订单管理
  - id: REQ-003
    name: 数据导出
---
# PRD
""", encoding="utf-8")

        # Architecture only covers 2 of 3
        (spec_dir / "biz-arch.md").write_text("""---
stage: biz-arch
id: biz-arch-v1
covers_requirements:
  - REQ-001
  - REQ-002
---
# Architecture
""", encoding="utf-8")

        # Create config
        config_dir = tmpdir / ".unified-lint"
        config_dir.mkdir()
        (config_dir / "spec-chain.toml").write_text("""
[[chains]]
source = "specs/prd.md"
target = "specs/biz-arch.md"
rule = "prd_coverage"
""", encoding="utf-8")

        engine.configure(tmpdir)
        result = engine.check(tmpdir, {})
        violations = [v for v in result.violations if v.rule_id == "prd_coverage"]

        assert len(violations) == 1
        assert "REQ-003" in violations[0].message
