"""Markdown AST engine: uses markdown-it-py for precise documentation analysis.

This engine handles rules that GritQL's Alpha Markdown parser cannot,
such as frontmatter field validation, broken links, heading structure,
code block language tags, and image alt text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import yaml
from markdown_it import MarkdownIt

from .base import EngineResult, LintEngine, Severity, Violation


# Rule function signature: takes file path + tokens, returns violations
RuleFn = Callable[[Path, list[dict]], list[Violation]]

_REGISTRY: dict[str, tuple[RuleFn, Severity, str]] = {}


def rule(rule_id: str, severity: Severity, description: str):
    """Decorator to register a Markdown AST rule."""

    def decorator(fn: RuleFn):
        _REGISTRY[rule_id] = (fn, severity, description)
        return fn

    return decorator


# ── Rules ─────────────────────────────────────────────────────


@rule(
    "doc_frontmatter_fields",
    Severity.ERROR,
    "Frontmatter must have required fields (last_updated)",
)
def check_frontmatter_fields(path: Path, tokens: list[dict]) -> list[Violation]:
    """Check that frontmatter has required fields."""
    violations = []
    required_fields = {"last_updated"}

    # Parse frontmatter
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return violations

    end = content.find("---", 3)
    if end == -1:
        return violations

    frontmatter_text = content[3:end].strip()
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError:
        violations.append(
            Violation(
                rule_id="doc_frontmatter_fields",
                message="Invalid YAML in frontmatter",
                file=str(path),
                line=1,
                col=1,
                severity=Severity.ERROR,
                engine="markdown-ast",
                fixable=False,
            )
        )
        return violations

    if not isinstance(frontmatter, dict):
        violations.append(
            Violation(
                rule_id="doc_frontmatter_fields",
                message="Frontmatter must be a YAML mapping",
                file=str(path),
                line=1,
                col=1,
                severity=Severity.ERROR,
                engine="markdown-ast",
                fixable=False,
            )
        )
        return violations

    # Check required fields
    missing = required_fields - set(frontmatter.keys())
    if missing:
        violations.append(
            Violation(
                rule_id="doc_frontmatter_fields",
                message=f"Missing required frontmatter fields: {', '.join(sorted(missing))}",
                file=str(path),
                line=1,
                col=1,
                severity=Severity.ERROR,
                engine="markdown-ast",
                fixable=False,
            )
        )

    return violations


@rule(
    "doc_broken_links",
    Severity.ERROR,
    "Internal links must point to existing files",
)
def check_broken_links(path: Path, tokens: list[dict]) -> list[Violation]:
    """Check that internal links point to existing files."""
    violations = []
    base_dir = path.parent

    for token in tokens:
        if token["type"] != "link_open":
            continue

        href = token.get("attrs", {}).get("href", "")
        # Skip external links
        if href.startswith(("http://", "https://", "mailto:", "#")):
            continue

        # Remove anchor
        file_path = href.split("#")[0]
        if not file_path:
            continue

        # Check if file exists
        target = base_dir / file_path
        if not target.exists():
            violations.append(
                Violation(
                    rule_id="doc_broken_links",
                    message=f"Broken link: {href} (file not found)",
                    file=str(path),
                    line=token.get("line", 1),
                    col=1,
                    severity=Severity.ERROR,
                    engine="markdown-ast",
                    fixable=False,
                )
            )

    return violations


@rule(
    "doc_heading_structure",
    Severity.WARN,
    "Heading levels must not skip (e.g., h1 → h3)",
)
def check_heading_structure(path: Path, tokens: list[dict]) -> list[Violation]:
    """Check that heading levels don't skip."""
    violations = []
    prev_level = 0

    for token in tokens:
        if token["type"] != "heading_open":
            continue

        level = int(token["tag"][1])  # h1 -> 1, h2 -> 2, etc.

        if prev_level > 0 and level > prev_level + 1:
            violations.append(
                Violation(
                    rule_id="doc_heading_structure",
                    message=f"Heading level h{level} skips h{prev_level + 1} (previous was h{prev_level})",
                    file=str(path),
                    line=token.get("line", 1),
                    col=1,
                    severity=Severity.WARN,
                    engine="markdown-ast",
                    fixable=False,
                )
            )

        prev_level = level

    return violations


