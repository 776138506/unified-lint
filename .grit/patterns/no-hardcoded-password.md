---
name: no-hardcoded-password
title: 禁止硬编码密码
description: 密码必须使用环境变量引用，禁止在代码中硬编码
level: error
tags:
  - security
  - credentials
---

# 禁止硬编码密码

匹配模式：`password = "..."` 或 `PASSWORD = "..."`

```grit
language python

or {
  `$name = $value` as $assign,
  `$name: $value` as $assign
} where {
  $name <: r"(?i)password|passwd|pwd|secret|api_key",
  $value <: r"^['"]",
  $value <: not r"^\$\{",
  $assign <: not contains r"os\.environ|os\.getenv",
  register_diagnostic(
    span = $assign,
    message = "R001: 禁止硬编码密码/密钥。请使用 os.environ 或配置文件引用。"
  )
}
```

## 违规示例
```python
password = "admin123"  # ✗ 违规
API_KEY = "sk-abc123"  # ✗ 违规
```

## 正确写法
```python
password = os.environ["DB_PASSWORD"]  # ✓ 正确
API_KEY = os.getenv("API_KEY", "")    # ✓ 正确
```
