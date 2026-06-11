"""Tests for spec-chain engine."""

import tempfile
from pathlib import Path

from unified_lint.engines.spec_chain import SpecChainEngine


def test_spec_chain_available():
    """Test that spec-chain engine is available."""
    engine = SpecChainEngine()
    assert engine.is_available()


def test_prd_coverage_violation():
    """Test that PRD coverage violations are detected."""
    engine = SpecChainEngine()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        spec_dir = tmpdir / "specs"
        spec_dir.mkdir()

        # PRD with 3 requirements
        (spec_dir / "prd.md").write_text(
            """---
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
""",
            encoding="utf-8",
        )

        # Architecture only covers 2 of 3
        (spec_dir / "biz-arch.md").write_text(
            """---
stage: biz-arch
id: biz-arch-v1
covers_requirements:
  - REQ-001
  - REQ-002
modules:
  - name: AuthService
    covers: REQ-001
  - name: OrderService
    covers: REQ-002
---
# Architecture
""",
            encoding="utf-8",
        )

        # Create config
        config_dir = tmpdir / ".unified-lint"
        config_dir.mkdir()
        (config_dir / "spec-chain.toml").write_text(
            f"""
[[chains]]
source = "{spec_dir.as_posix()}/prd.md"
target = "{spec_dir.as_posix()}/biz-arch.md"
rule = "prd_coverage"
""",
            encoding="utf-8",
        )

        result = engine.check(tmpdir, {})
        violations = [v for v in result.violations if v.rule_id == "prd_coverage"]

        assert len(violations) == 1
        assert "REQ-003" in violations[0].message


def test_metrics_api_compliance_violation():
    """Test that metrics API compliance violations are detected."""
    engine = SpecChainEngine()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        spec_dir = tmpdir / "specs"
        spec_dir.mkdir()

        # Metrics with P95 latency 200ms
        (spec_dir / "metrics.md").write_text(
            """---
stage: metrics
id: metrics-v1
core_metrics:
  latency_p95_ms: 200
  availability: 99.9
---
# Metrics
""",
            encoding="utf-8",
        )

        # API with one endpoint exceeding latency
        (spec_dir / "api.md").write_text(
            """---
stage: api
id: api-v1
endpoints:
  - path: /api/v1/login
    method: POST
    estimated_latency_ms: 150
    target_availability: 99.9
  - path: /api/v1/orders
    method: GET
    estimated_latency_ms: 250
    target_availability: 99.8
---
# API
""",
            encoding="utf-8",
        )

        # Create config
        config_dir = tmpdir / ".unified-lint"
        config_dir.mkdir()
        (config_dir / "spec-chain.toml").write_text(
            f"""
[[chains]]
source = "{spec_dir.as_posix()}/metrics.md"
target = "{spec_dir.as_posix()}/api.md"
rule = "metrics_api_compliance"
""",
            encoding="utf-8",
        )

        result = engine.check(tmpdir, {})
        violations = [
            v for v in result.violations if v.rule_id == "metrics_api_compliance"
        ]

        # Should have 2 violations: latency and availability
        assert len(violations) == 2

        latency_violation = [v for v in violations if "latency" in v.message.lower()]
        assert len(latency_violation) == 1
        assert "250ms" in latency_violation[0].message
        assert "200ms" in latency_violation[0].message

        availability_violation = [
            v for v in violations if "availability" in v.message.lower()
        ]
        assert len(availability_violation) == 1
        assert "99.8%" in availability_violation[0].message


def test_no_violations():
    """Test that clean documents have no violations."""
    engine = SpecChainEngine()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        spec_dir = tmpdir / "specs"
        spec_dir.mkdir()

        # PRD with 2 requirements
        (spec_dir / "prd.md").write_text(
            """---
stage: prd
id: prd-v1
requirements:
  - id: REQ-001
    name: 用户登录
  - id: REQ-002
    name: 订单管理
---
# PRD
""",
            encoding="utf-8",
        )

        # Architecture covers all requirements
        (spec_dir / "biz-arch.md").write_text(
            """---
stage: biz-arch
id: biz-arch-v1
covers_requirements:
  - REQ-001
  - REQ-002
modules:
  - name: AuthService
    covers: REQ-001
  - name: OrderService
    covers: REQ-002
---
# Architecture
""",
            encoding="utf-8",
        )

        # Create config
        config_dir = tmpdir / ".unified-lint"
        config_dir.mkdir()
        (config_dir / "spec-chain.toml").write_text(
            f"""
[[chains]]
source = "{spec_dir.as_posix()}/prd.md"
target = "{spec_dir.as_posix()}/biz-arch.md"
rule = "prd_coverage"
""",
            encoding="utf-8",
        )

        result = engine.check(tmpdir, {})
        violations = [v for v in result.violations if v.rule_id == "prd_coverage"]
        assert len(violations) == 0
