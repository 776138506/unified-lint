"""import-linter engine adapter."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from .base import EngineResult, LintEngine, Severity, Violation


class ImportLinterEngine(LintEngine):
    name = "import-linter"

    def is_available(self) -> bool:
        return shutil.which("lint-imports") is not None

    def check(self, project_root: Path, config: dict) -> EngineResult:
        result = EngineResult(engine_name=self.name)

        if not self.is_available():
            result.error = "import-linter not installed (pip install import-linter)"
            return result

        importlinter_file = project_root / ".importlinter"
        if not importlinter_file.exists():
            # Try to generate from arch.toml
            arch_toml = project_root / ".unified-lint" / "arch.toml"
            if arch_toml.exists():
                self._generate_importlinter(project_root, arch_toml)
            else:
                result.error = "No .importlinter or .unified-lint/arch.toml found"
                return result

        try:
            proc = subprocess.run(
                ["lint-imports"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(project_root),
            )
            output = proc.stdout + proc.stderr
            result.violations = self._parse_output(output)
        except subprocess.TimeoutExpired:
            result.error = "lint-imports timed out"
        except Exception as e:
            result.error = f"lint-imports failed: {e}"

        return result

    def _generate_importlinter(self, project_root: Path, arch_toml: Path):
        """Convert arch.toml to .importlinter format."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        with open(arch_toml, "rb") as f:
            arch = tomllib.load(f)

        lines = ["[importlinter]"]
        root_pkg = arch.get("root_package", "myapp")
        lines.append(f"root_package = {root_pkg}")
        lines.append("include_external_packages = False")
        lines.append("")

        # Layers contract
        layers = arch.get("layers", {}).get("order", [])
        if layers:
            lines.append("[importlinter:contract:layers]")
            lines.append("name = Layer dependency rules")
            lines.append("type = layers")
            lines.append("layers =")
            for layer in layers:
                lines.append(f"    {root_pkg}.{layer}")
            lines.append("")

        # Forbidden contracts
        for i, forbidden in enumerate(arch.get("contracts", {}).get("forbidden", [])):
            lines.append(f"[importlinter:contract:forbidden_{i}]")
            lines.append(
                f"name = Forbidden: {forbidden.get('from', '?')} -> {forbidden.get('to', '?')}"
            )
            lines.append("type = forbidden")
            lines.append(f"source_modules = {root_pkg}.{forbidden['from']}")
            lines.append(f"forbidden_modules = {root_pkg}.{forbidden['to']}")
            lines.append("")

        output_path = project_root / ".importlinter"
        output_path.write_text("\n".join(lines), encoding="utf-8")

    def _parse_output(self, output: str) -> list[Violation]:
        violations = []
        # Find "Broken contracts" section
        if "Broken contracts" not in output:
            return violations

        broken_section = output.split("Broken contracts")[1]

        # Parse: "module_a is not allowed to import module_b:"
        # followed by "- module_a.file -> module_b.file (l.N)"
        current_contract = None
        for line in broken_section.split("\n"):
            line = line.strip()
            if "is not allowed to import" in line:
                current_contract = line
            elif line.startswith("-") and current_contract:
                # Parse: - module_a.file -> module_b.file (l.N)
                m = re.search(r"(.+?)\s*->\s*(.+?)\s*\(l\.(\d+)\)", line)
                if m:
                    violations.append(
                        Violation(
                            rule_id="arch-forbidden-import",
                            message=f"Architecture violation: {current_contract}",
                            file=m.group(1),
                            line=int(m.group(3)),
                            severity=Severity.ERROR,
                            engine=self.name,
                            fixable=False,
                        )
                    )

        return violations
