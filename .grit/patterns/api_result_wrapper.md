---
name: api_result_wrapper
title: API 返回值必须封装 Result
description: API 层函数不能返回裸 dict，必须封装在 Result 对象中
level: error
tags:
  - convention
  - architecture
---

# API 返回值规范

```grit
language python

`return {$...}` where {}
```

## 违规
```python
return {"id": user_id, "name": "test"}
```

## 正确
```python
return Result(data=user)
```
