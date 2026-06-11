"""Tests for Markdown AST engine rules."""

import pytest
from pathlib import Path
from markdown_it import MarkdownIt

from unified_lint.engines.markdown_ast import (
    check_frontmatter_fields,
    check_broken_links,
    check_heading_structure,
    check_code_block_lang,
    check_image_alt,
)

md = MarkdownIt()


def test_frontmatter_missing_last_updated(tmp_path):
    """Test that missing last_updated field is flagged."""
    doc = tmp_path / "test.md"
    doc.write_text("---\ntitle: Test\n---\n\n# Content\n", encoding="utf-8")

    tokens = md.parse(doc.read_text(encoding="utf-8"))
    token_dicts = [
        {
            "type": t.type,
            "tag": t.tag,
            "attrs": dict(t.attrs) if t.attrs else {},
            "content": t.content,
            "info": t.info,
            "line": t.map[0] + 1 if t.map else 1,
        }
        for t in tokens
    ]

    violations = check_frontmatter_fields(doc, token_dicts)
    assert len(violations) == 1
    assert "last_updated" in violations[0].message


def test_frontmatter_has_last_updated(tmp_path):
    """Test that valid frontmatter passes."""
    doc = tmp_path / "test.md"
    doc.write_text(
        "---\ntitle: Test\nlast_updated: 2024-01-01\n---\n\n# Content\n",
        encoding="utf-8",
    )

    tokens = md.parse(doc.read_text(encoding="utf-8"))
    token_dicts = [
        {
            "type": t.type,
            "tag": t.tag,
            "attrs": dict(t.attrs) if t.attrs else {},
            "content": t.content,
            "info": t.info,
            "line": t.map[0] + 1 if t.map else 1,
        }
        for t in tokens
    ]

    violations = check_frontmatter_fields(doc, token_dicts)
    assert len(violations) == 0


def test_broken_link(tmp_path):
    """Test that broken internal link is flagged."""
    doc = tmp_path / "test.md"
    doc.write_text("# Test\n\n[Link](./missing.md)\n", encoding="utf-8")

    tokens = md.parse(doc.read_text(encoding="utf-8"))
    token_dicts = []

    def collect_tokens(tok_list):
        for t in tok_list:
            token_dicts.append(
                {
                    "type": t.type,
                    "tag": t.tag,
                    "attrs": dict(t.attrs) if t.attrs else {},
                    "content": t.content,
                    "info": t.info,
                    "line": t.map[0] + 1 if t.map else 1,
                }
            )
            if t.children:
                collect_tokens(t.children)

    collect_tokens(tokens)

    violations = check_broken_links(doc, token_dicts)
    assert len(violations) == 1
    assert "missing.md" in violations[0].message


def test_valid_link(tmp_path):
    """Test that valid internal link passes."""
    doc = tmp_path / "test.md"
    target = tmp_path / "target.md"
    target.write_text("# Target\n", encoding="utf-8")

    doc.write_text("# Test\n\n[Link](./target.md)\n", encoding="utf-8")

    tokens = md.parse(doc.read_text(encoding="utf-8"))
    token_dicts = [
        {
            "type": t.type,
            "tag": t.tag,
            "attrs": dict(t.attrs) if t.attrs else {},
            "content": t.content,
            "info": t.info,
            "line": t.map[0] + 1 if t.map else 1,
        }
        for t in tokens
    ]

    violations = check_broken_links(doc, token_dicts)
    assert len(violations) == 0


def test_heading_skip(tmp_path):
    """Test that heading level skip is flagged."""
    doc = tmp_path / "test.md"
    doc.write_text("# Title\n\n### Subtitle\n", encoding="utf-8")

    tokens = md.parse(doc.read_text(encoding="utf-8"))
    token_dicts = [
        {
            "type": t.type,
            "tag": t.tag,
            "attrs": dict(t.attrs) if t.attrs else {},
            "content": t.content,
            "info": t.info,
            "line": t.map[0] + 1 if t.map else 1,
        }
        for t in tokens
    ]

    violations = check_heading_structure(doc, token_dicts)
    assert len(violations) == 1
    assert "h3" in violations[0].message
    assert "h2" in violations[0].message


