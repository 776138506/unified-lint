# Working GritQL Patterns (verified 2026-06-11)

These patterns are tested and confirmed working with standalone Grit CLI v0.1.1.
Do NOT use `register_diagnostic` — it is Biome-specific, not available in standalone grit.

## Pattern: No Hardcoded Secrets (with safe-assignment exclusions)

```grit
language python

`$name = $value` where {
  $name <: r"(?i)password|passwd|pwd|secret|api_key",
  $value <: not r"os\.",
  $value <: not r"config\.",
  $value <: not r"settings\.",
  $value <: not r"^None$",
  $value <: not r'^""$',
  $value <: not r"^''$",
}
```

**Why exclusions matter**: Without them, any assignment to a variable named `password` or `api_key` triggers, even when the value comes from a safe source (environment lookup, config module). Always exclude safe assignment patterns when matching by variable name.

## Pattern: Service Method ctx-first

```grit
language python

`def $method(self, $first, $...):` where {
  $first <: not `ctx`,
  $first <: not `self`,
}
```

**Limitation**: Matches ALL methods in ALL classes, not just Service classes. Class-scoped matching is unreliable in Alpha Python parser.

## Pattern: API Return Raw Dict

```grit
language python

`return {$...}` where {}
```

Simple and reliable — catches any `return {...}` regardless of context.

## Pattern: Doc Frontmatter (Markdown)

```grit
language markdown

`---
$frontmatter
---
$body` where {
  $frontmatter <: not contains `last_updated`,
}
```

**Note**: Only matches files that ALREADY have frontmatter but are missing `last_updated`. Files without any frontmatter will not match (GritQL Markdown parser limitation).

## Pattern: Bare Except

```grit
language python

`except:
    $body`
```

## Key GritQL Syntax Reminders

- `where { ... }` = conditions (all must be true, comma-separated)
- `<:` = match operator (tests if variable matches pattern)
- `not` = negation
- `$...` = spread (zero or more args)
- `r"..."` = regex match on text content
- `contains` = search entire subtree

## GritQL Pattern File Format

```markdown
---
name: rule_name_underscore     # NO HYPHENS allowed
title: "Human Readable Title"
description: "Description. Quote if it contains colons."
level: error                   # error | warn | info
tags:
  - security
---

# Title

(paste grit code block here)

## Examples
## Bad/Good code snippets
```
