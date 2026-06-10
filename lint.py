#!/usr/bin/env python3
"""
Unified Lint - 统一 Linter 入口
组合三层检查：GritQL 自定义规则 + import-linter 架构规则 + 元规则

用法：
    python lint.py              # 跑全部检查
    python lint.py --code       # 只跑代码规则
    python lint.py --docs       # 只跑文档规则
    python lint.py --arch       # 只跑架构规则
    python lint.py --fix        # 自动修复可修复的问题
"""

import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent
LINT_CONFIG = ROOT / ".lint-config"
CODE_RULES = LINT_CONFIG / "code-rules"
DOC_RULES = LINT_CONFIG / "doc-rules"


def run_grit(rules_dir: Path, label: str, fix: bool = False) -> tuple[int, list[str]]:
    """运行 GritQL 规则"""
    if not rules_dir.exists():
        return 0, [f"  {label}: 无规则目录，跳过"]

    grit_files = list(rules_dir.glob("*.grit"))
    if not grit_files:
        return 0, [f"  {label}: 无 .grit 文件，跳过"]

    total_issues = 0
    messages = []

    for grit_file in grit_files:
        cmd = ["grit", "check", "--config-path", str(grit_file), str(ROOT)]
        if fix:
            cmd = ["grit", "apply", str(grit_file), str(ROOT)]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            output = result.stdout + result.stderr
            if output.strip():
                # 统计 issue 数量（粗略）
                issues = (
                    output.count("diagnostic")
                    + output.count("warning")
                    + output.count("error")
                )
                total_issues += max(1, issues) if result.returncode != 0 else 0
                messages.append(f"  [{grit_file.stem}]\n{output}")
            else:
                messages.append(f"  [{grit_file.stem}] ✓ 通过")
        except FileNotFoundError:
            messages.append(f"  [{grit_file.stem}] ✗ grit CLI 未安装")
            return -1, messages
        except subprocess.TimeoutExpired:
            messages.append(f"  [{grit_file.stem}] ✗ 超时")
            total_issues += 1

    return total_issues, messages


def run_import_linter() -> tuple[int, list[str]]:
    """运行 import-linter 架构规则"""
    cmd = ["lint-imports"]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, cwd=str(ROOT)
        )
        output = result.stdout + result.stderr
        if result.returncode == 0:
            return 0, ["  分层架构: ✓ 所有依赖规则通过"]
        else:
            issues = output.count("broken contract") + output.count("Error")
            return max(1, issues), [f"  分层架构: ✗ 违规\n{output}"]
    except FileNotFoundError:
        return -1, ["  分层架构: ✗ import-linter 未安装 (pip install import-linter)"]
    except subprocess.TimeoutExpired:
        return 1, ["  分层架构: ✗ 超时"]


def main():
    args = sys.argv[1:]
    fix = "--fix" in args
    run_all = not any(a.startswith("--") for a in args) or "--all" in args
    run_code = run_all or "--code" in args
    run_docs = run_all or "--docs" in args
    run_arch = run_all or "--arch" in args

    print("=" * 60)
    print("  Unified Lint - 统一 Linter")
    print("=" * 60)
    print()

    total_issues = 0
    all_messages = []

    # 1. 代码规则 (GritQL)
    if run_code:
        print("[1/3] 代码规则 (GritQL)")
        issues, messages = run_grit(CODE_RULES, "代码", fix)
        total_issues += max(0, issues)
        all_messages.extend(messages)
        for m in messages:
            print(m)
        print()

    # 2. 文档规则 (GritQL)
    if run_docs:
        print("[2/3] 文档规则 (GritQL)")
        issues, messages = run_grit(DOC_RULES, "文档", fix)
        total_issues += max(0, issues)
        all_messages.extend(messages)
        for m in messages:
            print(m)
        print()

    # 3. 架构规则 (import-linter)
    if run_arch:
        print("[3/3] 架构规则 (import-linter)")
        issues, messages = run_import_linter()
        total_issues += max(0, issues)
        all_messages.extend(messages)
        for m in messages:
            print(m)
        print()

    # 总结
    print("=" * 60)
    if total_issues == 0:
        print("  ✓ 全部通过")
    elif total_issues < 0:
        print("  ⚠ 工具未安装，请先安装依赖")
    else:
        print(f"  ✗ 发现 {total_issues} 个问题")
    print("=" * 60)

    sys.exit(1 if total_issues > 0 else 0)


if __name__ == "__main__":
    main()
