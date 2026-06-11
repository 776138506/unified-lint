---
name: no_hardcoded_password
title: 禁止硬编码密码
description: 密码必须使用环境变量引用，禁止在代码中硬编码
level: error
tags:
  - security
---

# 禁止硬编码密码

```grit
language python

`$name = $value` where {
  $name <: r"(?i)password|passwd|pwd|secret|api_key",
}
```

## 违规
```python
password = "admin123"
```

## 正确
```python
password = os.getenv("DB_PASSWORD")
```
