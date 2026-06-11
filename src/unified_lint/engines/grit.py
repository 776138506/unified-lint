"""Grit CLI engine adapter."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .base import EngineResult, LintEngine, Severity, Violation


class GritEngine(LintEngine):
    """Wraps the Grit CLI for code and doc linting."""

    name = "grit"

    def __init__(self):
        self._bin: Optional[str] = None

    def _find_bin(self) -> str:
        """Locate the grit binary."""
        if self._bin:
            return self._bin
        # Check local grit.exe first, then PATH
        local = Path("grit.exe")
        if local.exists():
            self._bin = str(local.resolve())
            return self._bin
        found = shutil.which("grit") or shutil.which("grit.exe")
        if found:
            self._bin = found
            return self._bin
        raise FileNotFoundError("grit CLI not found in PATH or local directory")

    def is_available(self) -> bool:
        """Check if grit is installed."""
        try:
            self._find_bin()
            return True
        except FileNotFoundError:
            return False

    def check(self, project_root: Path, config: dict) -> EngineResult:
        """Run grit check and parse output."""
        result = EngineResult(engine_name=self.name)
        try:
            bin_path = self._find_bin()
        except FileNotFoundError as e:
            result.error = str(e)
            return result

        paths = config.get("grit_paths", ["."])
        cmd = [bin_path, "check", "--level", "info"]
        cmd.extend(str(project_root / p) for p in paths)

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60, cwd=str(project_root)
            )
            output = proc.stdout + proc.stderr
            result.violations = self._parse_output(output)
        except subprocess.TimeoutExpired:
            result.error = "grit check timed out"
        except Exception as e:
            result.error = f"grit check failed: {e}"

        return result

    def fix(self, project_root: Path, config: dict) -> EngineResult:
        """Run grit check --fix, then re-check."""
        result = EngineResult(engine_name=self.name)
        try:
            bin_path = self._find_bin()
        except FileNotFoundError as e:
            result.error = str(e)
            return result

        paths = config.get("grit_paths", ["."])
        cmd = [bin_path, "check", "--fix", "--level", "info"]
        cmd.extend(str(project_root / p) for p in paths)

        try:
            subprocess.run(
                cmd, capture_output=True, text=True, timeout=60, cwd=str(project_root)
            )
            # Re-check after fix
            return self.check(project_root, config)
        except Exception as e:
            result.error = f"grit fix failed: {e}"
            return result

    def _parse_output(self, output: str) -> list[Violation]:
        """Parse grit check output into Violation objects."""
        violations = []
        if "No results found" in output:
            return violations

        # Output format:
        #   file_path
        #     line:col  match  message  rule_id
        current_file = None
        for line in output.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            # Skip PATTERNS header
            if (
                stripped == "PATTERNS"
                or stripped.startswith("✗")
                or stripped.startswith("✓")
            ):
                continue
            # Skip "N files with rewrites" line
            if "files with rewrites" in stripped or "Run grit" in stripped:
                continue
            # File path line (no leading digits:)
            if not re.match(r"^\d+:\d+", stripped) and (
                "/" in stripped or "\\" in stripped
            ):
                current_file = stripped
                continue
            # Match line: "line:col  match  message  rule_id"
            m = re.match(r"(\d+):(\d+)\s+match\s+(.+?)\s+(\w+)\s*$", stripped)
            if m and current_file:
                violations.append(
                    Violation(
                        rule_id=m.group(4),
                        message=m.group(3).strip(),
                        file=current_file,
                        line=int(m.group(1)),
                        col=int(m.group(2)),
                        severity=Severity.WARN,
                        engine=self.name,
                        fixable=True,
                    )
                )

        return violations