def test_heading_valid(tmp_path):
    """Test that valid heading structure passes."""
    doc = tmp_path / "test.md"
    doc.write_text("# Title\n\n## Subtitle\n\n### Sub-subtitle\n", encoding="utf-8")

    tokens = md.parse(doc.read_text(encoding="utf-8"))
    token_dicts = [
        {
            "type": t.type,
            "tag": t.tag,
            "attrs": dict(t.attrs) if t.attrs else {},
            "content": t.content,
            "info": t.info,
            "line": t.map[0] + 1 if t.map else 1,
        }
        for t in tokens
    ]

    violations = check_heading_structure(doc, token_dicts)
    assert len(violations) == 0


def test_code_block_no_lang(tmp_path):
    """Test that code block without language is flagged."""
    doc = tmp_path / "test.md"
    doc.write_text("# Test\n\n```\nprint('hello')\n```\n", encoding="utf-8")

    tokens = md.parse(doc.read_text(encoding="utf-8"))
    token_dicts = [
        {
            "type": t.type,
            "tag": t.tag,
            "attrs": dict(t.attrs) if t.attrs else {},
            "content": t.content,
            "info": t.info,
            "line": t.map[0] + 1 if t.map else 1,
        }
        for t in tokens
    ]

    violations = check_code_block_lang(doc, token_dicts)
    assert len(violations) == 1
    assert "language" in violations[0].message


def test_code_block_with_lang(tmp_path):
    """Test that code block with language passes."""
    doc = tmp_path / "test.md"
    doc.write_text("# Test\n\n```python\nprint('hello')\n```\n", encoding="utf-8")

    tokens = md.parse(doc.read_text(encoding="utf-8"))
    token_dicts = [
        {
            "type": t.type,
            "tag": t.tag,
            "attrs": dict(t.attrs) if t.attrs else {},
            "content": t.content,
            "info": t.info,
            "line": t.map[0] + 1 if t.map else 1,
        }
        for t in tokens
    ]

    violations = check_code_block_lang(doc, token_dicts)
    assert len(violations) == 0


def test_image_no_alt(tmp_path):
    """Test that image without alt text is flagged."""
    doc = tmp_path / "test.md"
    doc.write_text("# Test\n\n![](./image.png)\n", encoding="utf-8")

    tokens = md.parse(doc.read_text(encoding="utf-8"))
    token_dicts = []

    def collect_tokens(tok_list):
        for t in tok_list:
            token_dicts.append(
                {
                    "type": t.type,
                    "tag": t.tag,
                    "attrs": dict(t.attrs) if t.attrs else {},
                    "content": t.content,
                    "info": t.info,
                    "line": t.map[0] + 1 if t.map else 1,
                }
            )
            if t.children:
                collect_tokens(t.children)

    collect_tokens(tokens)

    violations = check_image_alt(doc, token_dicts)
    assert len(violations) == 1
    assert "alt" in violations[0].message


def test_image_with_alt(tmp_path):
    """Test that image with alt text passes."""
    doc = tmp_path / "test.md"
    doc.write_text("# Test\n\n![Description](./image.png)\n", encoding="utf-8")

    tokens = md.parse(doc.read_text(encoding="utf-8"))
    token_dicts = [
        {
            "type": t.type,
            "tag": t.tag,
            "attrs": dict(t.attrs) if t.attrs else {},
            "content": t.content,
            "info": t.info,
            "line": t.map[0] + 1 if t.map else 1,
        }
        for t in tokens
    ]

    violations = check_image_alt(doc, token_dicts)
    assert len(violations) == 0
