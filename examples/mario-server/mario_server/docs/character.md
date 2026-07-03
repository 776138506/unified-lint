# Character 模块

角色（Character）是核心实体，包含 Mario / Luigi / Peach 等。

## 用法

```
character = repo.find_by_id(1)
```

## 字段

```
id: int
name: str
hp: int
level: int
```

## 状态机示例

```python
if character.hp <= 0:
    raise GameOver()
```

## 字段说明

- id
- name
- hp
- level
