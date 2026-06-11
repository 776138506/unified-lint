"""Tree-sitter engine for multi-language AST analysis (Rust, C#)."""

from __future__ import annotations

from pathlib import Path
from typing import List

from .base import EngineResult, LintEngine, Severity, Violation


class TreeSitterEngine(LintEngine):
    """Engine using tree-sitter for Rust and C# code analysis."""

    name = "tree-sitter"

    def __init__(self):
        self.languages = {}
        self._init_languages()

    def _init_languages(self):
        """Initialize tree-sitter language parsers."""
        try:
            from tree_sitter import Language
            import tree_sitter_rust
            import tree_sitter_c_sharp

            self.languages["rust"] = Language(tree_sitter_rust.language())
            self.languages["c_sharp"] = Language(tree_sitter_c_sharp.language())
        except ImportError:
            pass

    def is_available(self) -> bool:
        """Check if tree-sitter is installed."""
        return len(self.languages) > 0

    def check(self, project_root: Path, config: dict) -> EngineResult:
        """Check Rust and C# files in the project."""
        result = EngineResult(engine_name=self.name)

        # Find Rust files
        rust_files = list(project_root.rglob("*.rs"))
        for file_path in rust_files:
            violations = self._check_rust_file(file_path, project_root)
            result.violations.extend(violations)

        # Find C# files
        csharp_files = list(project_root.rglob("*.cs"))
        for file_path in csharp_files:
            violations = self._check_csharp_file(file_path, project_root)
            result.violations.extend(violations)

        return result

    def _check_rust_file(self, file_path: Path, project_root: Path) -> List[Violation]:
        """Check a single Rust file."""
        violations = []

        if "rust" not in self.languages:
            return violations

        try:
            from tree_sitter import Parser

            parser = Parser(self.languages["rust"])
            content = file_path.read_text(encoding="utf-8")
            tree = parser.parse(bytes(content, "utf-8"))

            # Rule 1: Detect unsafe blocks
            violations.extend(self._rust_check_unsafe(tree, file_path, project_root))

            # Rule 2: Function length
            violations.extend(
                self._rust_check_function_length(tree, file_path, project_root)
            )

            # Rule 3: Public API documentation
            violations.extend(
                self._rust_check_pub_documentation(tree, file_path, project_root)
            )

        except Exception:
            pass

        return violations

    def _rust_check_unsafe(
        self, tree, file_path: Path, project_root: Path
    ) -> List[Violation]:
        """Detect unsafe blocks in Rust code."""
        violations = []

        def visit(node):
            if node.type == "unsafe_block":
                rel_path = file_path.relative_to(project_root)
                violations.append(
                    Violation(
                        rule_id="rust_no_unsafe",
                        message="Unsafe block detected - ensure this is necessary and well-documented",
                        file=str(rel_path),
                        line=node.start_point[0] + 1,
                        col=node.start_point[1] + 1,
                        severity=Severity.WARN,
                        engine=self.name,
                    )
                )

            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return violations

    def _rust_check_function_length(
        self, tree, file_path: Path, project_root: Path, max_lines=50
    ) -> List[Violation]:
        """Check function length in Rust code."""
        violations = []

        def visit(node):
            if node.type == "function_item":
                # Get function name
                name_node = None
                for child in node.children:
                    if child.type == "identifier":
                        name_node = child
                        break

                if name_node:
                    start_line = node.start_point[0] + 1
                    end_line = node.end_point[0] + 1
                    length = end_line - start_line

                    if length > max_lines:
                        rel_path = file_path.relative_to(project_root)
                        violations.append(
                            Violation(
                                rule_id="rust_function_length",
                                message=f"Function '{name_node.text.decode('utf-8')}' is {length} lines (max {max_lines})",
                                file=str(rel_path),
                                line=start_line,
                                col=1,
                                severity=Severity.WARN,
                                engine=self.name,
                            )
                        )

            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return violations

    def _rust_check_pub_documentation(
        self, tree, file_path: Path, project_root: Path
    ) -> List[Violation]:
        """Check that public APIs have documentation."""
        violations = []

        def visit(node):
            if node.type == "function_item":
                # Check if function is public
                is_pub = False
                name_node = None
                has_doc = False

                for child in node.children:
                    if child.type == "visibility_modifier" and b"pub" in child.text:
                        is_pub = True
                    elif child.type == "identifier":
                        name_node = child
                    elif child.type == "line_comment" and child.text.startswith(b"///"):
                        has_doc = True

                # Check previous sibling for doc comments
                prev = node.prev_sibling
                while prev and prev.type == "line_comment":
                    if prev.text.startswith(b"///"):
                        has_doc = True
                        break
                    prev = prev.prev_sibling

                if is_pub and name_node and not has_doc:
                    rel_path = file_path.relative_to(project_root)
                    violations.append(
                        Violation(
                            rule_id="rust_pub_documentation",
                            message=f"Public function '{name_node.text.decode('utf-8')}' lacks documentation (/// comment)",
                            file=str(rel_path),
                            line=node.start_point[0] + 1,
                            col=1,
                            severity=Severity.WARN,
                            engine=self.name,
                        )
                    )

            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return violations

    def _check_csharp_file(
        self, file_path: Path, project_root: Path
    ) -> List[Violation]:
        """Check a single C# file."""
        violations = []

        if "c_sharp" not in self.languages:
            return violations

        try:
            from tree_sitter import Parser

            parser = Parser(self.languages["c_sharp"])
            content = file_path.read_text(encoding="utf-8")
            tree = parser.parse(bytes(content, "utf-8"))

            # Rule 1: Async without await
            violations.extend(
                self._csharp_check_async_await(tree, file_path, project_root)
            )

            # Rule 2: Null checks
            violations.extend(self._csharp_check_null(tree, file_path, project_root))

            # Rule 3: Naming conventions
            violations.extend(self._csharp_check_naming(tree, file_path, project_root))

        except Exception:
            pass

        return violations

    def _csharp_check_async_await(
        self, tree, file_path: Path, project_root: Path
    ) -> List[Violation]:
        """Detect async methods without await."""
        violations = []

        def visit(node):
            if node.type == "method_declaration":
                # Check if method is async
                is_async = False
                has_await = False
                name_node = None

                for child in node.children:
                    if child.type == "modifier" and b"async" in child.text:
                        is_async = True
                    elif child.type == "identifier":
                        name_node = child
                    elif child.type == "block":
                        # Check for await in method body
                        def check_await(n):
                            nonlocal has_await
                            if n.type == "await_expression":
                                has_await = True
                            for c in n.children:
                                check_await(c)

                        check_await(child)

                if is_async and not has_await and name_node:
                    rel_path = file_path.relative_to(project_root)
                    violations.append(
                        Violation(
                            rule_id="csharp_async_await",
                            message=f"Async method '{name_node.text.decode('utf-8')}' does not use await",
                            file=str(rel_path),
                            line=node.start_point[0] + 1,
                            col=1,
                            severity=Severity.WARN,
                            engine=self.name,
                        )
                    )

            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return violations

    def _csharp_check_null(
        self, tree, file_path: Path, project_root: Path
    ) -> List[Violation]:
        """Detect potential null reference issues."""
        violations = []

        def visit(node):
            if node.type == "return_statement":
                # Check if returning null
                for child in node.children:
                    if child.type == "null_literal":
                        rel_path = file_path.relative_to(project_root)
                        violations.append(
                            Violation(
                                rule_id="csharp_null_return",
                                message="Returning null - consider using nullable types or Optional<T>",
                                file=str(rel_path),
                                line=node.start_point[0] + 1,
                                col=1,
                                severity=Severity.WARN,
                                engine=self.name,
                            )
                        )
                        break

            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return violations

    def _csharp_check_naming(
        self, tree, file_path: Path, project_root: Path
    ) -> List[Violation]:
        """Check C# naming conventions."""
        violations = []

        def visit(node):
            # Check class names (should be PascalCase)
            if node.type == "class_declaration":
                for child in node.children:
                    if child.type == "identifier":
                        name = child.text.decode("utf-8")
                        if name and name[0].islower():
                            rel_path = file_path.relative_to(project_root)
                            violations.append(
                                Violation(
                                    rule_id="csharp_class_naming",
                                    message=f"Class '{name}' should use PascalCase",
                                    file=str(rel_path),
                                    line=node.start_point[0] + 1,
                                    col=1,
                                    severity=Severity.WARN,
                                    engine=self.name,
                                )
                            )
                        break

            # Check method names (should be PascalCase)
            elif node.type == "method_declaration":
                for child in node.children:
                    if child.type == "identifier":
                        name = child.text.decode("utf-8")
                        if name and name[0].islower():
                            rel_path = file_path.relative_to(project_root)
                            violations.append(
                                Violation(
                                    rule_id="csharp_method_naming",
                                    message=f"Method '{name}' should use PascalCase",
                                    file=str(rel_path),
                                    line=node.start_point[0] + 1,
                                    col=1,
                                    severity=Severity.WARN,
                                    engine=self.name,
                                )
                            )
                        break

            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return violations

    def get_rules(self) -> list:
        """Return list of supported rules."""
        return [
            {
                "id": "rust_no_unsafe",
                "severity": "warn",
                "description": "Detect unsafe blocks",
            },
            {
                "id": "rust_function_length",
                "severity": "warn",
                "description": "Check function length",
            },
            {
                "id": "rust_pub_documentation",
                "severity": "warn",
                "description": "Check public API documentation",
            },
            {
                "id": "csharp_async_await",
                "severity": "warn",
                "description": "Detect async without await",
            },
            {
                "id": "csharp_null_return",
                "severity": "warn",
                "description": "Detect null returns",
            },
            {
                "id": "csharp_class_naming",
                "severity": "warn",
                "description": "Check class naming",
            },
            {
                "id": "csharp_method_naming",
                "severity": "warn",
                "description": "Check method naming",
            },
        ]
