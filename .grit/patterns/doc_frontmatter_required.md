---
name: doc_frontmatter_required
title: 文档必须包含 frontmatter
description: "docs/ 目录下的 Markdown 文档必须包含 YAML frontmatter"
level: warn
tags:
  - documentation
---

# 文档 Frontmatter 规范

docs/ 目录下所有 Markdown 文件必须包含 `---` frontmatter。

```grit
language markdown

`---
$frontmatter
---
$body` where {
  $frontmatter <: not contains `last_updated`,
}
```

## 正确示例
```markdown
---
last_updated: 2026-06-10
---

# API 文档
```

## 违规
缺少 frontmatter 或 frontmatter 中没有 last_updated。
