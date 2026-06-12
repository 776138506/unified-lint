# Python GritQL 规则示例集

## 1. 禁止硬编码密码

```grit
language python

`$name = $value` where {
  $name <: r"(?i)password|passwd|pwd|secret|api_key",
}
```

**匹配**：`password = "admin123"` ✓
**不匹配**：`password = get_env_var(...)` ✗（非字符串字面量）

## 2. Service 方法 ctx-first 签名

```grit
language python

`def $method(self, $first, $...):` where {
  $first <: not `ctx`,
  $first <: not `self`,
  $first <: not r"^_",
}
```

**匹配**：`def get_user(self, user_id: int):` ✓
**不匹配**：`def get_user(self, ctx, user_id: int):` ✗

### 限制

当前 GritQL Python parser 对 type annotation 的匹配有限。
`$first <: not r"^_"` 用来排除 dunder 方法，
但不能精确区分 class 内部 vs 模块级函数。

## 3. API 返回值裸 dict

```grit
language python

`return {$...}` where {}
```

**匹配**：`return {"id": user_id}` ✓
**不匹配**：`return Result(data=user)` ✗

### 限制

会匹配所有 dict literal return。生产环境需加路径过滤。

## 4. 文档 frontmatter 检查

```grit
language markdown

`---
$frontmatter
---
$body` where {
  $frontmatter <: not contains `last_updated`,
}
```

### 限制

Markdown 支持是 Alpha。`file()` 函数在 standalone CLI 中不可用。
只能用模板匹配 `--- ... ---` 模式。

## 5. 模式匹配技巧速查

```
匹配函数:    `def $fn($...):`
至少一参数:   `def $fn($first, $...):`
方法(self):  `def $fn(self, $...):`
任何赋值:    `$name = $value`
带类型注解:   `$name: $type = $value`
正则变量名:   $name <: r"(?i)pattern"
排除特定值:   $value <: not `None`
嵌套查找:    $body <: contains `return $val` where { ... }
```
