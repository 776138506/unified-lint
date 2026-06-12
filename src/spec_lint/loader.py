"""Spec loader: scan all YAML files in specs/ directory."""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import yaml


@dataclass
class SpecNode:
    """A single spec file in the index."""

    path: str
    stage: str
    id: str
    parent: str | None
    data: dict
    refs_out: set[str] = field(default_factory=set)
    refs_in: set[str] = field(default_factory=set)

    @property
    def name(self) -> str:
        return self.data.get("name", self.id)


_SKIP_FILENAMES = {"_index.yaml"}
_SKIP_DIRS = {"__pycache__"}

ID_PREFIXES = (
    "REQ-",
    "FEAT-",
    "EP-",
    "ADR-",
    "BR-",
    "FP-",
    "UT-",
    "IT-",
    "E2E-",
    "AuthService",
    "OrderService",
    "ExportService",
    "api-gateway",
    "auth-service",
    "order-service",
    "export-service",
    "User",
    "Order",
    "ExportJob",
    "Session",
    "prd-v1",
    "biz-arch-v1",
    "tech-arch-v1",
    "metrics-v1",
    "roles-v1",
    "decisions-v1",
    "changelog-v1",
    "api-v1",
)

REF_FIELDS = {
    "parent",
    "requirement",
    "covers_requirement",
    "covers_biz_arch",
    "covers_tech_arch",
    "covers_biz_module",
    "covers_metrics",
    "covers_api",
}
LIST_REF_FIELDS = {
    "covers_requirements",
    "covers_features",
    "endpoints",
    "depends_on",
}


def _looks_like_id(s: str) -> bool:
    if not isinstance(s, str):
        return False
    return any(s == p or s.startswith(p) for p in ID_PREFIXES)


def _extract_refs(data: Any) -> set[str]:
    refs: set[str] = set()

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in REF_FIELDS and isinstance(v, str):
                    refs.add(v)
                elif k in LIST_REF_FIELDS and isinstance(v, list):
                    for item in v:
                        if isinstance(item, str):
                            refs.add(item)
                        elif isinstance(item, dict):
                            walk(item)
                else:
                    walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)
        elif isinstance(obj, str) and _looks_like_id(obj):
            refs.add(obj)

    walk(data)
    return refs


def _walk_specs(specs_dir: Path) -> Iterator[Path]:
    for root, dirs, files in os.walk(specs_dir):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for f in sorted(files):
            if f.endswith((".yaml", ".yml")) and f not in _SKIP_FILENAMES:
                yield Path(root) / f


def build_index(specs_dir: str | Path) -> dict[str, SpecNode]:
    """Build a complete index of all specs under specs_dir."""
    specs_dir = Path(specs_dir)
    index: dict[str, SpecNode] = {}
    for path in _walk_specs(specs_dir):
        rel = path.relative_to(specs_dir).as_posix()
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict) or "id" not in data or "stage" not in data:
            continue
        node = SpecNode(
            path=rel,
            stage=data.get("stage", ""),
            id=data.get("id", ""),
            parent=data.get("parent"),
            data=data,
            refs_out=_extract_refs(data),
        )
        index[rel] = node

    by_id: dict[str, SpecNode] = {n.id: n for n in index.values()}
    for node in index.values():
        for ref_id in node.refs_out:
            target = by_id.get(ref_id)
            if target is not None:
                target.refs_in.add(node.id)
    return index


def get_topology(index: dict[str, SpecNode]) -> dict[str, list[SpecNode]]:
    grouped: dict[str, list[SpecNode]] = defaultdict(list)
    for node in index.values():
        grouped[node.stage].append(node)
    for stage in grouped:
        grouped[stage].sort(key=lambda n: n.id)
    return dict(grouped)


def render_index_yaml(index: dict[str, SpecNode]) -> str:
    """Render the _index.yaml file with stats and topology."""
    topology = get_topology(index)
    by_id_count: dict[str, int] = defaultdict(int)
    for n in index.values():
        by_id_count[n.id] += 1

    lines = [
        "# Auto-generated index of all specs",
        "# DO NOT EDIT - run: spec-cli index",
        "",
        'generated: "2026-06-12"',
        f"total_files: {len(index)}",
        f"total_ids: {len(set(n.id for n in index.values()))}",
        f"duplicate_ids:",
    ]
    for k, v in sorted(by_id_count.items()):
        if v > 1:
            lines.append(f"  - id: {k}")
            lines.append(f"    count: {v}")
    if not any(v > 1 for v in by_id_count.values()):
        lines.append("  []")

    lines += ["", "# 链式从属结构", "topology:"]
    for stage in (
        "prd",
        "biz-arch",
        "features",
        "datamodel",
        "api",
        "tests",
        "tech-arch",
        "deployment",
        "metrics",
        "roles",
        "decisions",
        "changelog",
    ):
        nodes = topology.get(stage, [])
        if not nodes:
            continue
        lines.append(f"  {stage}:")
        for n in nodes:
            parent_note = f" <- {n.parent}" if n.parent else ""
            lines.append(f"    - id: {n.id}")
            lines.append(f"      path: {n.path}{parent_note}")
            lines.append(f"      refs_out: {sorted(n.refs_out)}")
            lines.append(f"      refs_in_count: {len(n.refs_in)}")
    return "\n".join(lines) + "\n"
