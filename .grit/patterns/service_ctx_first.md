---
name: service_ctx_first
title: Service 方法第一个参数必须是 ctx
description: "所有 Service 类的方法，第一个参数必须是 ctx: Context"
level: warn
tags:
  - convention
  - architecture
---

# Service 方法签名规范

```grit
language python

`def $method(self, $first, $...):` where {
  $first <: not `ctx`,
  $first <: not `self`,
  $first <: not r"^_",
}
```

## 违规
```python
class UserService:
    def get_user(self, user_id: int):
        pass
```

## 正确
```python
class UserService:
    def get_user(self, ctx, user_id: int):
        pass
```
