"""Spec validation rules.

Built-in rules:
- structural: every spec must have stage, id, metadata
- chain_subordinate: parent must exist and be in the parent stage
- coverage: PRD requirements must be covered by biz-arch modules
- reference_integrity: every referenced ID must exist
- no_duplicate_id: each ID must be unique

Custom rules can be added via plugins in .unified-lint/rules/.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .loader import SpecNode, build_index


@dataclass
class Violation:
    rule_id: str
    severity: str  # "error" | "warning" | "info"
    message: str
    file: str
    line: Optional[int] = None

    def __str__(self) -> str:
        loc = f"{self.file}:{self.line}" if self.line else self.file
        return f"[{self.severity.upper()}] {self.rule_id} {loc}: {self.message}"


# 父级映射：合法的链式从属关系
CHAIN_PARENT_STAGE = {
    "prd": None,
    "biz-arch": "prd",
    "features": "biz-arch",
    # datamodel 是模块的局部，不需要 parent（通过 module.owns_entities 引用）
    "datamodel": None,
    "api": "features",
    "tests": "features",
    "tech-arch": "prd",  # 技术架构也从属于 PRD（业务需求驱动）
    "deployment": "tech-arch",
    "metrics": None,  # 全局
    "roles": None,  # 全局
    "decisions": None,  # 全局
    "changelog": None,  # 全局
}


# 全局文件不参与链式校验
GLOBAL_STAGES = {"metrics", "roles", "decisions", "changelog"}


def check_structural(index: dict[str, SpecNode]) -> list[Violation]:
    """Every spec must have stage, id, metadata."""
    violations: list[Violation] = []
    for node in index.values():
        if not node.stage:
            violations.append(
                Violation("structural", "error", "missing 'stage'", node.path)
            )
        if not node.id:
            violations.append(
                Violation("structural", "error", "missing 'id'", node.path)
            )
        if "metadata" not in node.data:
            violations.append(
                Violation("structural", "warning", "missing 'metadata'", node.path)
            )
    return violations


def check_no_duplicate_id(index: dict[str, SpecNode]) -> list[Violation]:
    """Each ID must be unique across the whole spec set."""
    violations: list[Violation] = []
    by_id: dict[str, list[SpecNode]] = {}
    for node in index.values():
        by_id.setdefault(node.id, []).append(node)
    for id_, nodes in by_id.items():
        if len(nodes) > 1:
            paths = ", ".join(n.path for n in nodes)
            for n in nodes:
                violations.append(
                    Violation(
                        "no_duplicate_id",
                        "error",
                        f"duplicate ID '{id_}' also in: {paths}",
                        n.path,
                    )
                )
    return violations


def check_reference_integrity(index: dict[str, SpecNode]) -> list[Violation]:
    """Every ID referenced must exist somewhere in the index."""
    violations: list[Violation] = []
    by_id = {n.id for n in index.values()}
    for node in index.values():
        for ref_id in node.refs_out:
            if ref_id not in by_id:
                violations.append(
                    Violation(
                        "reference_integrity",
                        "error",
                        f"references unknown ID '{ref_id}'",
                        node.path,
                    )
                )
    return violations


def check_chain_subordinate(index: dict[str, SpecNode]) -> list[Violation]:
    """Parent must exist and be in the correct parent stage.

    Chain: api -> features -> biz-arch -> prd
           deployment -> tech-arch -> prd
    """
    violations: list[Violation] = []
    by_id = {n.id: n for n in index.values()}
    for node in index.values():
        if node.stage in GLOBAL_STAGES or node.stage == "datamodel":
            continue
        if not node.parent:
            violations.append(
                Violation(
                    "chain_subordinate",
                    "warning",
                    f"stage '{node.stage}' should have 'parent'",
                    node.path,
                )
            )
            continue
        parent_node = by_id.get(node.parent)
        if parent_node is None:
            violations.append(
                Violation(
                    "chain_subordinate",
                    "error",
                    f"parent '{node.parent}' not found",
                    node.path,
                )
            )
            continue
        expected_parent_stage = CHAIN_PARENT_STAGE.get(node.stage)
        if expected_parent_stage and parent_node.stage != expected_parent_stage:
            violations.append(
                Violation(
                    "chain_subordinate",
                    "error",
                    f"parent '{node.parent}' has stage '{parent_node.stage}', "
                    f"expected '{expected_parent_stage}'",
                    node.path,
                )
            )
    return violations


def check_prd_coverage(index: dict[str, SpecNode]) -> list[Violation]:
    """Every PRD requirement should be covered by a biz-arch module."""
    violations: list[Violation] = []
    req_ids: set[str] = {n.id for n in index.values() if n.stage == "prd"}
    covered: set[str] = set()
    for node in index.values():
        if node.stage in ("biz-arch", "features", "api", "tests"):
            for ref in node.refs_out:
                if ref in req_ids:
                    covered.add(ref)
    for req_id in sorted(req_ids - covered):
        violations.append(
            Violation(
                "prd_coverage",
                "error",
                f"requirement {req_id} is not covered by any biz-arch/features/api/tests",
                "prd/prd.yaml",
            )
        )
    return violations


def check_api_implemented(index: dict[str, SpecNode]) -> list[Violation]:
    """Every API endpoint should be covered by a feature (covers_requirement)."""
    violations: list[Violation] = []
    feat_ids = {n.id for n in index.values() if n.stage == "features"}
    for node in index.values():
        if node.stage != "api":
            continue
        if node.parent not in feat_ids:
            violations.append(
                Violation(
                    "api_implemented",
                    "error",
                    f"API {node.id} parent '{node.parent}' is not a known feature",
                    node.path,
                )
            )
    return violations


# All built-in rules
BUILTIN_RULES = {
    "structural": check_structural,
    "no_duplicate_id": check_no_duplicate_id,
    "reference_integrity": check_reference_integrity,
    "chain_subordinate": check_chain_subordinate,
    "prd_coverage": check_prd_coverage,
    "api_implemented": check_api_implemented,
}


def run_all(
    index: dict[str, SpecNode], rule_ids: Optional[list[str]] = None
) -> list[Violation]:
    """Run the selected rules (or all built-in if None)."""
    rules = rule_ids or list(BUILTIN_RULES.keys())
    violations: list[Violation] = []
    for rid in rules:
        if rid in BUILTIN_RULES:
            violations.extend(BUILTIN_RULES[rid](index))
    return violations
