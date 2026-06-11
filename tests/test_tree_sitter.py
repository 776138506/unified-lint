"""Tests for tree-sitter engine (Rust and C# rules)."""

import tempfile
from pathlib import Path

from unified_lint.engines.tree_sitter_engine import TreeSitterEngine


def test_tree_sitter_available():
    """Test that tree-sitter engine is available."""
    engine = TreeSitterEngine()
    assert engine.is_available()


def test_rust_unsafe_detection():
    """Test that unsafe blocks are detected in Rust code."""
    engine = TreeSitterEngine()

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        rust_file = project_root / "test.rs"
        rust_file.write_text(
            """
fn main() {
    unsafe {
        let ptr = std::ptr::null::<i32>();
    }
}
"""
        )

        result = engine.check(project_root, {})
        violations = result.violations

        assert len(violations) == 1
        assert violations[0].rule_id == "rust_no_unsafe"
        assert violations[0].line == 3


def test_rust_pub_documentation():
    """Test that public functions without documentation are detected."""
    engine = TreeSitterEngine()

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        rust_file = project_root / "test.rs"
        rust_file.write_text(
            """
pub fn undocumented() {
    println!("No docs");
}

/// This is documented
pub fn documented() {
    println!("Has docs");
}
"""
        )

        result = engine.check(project_root, {})
        violations = [
            v for v in result.violations if v.rule_id == "rust_pub_documentation"
        ]

        assert len(violations) == 1
        assert "undocumented" in violations[0].message


def test_csharp_async_without_await():
    """Test that async methods without await are detected."""
    engine = TreeSitterEngine()

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        cs_file = project_root / "test.cs"
        cs_file.write_text(
            """
using System.Threading.Tasks;

public class Test {
    public async Task BadAsync() {
        System.Console.WriteLine("No await");
    }

    public async Task GoodAsync() {
        await Task.Delay(100);
    }
}
"""
        )

        result = engine.check(project_root, {})
        violations = [v for v in result.violations if v.rule_id == "csharp_async_await"]

        assert len(violations) == 1
        assert "BadAsync" in violations[0].message


def test_csharp_null_return():
    """Test that null returns are detected."""
    engine = TreeSitterEngine()

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        cs_file = project_root / "test.cs"
        cs_file.write_text(
            """
public class Test {
    public string GetNull() {
        return null;
    }

    public string GetValid() {
        return "valid";
    }
}
"""
        )

        result = engine.check(project_root, {})
        violations = [v for v in result.violations if v.rule_id == "csharp_null_return"]

        assert len(violations) == 1
        assert violations[0].line == 4


def test_csharp_class_naming():
    """Test that class naming violations are detected."""
    engine = TreeSitterEngine()

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        cs_file = project_root / "test.cs"
        cs_file.write_text(
            """
public class badClassName {
}

public class GoodClassName {
}
"""
        )

        result = engine.check(project_root, {})
        violations = [
            v for v in result.violations if v.rule_id == "csharp_class_naming"
        ]

        assert len(violations) == 1
        assert "badClassName" in violations[0].message


def test_csharp_method_naming():
    """Test that method naming violations are detected."""
    engine = TreeSitterEngine()

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        cs_file = project_root / "test.cs"
        cs_file.write_text(
            """
public class Test {
    public void badMethodName() {
    }

    public void GoodMethodName() {
    }
}
"""
        )

        result = engine.check(project_root, {})
        violations = [
            v for v in result.violations if v.rule_id == "csharp_method_naming"
        ]

        assert len(violations) == 1
        assert "badMethodName" in violations[0].message


def test_tree_sitter_no_violations():
    """Test that clean code has no violations."""
    engine = TreeSitterEngine()

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Clean Rust code
        rust_file = project_root / "clean.rs"
        rust_file.write_text(
            """
/// Documented function
pub fn good_function() {
    println!("Good");
}
"""
        )

        # Clean C# code
        cs_file = project_root / "clean.cs"
        cs_file.write_text(
            """
using System.Threading.Tasks;

public class GoodClass {
    public async Task GoodAsync() {
        await Task.Delay(100);
    }

    public string GetValid() {
        return "valid";
    }
}
"""
        )

        result = engine.check(project_root, {})
        violations = result.violations

        assert len(violations) == 0
