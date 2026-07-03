"""import-linter engine adapter."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

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
        violations: list[Violation] = []
        # Find "Broken contracts" section
        if "Broken contracts" not in output:
            return violations

        broken_section = output.split("Broken contracts")[1]

        # import-linter reports each broken contract as a header line
        # ("module_a is not allowed to import module_b:") followed by
        # one or more indented chain lines ("- module_a.file ->
        # module_b.file (l.N)"). The chain can be longer than two
        # hops when the forbidden contract is transitive; capture
        # every hop so the user can see *why* the chain was flagged
        # without re-running lint-imports.
        current_contract: Optional[str] = None
        current_chain: list[str] = []
        for line in broken_section.split("\n"):
            stripped = line.strip()
            if "is not allowed to import" in stripped:
                # Flush previous contract first.
                if current_contract:
                    is_transitive = len(current_chain) > 1
                    for hop in current_chain:
                        violations.extend(
                            _hops_to_violations(
                                current_contract, hop, is_transitive
                            )
                        )
                current_contract = stripped
                current_chain = []
            elif stripped.startswith("-") and current_contract:
                # Each indented line after the header is one chain hop.
                current_chain.append(stripped)
        # Flush the last contract
        if current_contract:
            is_transitive = len(current_chain) > 1
            for hop in current_chain:
                violations.extend(
                    _hops_to_violations(current_contract, hop, is_transitive)
                )

        return violations


def _hops_to_violations(
    contract_header: str, hop_line: str, is_transitive: bool = False
) -> list[Violation]:
    """Convert one import-linter chain line into a Violation.

    Surfaces the full chain in the message so the user can see whether
    this is a direct or transitive violation, and where the chain
    starts in their own source.
    """
    # Strip the leading "- " (and any nested indent markers that
    # import-linter prints for multi-hop chains).
    body = hop_line.lstrip("- ").strip()
    m = re.search(r"(.+?)\s*->\s*(.+?)\s*\(l\.(\d+)\)", body)
    if not m:
        return []
    src = m.group(1).strip()
    line = int(m.group(3))
    chain_hint = (
        " (transitive chain — see full output)" if is_transitive else ""
    )
    return [
        Violation(
            rule_id="arch-forbidden-import",
            message=(
                f"Architecture violation: {contract_header}{chain_hint}. "
                f"First hop: {src} (line {line})"
            ),
            file=src,
            line=line,
            severity=Severity.ERROR,
            engine="import-linter",
            fixable=False,
        )
    ]
