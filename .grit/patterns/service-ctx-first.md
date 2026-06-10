---
name: service-ctx-first
title: Service 方法第一个参数必须是 ctx
description: 所有 Service 类的方法，第一个参数必须是 ctx: Context
level: warn
tags:
  - convention
  - architecture
---

# Service 方法签名规范

Service 类中所有公开方法，第一个参数必须是 `ctx`。

```grit
language python

`class $cls:
    $body` as $class where {
  $cls <: r"Service$",
  $body <: contains `def $method(self, $first, $...):` as $def where {
    $method <: not r"^_",
    $first <: not `ctx`,
    $first <: not `context`,
    $first <: not `self`,
    register_diagnostic(
      span = $def,
      message = "R002: Service 方法 '$method' 的第一个参数必须是 ctx: Context，当前是 '$first'。"
    )
  }
}
```

## 违规示例
```python
class UserService:
    def get_user(self, user_id: int):  # ✗ 缺少 ctx
        pass
```

## 正确写法
```python
class UserService:
    def get_user(self, ctx: Context, user_id: int):  # ✓
        pass
```
