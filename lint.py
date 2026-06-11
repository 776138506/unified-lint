#!/usr/bin/env python3
"""
Unified Lint - 统一 Linter 入口
组合三层检查：GritQL 自定义规则 + import-linter 架构规则

用法：
    python lint.py              # 跑全部检查
    python lint.py --code       # 只跑 GritQL 代码规则
    python lint.py --docs       # 只跑 GritQL 文档规则
    python lint.py --arch       # 只跑 import-linter 架构规则
    python lint.py --fix        # 自动修复可修复的问题
"""

import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent
GRIT_BIN = str(ROOT / "grit.exe") if (ROOT / "grit.exe").exists() else "grit"


def section(title: str, num: str):
    print(f"\n[{num}] {title}")
    print("-" * 50)


def run_grit(paths: list[str], label: str, fix: bool = False) -> tuple[int, str]:
    """运行 GritQL 规则"""
    cmd = [GRIT_BIN, "check", "--level", "info"]
    if fix:
        cmd.append("--fix")
    cmd.extend(paths)

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, cwd=str(ROOT)
        )
        output = (result.stdout + result.stderr).strip()
        if not output or "No results found" in output:
            return 0, f"  {label}: OK - 无违规"
        # Count matches
        count = output.count("match")
        return max(1, count), output
    except FileNotFoundError:
        return -1, f"  {label}: grit CLI 未安装"
    except subprocess.TimeoutExpired:
        return 1, f"  {label}: 超时"


def run_import_linter() -> tuple[int, str]:
    """运行 import-linter 架构规则"""
    try:
        result = subprocess.run(
            ["lint-imports"], capture_output=True, text=True, timeout=30, cwd=str(ROOT)
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode == 0:
            return 0, "  架构规则: OK - 所有依赖契约通过"
        # Count broken contracts
        count = output.count("BROKEN")
        return max(1, count), output
    except FileNotFoundError:
        return -1, "  架构规则: import-linter 未安装 (pip install import-linter)"
    except subprocess.TimeoutExpired:
        return 1, "  架构规则: 超时"


def main():
    args = sys.argv[1:]
    fix = "--fix" in args
    run_all = not any(a.startswith("--") for a in args if a != "--fix")
    run_code = run_all or "--code" in args
    run_docs = run_all or "--docs" in args
    run_arch = run_all or "--arch" in args

    print("=" * 60)
    print("  Unified Lint - 统一 Linter")
    print("  GritQL (代码+文档) + import-linter (架构)")
    print("=" * 60)

    total_issues = 0
    has_error = False

    # 1. 代码规则 (GritQL)
    if run_code:
        section("代码规则 (GritQL)", "1/3")
        issues, output = run_grit(["myapp/"], "代码规则", fix)
        print(output)
        if issues > 0:
            total_issues += issues
        elif issues < 0:
            has_error = True

    # 2. 文档规则 (GritQL)
    if run_docs:
        section("文档规则 (GritQL)", "2/3")
        issues, output = run_grit(["docs/"], "文档规则", fix)
        print(output)
        if issues > 0:
            total_issues += issues
        elif issues < 0:
            has_error = True

    # 3. 架构规则 (import-linter)
    if run_arch:
        section("架构规则 (import-linter)", "3/3")
        issues, output = run_import_linter()
        print(output)
        if issues > 0:
            total_issues += issues
        elif issues < 0:
            has_error = True

    # 总结
    print("\n" + "=" * 60)
    if has_error and total_issues == 0:
        print("  !! 工具缺失，请安装依赖后重试")
        sys.exit(2)
    elif total_issues == 0:
        print("  ALL PASS - 全部检查通过")
        sys.exit(0)
    else:
        print(f"  FAILED - 发现 {total_issues} 个问题")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
