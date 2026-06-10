---
name: api-result-wrapper
title: API 返回值必须封装 Result
description: api/ 目录下的函数返回值必须封装在 Result 对象中
level: error
tags:
  - convention
  - api
---

# API 返回值封装规范

`api/` 目录下的所有函数，返回值不能是裸对象，必须包装为 `Result`。

```grit
language python

`def $fn($...):
    $body` as $func where {
  $body <: contains `return $value` as $ret where {
    $value <: not r"Result",
    $value <: not r"None$",
    $value <: not r"\{",
    register_diagnostic(
      span = $ret,
      message = "R003: API 函数 '$fn' 返回值必须封装在 Result 对象中。使用 Result.ok(data) 或 Result.error(msg)。"
    )
  }
}
```

## 违规示例
```python
def get_user_api(user_id: int):
    return service.get_user(user_id)  # ✗ 裸返回
```

## 正确写法
```python
def get_user_api(user_id: int):
    user = service.get_user(user_id)
    return Result.ok(user)  # ✓ 封装 Result
```
