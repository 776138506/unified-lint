"""Rule discovery and indexing."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

# Builtin rules as GritQL markdown patterns
BUILTIN_RULES = [
    {
        "id": "no_hardcoded_password",
        "engine": "grit",
        "severity": "error",
        "description": "No hardcoded passwords/secrets in code",
        "content": """---
name: no_hardcoded_password
title: "No hardcoded passwords"
description: "Passwords must use environment variables, never hardcoded"
level: error
tags:
  - security
---

# No Hardcoded Passwords

```grit
language python

`$name = $value` where {
  $name <: r"(?i)password|passwd|pwd|secret|api_key",
  // Exclude safe patterns: environment variables and config
  $value <: not r"os\.getenv",
  $value <: not r"os\.environ",
  $value <: not r"config\.",
  $value <: not r"settings\.",
  $value <: not r"^None$",
  $value <: not r'^""$',
  $value <: not r"^''$",
}
```

## Bad
```python
password = "admin123"
```

## Good
```python
password = os.getenv("DB_PASSWORD")
```
""",
    },
    {
        "id": "service_ctx_first",
        "engine": "grit",
        "severity": "warn",
        "description": "Service methods must have ctx as first parameter",
        "content": """---
name: service_ctx_first
title: "Service method ctx-first signature"
description: "All Service class methods must have ctx as the first parameter after self"
level: warn
tags:
  - convention
  - architecture
---

# Service Method Signature

```grit
language python

`def $method(self, $first, $...):` where {
  $first <: not `ctx`,
  $first <: not `self`,
}
```

## Bad
```python
class UserService:
    def get_user(self, user_id: int):
        pass
```

## Good
```python
class UserService:
    def get_user(self, ctx, user_id: int):
        pass
```
""",
    },
    {
        "id": "api_result_wrapper",
        "engine": "grit",
        "severity": "error",
        "description": "API functions must wrap returns in Result",
        "content": """---
name: api_result_wrapper
title: "API return must use Result wrapper"
description: "API layer functions must not return raw dicts"
level: error
tags:
  - convention
  - architecture
---

# API Return Wrapper

```grit
language python

`return {$...}` where {}
```

## Bad
```python
return {"id": user_id, "name": "test"}
```

## Good
```python
return Result(data=user)
```
""",
    },
    {
        "id": "doc_frontmatter",
        "engine": "grit",
        "severity": "warn",
        "description": "Docs must have YAML frontmatter with last_updated",
        "content": """---
name: doc_frontmatter
title: "Document frontmatter required"
description: "Markdown docs in docs/ must have YAML frontmatter with last_updated"
level: warn
tags:
  - documentation
---

# Document Frontmatter

```grit
language markdown

`---
$frontmatter
---
$body` where {
  $frontmatter <: not contains `last_updated`,
}
```

## Good
```markdown
---
last_updated: 2026-06-10
---
# API Docs
```
""",
    },
    {
        "id": "no_bare_except",
        "engine": "grit",
        "severity": "warn",
        "description": "No bare except clauses",
        "content": """---
name: no_bare_except
title: "No bare except"
description: "Use specific exception types instead of bare except"
level: warn
tags:
  - reliability
---

# No Bare Except

```grit
language python

`except:
    $body`
```

## Bad
```python
try:
    do_something()
except:
    pass
```

## Good
```python
try:
    do_something()
except ValueError:
    pass
```
""",
    },
    {
        "id": "no_n_plus_one",
        "engine": "grit",
        "severity": "error",
        "description": "No SELECT queries inside loops (N+1 problem)",
        "content": """---
name: no_n_plus_one
title: "No N+1 queries"
description: "Do not execute SELECT queries inside loops"
level: error
tags:
  - performance
---

# No N+1 Queries

```grit
language python

`for $item in $iterable:
    $body` where {
  $body <: contains `$var.execute($query)`,
  $query <: r"(?i)(SELECT|select)",
}
```

## Bad
```python
for user in users:
    cursor.execute("SELECT * FROM orders WHERE user_id = %s", (user.id,))
```

## Good
```python
user_ids = [u.id for u in users]
cursor.execute("SELECT * FROM orders WHERE user_id IN %s", (user_ids,))
```
""",
    },
]


def get_builtin_rules() -> list[dict]:
    """Return all builtin rules."""
    return BUILTIN_RULES


def discover_rules(project_root: Path) -> list[dict]:
    """Discover all rules: builtin + project-level overrides."""
    rules = []

    # Builtin rules
    for rule in BUILTIN_RULES:
        rule_info = {
            "id": rule["id"],
            "engine": rule["engine"],
            "severity": rule["severity"],
            "description": rule["description"],
            "source": "builtin",
        }

        # Check for project-level override
        override = project_root / ".grit" / "patterns" / f"{rule['id']}.md"
        if override.exists():
            rule_info["source"] = "project"

        rules.append(rule_info)

    # Project-only rules (not in builtin)
    patterns_dir = project_root / ".grit" / "patterns"
    if patterns_dir.exists():
        builtin_ids = {r["id"] for r in BUILTIN_RULES}
        for md_file in patterns_dir.glob("*.md"):
            rule_id = md_file.stem
            if rule_id not in builtin_ids:
                rules.append(
                    {
                        "id": rule_id,
                        "engine": "grit",
                        "severity": "warn",
                        "description": f"Project rule: {rule_id}",
                        "source": "project",
                    }
                )

    return rules
