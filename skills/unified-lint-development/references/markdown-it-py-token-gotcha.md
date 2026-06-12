# markdown-it-py Token 展平问题详解

## 问题现象

使用 markdown-it-py 解析文档时，`link_open` 和 `image` 规则的测试始终失败（0 violations），即使文档中明显包含链接和图片。

## 根因

markdown-it-py 的 token 结构是**树状**的，不是平铺的：

```python
tokens = md.parse(content)

# 顶层 tokens 只包含块级元素：
# [heading_open, inline, heading_close, paragraph_open, inline, ...]

# inline token 的 children 才包含行内元素：
# inline.children = [link_open, text, link_close]
# inline.children = [image]
```

`md.parse()` 返回的是顶层 token 列表，而 `link_open` 和 `image` 嵌套在 `inline` token 的 `children` 属性中。

## 错误做法（只遍历顶层）

```python
# ❌ 错误：只遍历顶层 token
token_dicts = [
    {
        "type": t.type,
        "tag": t.tag,
        "attrs": dict(t.attrs) if t.attrs else {},
        "content": t.content,
        "info": t.info,
        "line": t.map[0] + 1 if t.map else 1,
    }
    for t in tokens  # 这里只拿到 inline，拿不到 link_open
]

# 结果：token_dicts 中没有 type="link_open" 或 type="image" 的条目
# 规则永远匹配不到
```

## 正确做法（递归展平）

```python
# ✓ 正确：递归展平 token 树
token_dicts = []

def collect_tokens(tok_list):
    """Recursively collect all tokens including children."""
    for tok in tok_list:
        token_dict = {
            "type": tok.type,
            "tag": tok.tag,
            "attrs": dict(tok.attrs) if tok.attrs else {},
            "content": tok.content,
            "info": tok.info,
            "line": tok.map[0] + 1 if tok.map else 1,
        }
        token_dicts.append(token_dict)
        # 递归收集子 token
        if tok.children:
            collect_tokens(tok.children)

collect_tokens(tokens)

# 结果：token_dicts 包含所有 token，包括嵌套的 link_open 和 image
```

## 验证方法

```python
from markdown_it import MarkdownIt

md = MarkdownIt()
content = "# Test\n\n[Link](./missing.md)\n"
tokens = md.parse(content)

print("=== 顶层 tokens ===")
for t in tokens:
    print(f"  type={t.type}, tag={t.tag}")

print("\n=== 递归展平后 ===")
flat = []
def collect(tok_list):
    for t in tok_list:
        flat.append(t)
        if t.children:
            collect(t.children)
collect(tokens)

for t in flat:
    print(f"  type={t.type}, tag={t.tag}")
```

输出：
```
=== 顶层 tokens ===
  type=heading_open, tag=h1
  type=inline, tag=
  type=heading_close, tag=h1
  type=paragraph_open, tag=p
  type=inline, tag=
  type=paragraph_close, tag=p

=== 递归展平后 ===
  type=heading_open, tag=h1
  type=inline, tag=
  type=text, tag=
  type=heading_close, tag=h1
  type=paragraph_open, tag=p
  type=inline, tag=
  type=link_open, tag=a        ← 找到了！
  type=text, tag=
  type=link_close, tag=a
  type=paragraph_close, tag=p
```

## 测试中也要展平

测试代码中构建 `token_dicts` 时，必须使用同样的展平逻辑：

```python
def test_broken_link(tmp_path):
    doc = tmp_path / "test.md"
    doc.write_text("# Test\n\n[Link](./missing.md)\n", encoding="utf-8")

    tokens = md.parse(doc.read_text(encoding="utf-8"))
    token_dicts = []

    def collect_tokens(tok_list):
        for t in tok_list:
            token_dicts.append({
                "type": t.type,
                "tag": t.tag,
                "attrs": dict(t.attrs) if t.attrs else {},
                "content": t.content,
                "info": t.info,
                "line": t.map[0] + 1 if t.map else 1,
            })
            if t.children:
                collect_tokens(t.children)

    collect_tokens(tokens)  # ← 必须展平

    violations = check_broken_links(doc, token_dicts)
    assert len(violations) == 1  # 现在能通过
```

## 教训总结

1. **不要假设 token 结构是平铺的** — 先打印出来看实际结构
2. **引擎和测试必须用同样的展平逻辑** — 否则测试会通过但实际不工作（或反过来）
3. **嵌套 token 是常见模式** — 不只是 markdown-it-py，很多解析器都有类似的树状结构

## 相关文件

- `src/unified_lint/engines/markdown_ast.py` — 引擎实现（264-279 行）
- `tests/test_markdown_ast.py` — 测试实现（所有 test_* 函数）
