"""spec-cli command line tool.

Commands:
- spec-cli index    Regenerate _index.yaml
- spec-cli validate  Run built-in + custom rules
- spec-cli graph     Print ID reference graph
- spec-cli stats     Print index statistics
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

from .loader import build_index, render_index_yaml
from .validator import BUILTIN_RULES, Violation, run_all


def cmd_index(args, specs_dir: Path) -> int:
    """Regenerate _index.yaml."""
    index = build_index(specs_dir)
    out = specs_dir / "_index.yaml"
    out.write_text(render_index_yaml(index), encoding="utf-8")
    print(f"Wrote {out} ({len(index)} files indexed)")
    return 0


def _load_plugin_rules(specs_dir: Path) -> dict:
    """Load custom rules from .unified-lint/rules/*.py under specs_dir."""
    from .plugin_loader import discover_plugins

    return discover_plugins(specs_dir)


def cmd_validate(args, specs_dir: Path) -> int:
    """Run validation rules and print results."""
    index = build_index(specs_dir)
    print(f"Indexed {len(index)} specs")

    # Built-in
    rule_ids = args.rules if args.rules else None
    violations = run_all(index, rule_ids)

    # Plugins
    plugins = _load_plugin_rules(specs_dir)
    for rid, fn in plugins.items():
        if rule_ids and rid not in rule_ids:
            continue
        try:
            violations.extend(fn(index, specs_dir))
        except Exception as e:
            print(f"  warn: plugin {rid} failed: {e}", file=sys.stderr)

    # Print
    if not violations:
        print("\n[PASS] No violations")
        return 0
    errors = [v for v in violations if v.severity == "error"]
    warnings = [v for v in violations if v.severity == "warning"]
    print(f"\n{len(errors)} errors, {len(warnings)} warnings")
    for v in violations:
        print(f"  {v}")
    return 1 if errors else 0


def cmd_stats(args, specs_dir: Path) -> int:
    """Print index statistics."""
    index = build_index(specs_dir)
    from collections import Counter

    stages = Counter(n.stage for n in index.values())
    print(f"Total files: {len(index)}")
    print(f"Unique IDs:  {len(set(n.id for n in index.values()))}")
    print(f"\nBy stage:")
    for stage, count in stages.most_common():
        print(f"  {stage:12} {count:3d}")
    # Orphan check
    orphans = [
        n
        for n in index.values()
        if n.stage
        not in (
            "prd",
            "metrics",
            "roles",
            "decisions",
            "changelog",
            "biz-arch",
            "tech-arch",
        )
        and not n.parent
    ]
    if orphans:
        print(f"\n{len(orphans)} orphan nodes (no parent):")
        for n in orphans:
            print(f"  {n.id} ({n.stage}) in {n.path}")
    return 0


def cmd_graph(args, specs_dir: Path) -> int:
    """Print ID reference graph for a specific node."""
    index = build_index(specs_dir)
    by_id = {n.id: n for n in index.values()}
    if args.id:
        node = by_id.get(args.id)
        if not node:
            print(f"ID '{args.id}' not found")
            return 1
        print(f"\n=== {args.id} ===")
        print(f"  path: {node.path}")
        print(f"  stage: {node.stage}")
        if node.parent:
            print(f"  parent: {node.parent}")
        print(f"  references out: {sorted(node.refs_out)}")
        print(f"  referenced by:   {sorted(node.refs_in)}")
    else:
        # Print full graph summary
        print(f"\n=== Reference graph ({len(index)} nodes) ===")
        for node in sorted(index.values(), key=lambda n: (n.stage, n.id)):
            if node.refs_out:
                print(f"  [{node.stage:8}] {node.id:12} -> {sorted(node.refs_out)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spec-cli", description="YAML 规范校验工具")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_idx = sub.add_parser("index", help="重新生成 _index.yaml")
    p_idx.add_argument("--specs-dir", default="specs", help="specs 目录路径")
    p_idx.set_defaults(func=cmd_index)

    p_val = sub.add_parser("validate", help="运行校验规则")
    p_val.add_argument("--specs-dir", default="specs", help="specs 目录路径")
    p_val.add_argument("--rules", nargs="*", help="指定运行的规则（默认全部）")
    p_val.set_defaults(func=cmd_validate)

    p_stats = sub.add_parser("stats", help="打印索引统计")
    p_stats.add_argument("--specs-dir", default="specs", help="specs 目录路径")
    p_stats.set_defaults(func=cmd_stats)

    p_graph = sub.add_parser("graph", help="打印引用图")
    p_graph.add_argument("--specs-dir", default="specs", help="specs 目录路径")
    p_graph.add_argument("--id", help="只看指定 ID 的引用")
    p_graph.set_defaults(func=cmd_graph)

    args = parser.parse_args(argv)
    specs_dir = Path(args.specs_dir)
    if not specs_dir.exists():
        print(f"specs directory not found: {specs_dir}", file=sys.stderr)
        return 1
    return args.func(args, specs_dir)


if __name__ == "__main__":
    sys.exit(main())
