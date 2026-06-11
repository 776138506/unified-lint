"""Project initializer: detect language, install deps, generate config."""

from __future__ import annotations

import platform
import shutil
import subprocess
import urllib.request
from pathlib import Path

from rich.console import Console

console = Console()


def detect_language(project_root: Path) -> str:
    """Detect primary project language."""
    if (project_root / "pyproject.toml").exists() or (
        project_root / "setup.py"
    ).exists():
        return "python"
    if (project_root / "package.json").exists():
        return "javascript"
    if (project_root / "go.mod").exists():
        return "go"
    if (project_root / "Cargo.toml").exists():
        return "rust"
    return "python"  # default


def ensure_grit(project_root: Path) -> bool:
    """Ensure grit CLI is available."""
    if shutil.which("grit") or shutil.which("grit.exe"):
        return True
    local = project_root / "grit.exe"
    if local.exists():
        return True

    console.print("[yellow]grit CLI not found, downloading...[/yellow]")
    try:
        system = platform.system().lower()
        arch = "x86_64" if platform.machine() in ("AMD64", "x86_64") else "aarch64"
        if system == "windows":
            url = f"https://github.com/biomejs/gritql/releases/download/v0.1.0-alpha.1743007075/grit-{arch}-pc-windows-msvc.tar.gz"
        elif system == "linux":
            url = f"https://github.com/biomejs/gritql/releases/download/v0.1.0-alpha.1743007075/grit-{arch}-unknown-linux-gnu.tar.gz"
        elif system == "darwin":
            url = f"https://github.com/biomejs/gritql/releases/download/v0.1.0-alpha.1743007075/grit-{arch}-apple-darwin.tar.gz"
        else:
            console.print("[red]Unsupported platform[/red]")
            return False

        tarball = project_root / "grit.tar.gz"
        urllib.request.urlretrieve(url, str(tarball))
        subprocess.run(["tar", "xzf", str(tarball)], cwd=str(project_root), check=True)
        # Find the extracted binary
        for p in project_root.glob("grit-*"):
            if p.is_dir():
                exe = p / "grit.exe" if system == "windows" else p / "grit"
                if exe.exists():
                    shutil.move(
                        str(exe),
                        str(
                            project_root
                            / ("grit.exe" if system == "windows" else "grit")
                        ),
                    )
                    break
        tarball.unlink(missing_ok=True)
        console.print("[green]grit CLI installed[/green]")
        return True
    except Exception as e:
        console.print(f"[red]Failed to install grit: {e}[/red]")
        return False


def ensure_import_linter() -> bool:
    """Ensure import-linter is available."""
    if shutil.which("lint-imports"):
        return True
    console.print("[yellow]import-linter not found, installing...[/yellow]")
    try:
        subprocess.run(["pip", "install", "import-linter", "--quiet"], check=True)
        console.print("[green]import-linter installed[/green]")
        return True
    except Exception as e:
        console.print(f"[red]Failed to install import-linter: {e}[/red]")
        return False


def generate_config(project_root: Path, root_package: str, language: str):
    """Generate .unified-lint/config.toml."""
    config_dir = project_root / ".unified-lint"
    config_dir.mkdir(exist_ok=True)

    config_content = f"""# unified-lint configuration
language = "{language}"
root_package = "{root_package}"

[code]
enabled = true
paths = ["."]

[docs]
enabled = true
paths = ["docs"]

[layers]
enabled = true
"""
    (config_dir / "config.toml").write_text(config_content, encoding="utf-8")

    # Generate arch.toml for Python projects
    if language == "python":
        arch_content = f"""# Architecture rules
root_package = "{root_package}"

[layers]
order = ["api", "infra", "service", "domain"]

[[contracts.forbidden]]
from = "infra"
to = "domain"
"""
        (config_dir / "arch.toml").write_text(arch_content, encoding="utf-8")


def copy_builtin_rules(project_root: Path):
    """Copy builtin GritQL rules to .grit/patterns/."""
    patterns_dir = project_root / ".grit" / "patterns"
    patterns_dir.mkdir(parents=True, exist_ok=True)

    # Get builtin rules from package
    from .rules.registry import get_builtin_rules

    for rule in get_builtin_rules():
        target = patterns_dir / f"{rule['id']}.md"
        if not target.exists():
            target.write_text(rule["content"], encoding="utf-8")


def run_init(project_root: Path, root_package: str = "myapp"):
    """Full init flow."""
    console.print(f"[bold]Initializing unified-lint in {project_root}[/bold]\n")

    language = detect_language(project_root)
    console.print(f"  Detected language: [cyan]{language}[/cyan]")

    # Install dependencies
    console.print("\n[bold]Checking dependencies...[/bold]")
    ensure_grit(project_root)
    ensure_import_linter()

    # Generate config
    console.print("\n[bold]Generating configuration...[/bold]")
    generate_config(project_root, root_package, language)
    console.print("  [green]Created .unified-lint/config.toml[/green]")
    if language == "python":
        console.print("  [green]Created .unified-lint/arch.toml[/green]")

    # Copy builtin rules
    console.print("\n[bold]Installing builtin rules...[/bold]")
    copy_builtin_rules(project_root)
    console.print("  [green]Copied GritQL patterns to .grit/patterns/[/green]")

    console.print("\n[bold green]Done![/bold green]")
    console.print("  Run: [cyan]unified-lint check[/cyan]")
