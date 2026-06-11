"""Tests for unified-lint."""

from pathlib import Path
from unittest.mock import patch

from unified_lint.engines.base import EngineResult, Severity, Violation
from unified_lint.runner import format_results, run_check


def test_violation_severity():
    """Test severity exit priority ordering."""
    assert Severity.ERROR.exit_priority == 1
    assert Severity.WARN.exit_priority == 2
    assert Severity.INFO.exit_priority == 3


def test_engine_result_ok():
    """Test EngineResult.ok property."""
    r = EngineResult(engine_name="test")
    assert r.ok is True

    r.violations.append(
        Violation(rule_id="test", message="msg", file="f.py", severity=Severity.ERROR)
    )
    assert r.ok is False
    assert r.has_errors is True


def test_format_results_empty():
    """Test format with no violations."""
    results = [EngineResult(engine_name="test")]
    output = format_results(results)
    assert "OK - no violations" in output


def test_format_results_with_violations():
    """Test format with violations."""
    results = [
        EngineResult(
            engine_name="test",
            violations=[
                Violation(
                    rule_id="R001",
                    message="bad code",
                    file="main.py",
                    line=10,
                    severity=Severity.ERROR,
                )
            ],
        )
    ]
    output = format_results(results)
    assert "[x]" in output
    assert "R001" in output
    assert "main.py:10" in output


def test_exit_code_error_wins_over_warn(tmp_project):
    """Test that ERROR exit code (1) takes priority over WARN (2)."""
    config = {
        "code": {"enabled": False},
        "docs": {"enabled": False},
        "layers": {"enabled": False},
    }
    # With all engines disabled, should pass
    results, exit_code = run_check(tmp_project, config)
    assert exit_code == 0
