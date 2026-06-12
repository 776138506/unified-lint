"""Pattern templates for rule add wizard.

Each template provides a complete, runnable GritQL pattern body so the
generated `.grit/patterns/<id>.md` file is immediately functional
(out-of-the-box matches real violations in typical projects).

Users can edit the generated file to refine patterns.
"""

from __future__ import annotations

from typing import TypedDict


class Template(TypedDict):
    """A pattern template entry."""

    label: str
    description: str
    pattern_markdown: str


TEMPLATES: dict[str, Template] = {
    "sensitive_field": {
        "label": "sensitive_field",
        "description": (
            "Detect hardcoded passwords, API keys, tokens. "
            "Excludes os.getenv, config.*, None, empty strings."
        ),
        "pattern_markdown": (
            "```grit\n"
            "language python\n"
            "\n"
            "`$name = $value` where {\n"
            '  $name <: r"(?i)password|passwd|pwd|secret|api_key|token|credential",\n'
            '  $value <: not r"os\\.getenv",\n'
            '  $value <: not r"os\\.environ",\n'
            '  $value <: not r"config\\.",\n'
            '  $value <: not r"settings\\.",\n'
            '  $value <: not r"^None$",\n'
            "  $value <: not r'^\"\"$',\n"
            "  $value <: not r\"^''$\",\n"
            "}\n"
            "```\n"
            "\n"
            "## Bad\n"
            "```python\n"
            'db_password = "admin123"\n'
            "```\n"
            "\n"
            "## Good\n"
            "```python\n"
            'db_password = os.getenv("DB_PASSWORD")\n'
            "```\n"
        ),
    },
    "func_signature": {
        "label": "func_signature",
        "description": (
            "Enforce function signature convention. "
            "Default: first parameter after `self` must be `ctx`."
        ),
        "pattern_markdown": (
            "```grit\n"
            "language python\n"
            "\n"
            "`def $method(self, $first, $...rest):` where {\n"
            "  $first <: not `ctx`,\n"
            "  $first <: not `self`,\n"
            "}\n"
            "```\n"
            "\n"
            "## Bad\n"
            "```python\n"
            "def get_user(self, user_id: int): ...\n"
            "```\n"
            "\n"
            "## Good\n"
            "```python\n"
            "def get_user(self, ctx, user_id: int): ...\n"
            "```\n"
        ),
    },
    "naming": {
        "label": "naming",
        "description": (
            "Enforce snake_case for function names. "
            "Default pattern: function names matching `^[a-z][a-z0-9_]*$`."
        ),
        "pattern_markdown": (
            "```grit\n"
            "language python\n"
            "\n"
            "`def $name($...args):` where {\n"
            '  $name <: not r"^[a-z][a-z0-9_]*$",\n'
            "}\n"
            "```\n"
            "\n"
            "## Bad\n"
            "```python\n"
            "def GetUser(...): ...    # PascalCase\n"
            "def getUser(...): ...    # camelCase\n"
            "```\n"
            "\n"
            "## Good\n"
            "```python\n"
            "def get_user(...): ...   # snake_case\n"
            "```\n"
        ),
    },
    "no_print": {
        "label": "no_print",
        "description": (
            "Disallow `print()` in production code. Use `logging.info()` instead."
        ),
        "pattern_markdown": (
            "```grit\n"
            "language python\n"
            "\n"
            "`print($...args)` where {\n"
            "  // Allow in tests (heuristic: file path contains /tests/ or _test.py)\n"
            '  $file <: not r"tests?/|_test\\.py$",\n'
            "}\n"
            "```\n"
            "\n"
            "## Bad\n"
            "```python\n"
            'print("debug:", user_id)\n'
            "```\n"
            "\n"
            "## Good\n"
            "```python\n"
            "import logging\n"
            "logger = logging.getLogger(__name__)\n"
            'logger.info("user lookup: %s", user_id)\n'
            "```\n"
        ),
    },
    "custom": {
        "label": "custom",
        "description": "Empty stub. You write the pattern from scratch.",
        "pattern_markdown": (
            "```grit\n"
            "language python\n"
            "\n"
            "// TODO: write your GritQL pattern here.\n"
            "// See https://docs.grit.io for syntax.\n"
            "//\n"
            "// Example:\n"
            "// `$name = $value` where {{\n"
            '//   $name <: r"(?i)password",\n'
            '//   $value <: not r"os\\\\.getenv",\n'
            "// }}\n"
            "```\n"
        ),
    },
}


TEMPLATE_CHOICES = list(TEMPLATES.keys())


def get_template(name: str) -> Template:
    """Return template by name; raises KeyError if not found."""
    return TEMPLATES[name]


def render_rule_file(
    rule_id: str,
    title: str,
    severity: str,
    template_name: str,
    description: str = "",
    extra_tags: list[str] | None = None,
) -> str:
    """Render the full markdown content for a rule file."""
    if template_name not in TEMPLATES:
        raise ValueError(
            f"Unknown template: {template_name}. "
            f"Choose from: {', '.join(TEMPLATE_CHOICES)}"
        )
    template = TEMPLATES[template_name]
    tags = ["custom"]
    if extra_tags:
        tags.extend(extra_tags)
    tags_str = "\n".join(f"  - {t}" for t in tags)

    if not description:
        description = f"[{template['label']}] {template['description']}"

    return (
        f"---\n"
        f"name: {rule_id}\n"
        f'title: "{title}"\n'
        f'description: "{description}"\n'
        f"level: {severity}\n"
        f"tags:\n"
        f"{tags_str}\n"
        f"---\n"
        "\n"
        f"# {title}\n"
        "\n"
        f"{template['pattern_markdown']}"
    )