@rule(
    "doc_code_block_lang",
    Severity.WARN,
    "Code blocks should specify a language",
)
def check_code_block_lang(path: Path, tokens: list[dict]) -> list[Violation]:
    """Check that code blocks have language tags."""
    violations = []

    for token in tokens:
        if token["type"] != "fence":
            continue

        lang = token.get("info", "").strip()
        if not lang:
            violations.append(
                Violation(
                    rule_id="doc_code_block_lang",
                    message="Code block missing language tag (use ```language)",
                    file=str(path),
                    line=token.get("line", 1),
                    col=1,
                    severity=Severity.WARN,
                    engine="markdown-ast",
                    fixable=False,
                )
            )

    return violations


@rule(
    "doc_image_alt",
    Severity.WARN,
    "Images should have alt text",
)
def check_image_alt(path: Path, tokens: list[dict]) -> list[Violation]:
    """Check that images have alt text."""
    violations = []

    for token in tokens:
        if token["type"] != "image":
            continue

        alt = token.get("content", "").strip()
        if not alt:
            violations.append(
                Violation(
                    rule_id="doc_image_alt",
                    message="Image missing alt text (use ![description](url))",
                    file=str(path),
                    line=token.get("line", 1),
                    col=1,
                    severity=Severity.WARN,
                    engine="markdown-ast",
                    fixable=False,
                )
            )

    return violations


# ── Engine class ──────────────────────────────────────────────


class MarkdownAstEngine(LintEngine):
    """Engine that uses markdown-it-py for precise documentation analysis."""

    name = "markdown-ast"

    def __init__(self):
        """Initialize markdown parser."""
        self.md = MarkdownIt()

    def is_available(self) -> bool:
        """Always available (uses markdown-it-py)."""
        return True

    def check(self, project_root: Path, config: dict) -> EngineResult:
        """Run all registered rules on Markdown files."""
        result = EngineResult(engine_name=self.name)
        paths = config.get("grit_paths", ["."])

        md_files = []
        for p in paths:
            target = project_root / p
            if target.is_file() and target.suffix in (".md", ".markdown"):
                md_files.append(target)
            elif target.is_dir():
                md_files.extend(target.rglob("*.md"))
                md_files.extend(target.rglob("*.markdown"))

        for md_file in md_files:
            # Skip node_modules, .git, etc.
            if any(
                skip in str(md_file) for skip in ["node_modules", ".git", "__pycache__"]
            ):
                continue

            try:
                content = md_file.read_text(encoding="utf-8")
                tokens = self.md.parse(content)
            except Exception:
                continue  # Skip files that can't be parsed

            # Convert tokens to dict list for easier processing
            # Flatten token tree to include all children
            token_dicts = []

            def collect_tokens(tok_list):
                """Recursively collect all tokens including children."""
                for tok in tok_list:
                    token_dict = {
                        "type": tok.type,
                        "tag": tok.tag,
                        "attrs": dict(tok.attrs) if tok.attrs else {},
                        "content": tok.content,
                        "info": tok.info,
                        "line": tok.map[0] + 1 if tok.map else 1,
                    }
                    token_dicts.append(token_dict)
                    # Recursively collect children
                    if tok.children:
                        collect_tokens(tok.children)

            collect_tokens(tokens)

            rel_path = md_file.relative_to(project_root)
            for rule_id, (fn, severity, desc) in _REGISTRY.items():
                violations = fn(rel_path, token_dicts)
                for v in violations:
                    v.file = str(rel_path)
                result.violations.extend(violations)

        return result

    def get_rules(self) -> list[dict]:
        """Return info about registered rules."""
        return [
            {
                "id": rule_id,
                "engine": "markdown-ast",
                "severity": sev.value,
                "description": desc,
            }
            for rule_id, (_, sev, desc) in _REGISTRY.items()
        ]
