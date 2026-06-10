---
name: api_result_wrapper
title: API 返回值必须封装 Result
description: api/ 目录下的函数返回值必须封装在 Result 对象中
level: error
tags:
  - convention
  - architecture
---

# API 返回值规范

API 层函数不能返回裸 dict/list，必须封装在 Result 对象中。

```grit
language python

`def $fn($...):
    $body` where {
  $body <: contains `return $value` where {
    $value <: r"^\{",
  }
}
```

## 违规
```python
def get_user_api(user_id: int):
    return {"id": user_id, "name": "test"}
```

## 正确
```python
def get_user_api(user_id: int):
    return Result(data={"id": user_id})
```
