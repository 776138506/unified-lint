# unified-lint 自定义规则开发指南

本指南教你如何为 unified-lint 编写自定义规则。unified-lint 支持六种引擎，每种引擎适用于不同类型的检查。

## 目录

1. [引擎选择指南](#引擎选择指南)
2. [GritQL 引擎：简单模式匹配](#gritql-引擎简单模式匹配)
3. [Python AST 引擎：精确代码分析](#python-ast-引擎精确代码分析)
4. [Markdown AST 引擎：文档结构分析](#markdown-ast-引擎文档结构分析)
5. [Tree-sitter 引擎：Rust 和 C# 支持](#tree-sitter-引擎rust-和-c-支持)
6. [Spec-chain 引擎：文档阶段一致性](#spec-chain-引擎文档阶段一致性)
7. [测试你的规则](#测试你的规则)
8. [完整示例：从零编写一条规则](#完整示例从零编写一条规则)

---

## 引擎选择指南

### 三种引擎对比

| 引擎 | 适用场景 | 优势 | 劣势 |
|------|---------|------|------|
| **GritQL** | 简单的文本/语法模式匹配 | 语法简洁，跨语言 | Python parser 是 Alpha，复杂结构匹配不稳定 |
| **Python AST** | 精确的 Python 代码分析 | 100% 准确，完整 AST 访问 | 仅支持 Python |
| **Markdown AST** | 文档结构和内容检查 | 精确解析 Markdown 元素 | 仅支持 Markdown |
| **Tree-sitter** | Rust 和 C# 代码分析 | 精确 AST，多语言扩展性强 | 需安装语言 grammar |
| **Spec-chain** | 文档阶段一致性检查 | 检查上下游文档契约 | 仅支持 YAML frontmatter |
| **import-linter** | Python 架构依赖检查 | 分层架构强制执行 | 仅支持 Python |

### 决策树

```
你要检查什么？
│
├─ Python 代码的函数/类/控制流
│  └─ 使用 Python AST 引擎
│
├─ Rust 代码（unsafe/pub API/函数长度）
│  └─ 使用 Tree-sitter 引擎
│
├─ C# 代码（async-await/命名/null）
│  └─ 使用 Tree-sitter 引擎
│
├─ Markdown 文档的 frontmatter/链接/heading/代码块
│  └─ 使用 Markdown AST 引擎
│
├─ 简单的赋值语句模式（如 `password = "xxx"`）
│  └─ 使用 GritQL 引擎
│
├─ 跨语言的模式匹配（如 JavaScript/Go）
│  └─ 使用 GritQL 引擎
│
└─ Python 项目架构依赖方向
   └─ 使用 import-linter 引擎
```

---

## GritQL 引擎：简单模式匹配

GritQL 使用模式匹配语法，适合检查简单的代码模式。

### 基本语法

```markdown
---
name: rule_name
title: "Rule Title"
description: "What this rule checks"
level: error  # 或 warn
tags:
  - category
---

# Rule Name

Description of the rule.

```grit
language python

`pattern` where {
  condition1,
  condition2
}
```

## Bad Example
```python
# Code that violates the rule
```

## Good Example
```python
# Code that follows the rule
```
```

### 示例：禁止硬编码密码

```markdown
---
name: no_hardcoded_password
title: "No hardcoded passwords"
description: "Passwords must use environment variables, never hardcoded"
level: error
tags:
  - security
---

# No Hardcoded Passwords

```grit
language python

`$name = $value` where {
  $name <: r"(?i)password|passwd|pwd|secret|api_key",
  // Exclude safe patterns
  $value <: not r"os\.getenv",
  $value <: not r"os\.environ",
  $value <: not r"config\.",
  $value <: not r"settings\.",
  $value <: not r"^None$",
  $value <: not r'^""$',
  $value <: not r"^''$",
}
```

## Bad
```python
password = "admin123"
api_key = "sk-abc123"
```

## Good
```python
password = os.getenv("PASSWORD")
api_key = os.environ["API_KEY"]
```
```

### GritQL 模式语法

- `$var` — 捕获任意代码片段
- `$...` — 捕获任意参数列表
- `r"regex"` — 正则表达式匹配
- `not r"regex"` — 正则表达式不匹配
- `where { ... }` — 附加条件

### 存放位置

```
.grit/patterns/your_rule.md
```

---

## Python AST 引擎：精确代码分析

Python AST 引擎使用 Python 的 `ast` 模块，可以精确分析函数、类、控制流等结构。

### 基本模板

```python
"""Your rule module."""

import ast
from pathlib import Path
from unified_lint.engines.python_ast import rule, Severity, Violation


@rule(
    "your_rule_id",
    Severity.ERROR,  # 或 Severity.WARN
    "Description of what this rule checks"
)
def check_your_rule(path: Path, tree: ast.Module) -> list[Violation]:
    """Check your custom rule."""
    violations = []
    
    # 遍历 AST 节点
    for node in ast.walk(tree):
        # 检查特定条件
        if isinstance(node, ast.FunctionDef):
            # 发现违规
            violations.append(
                Violation(
                    rule_id="your_rule_id",
                    message=f"Violation message for {node.name}",
                    file=str(path),
                    line=node.lineno,
                    col=node.col_offset + 1,
                    severity=Severity.ERROR,
                    engine="python-ast",
                    fixable=False,
                )
            )
    
    return violations
```

### 示例：检查函数参数命名规范

```python
"""Check that function parameters use snake_case."""

import ast
from pathlib import Path
from unified_lint.engines.python_ast import rule, Severity, Violation


@rule(
    "function_param_snake_case",
    Severity.WARN,
    "Function parameters should use snake_case naming"
)
def check_function_param_snake_case(path: Path, tree: ast.Module) -> list[Violation]:
    """Check that function parameters use snake_case."""
    violations = []
    
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        
        for arg in node.args.args:
            param_name = arg.arg
            
            # 跳过 self 和 cls
            if param_name in ("self", "cls"):
                continue
            
            # 检查是否包含大写字母（camelCase）
            if any(c.isupper() for c in param_name):
                violations.append(
                    Violation(
                        rule_id="function_param_snake_case",
                        message=f"Parameter '{param_name}' should use snake_case",
                        file=str(path),
                        line=arg.lineno,
                        col=arg.col_offset + 1,
                        severity=Severity.WARN,
                        engine="python-ast",
                        fixable=False,
                    )
                )
    
    return violations
```

### 常用 AST 节点类型

| 节点类型 | 说明 | 常用属性 |
|---------|------|---------|
| `ast.FunctionDef` | 函数定义 | `name`, `args`, `body`, `lineno` |
| `ast.ClassDef` | 类定义 | `name`, `bases`, `body`, `lineno` |
| `ast.Assign` | 赋值语句 | `targets`, `value`, `lineno` |
| `ast.Return` | 返回语句 | `value`, `lineno` |
| `ast.For` | for 循环 | `target`, `iter`, `body`, `lineno` |
| `ast.Call` | 函数调用 | `func`, `args`, `lineno` |
| `ast.Import` | import 语句 | `names`, `lineno` |
| `ast.ExceptHandler` | except 块 | `type`, `body`, `lineno` |

### 存放位置

```
src/unified_lint/engines/your_rule.py
```

然后在 `src/unified_lint/engines/python_ast.py` 中导入。

---

## Markdown AST 引擎：文档结构分析

Markdown AST 引擎使用 `markdown-it-py`，可以精确分析文档结构。

### 基本模板

```python
"""Your markdown rule module."""

from pathlib import Path
from unified_lint.engines.markdown_ast import rule, Severity, Violation


@rule(
    "your_md_rule_id",
    Severity.WARN,  # 或 Severity.ERROR
    "Description of what this rule checks"
)
def check_your_md_rule(path: Path, tokens: list[dict]) -> list[Violation]:
    """Check your custom markdown rule."""
    violations = []
    
    # 遍历 tokens
    for token in tokens:
        # 检查特定条件
        if token["type"] == "heading_open":
            # 发现违规
            violations.append(
                Violation(
                    rule_id="your_md_rule_id",
                    message="Violation message",
                    file=str(path),
                    line=token.get("line", 1),
                    col=1,
                    severity=Severity.WARN,
                    engine="markdown-ast",
                    fixable=False,
                )
            )
    
    return violations
```

### 示例：检查文档必须有标题

```python
"""Check that documents have at least one h1 heading."""

from pathlib import Path
from unified_lint.engines.markdown_ast import rule, Severity, Violation


@rule(
    "doc_has_h1",
    Severity.ERROR,
    "Documents must have at least one h1 heading"
)
def check_doc_has_h1(path: Path, tokens: list[dict]) -> list[Violation]:
    """Check that document has at least one h1 heading."""
    violations = []
    
    # 检查是否有 h1
    has_h1 = any(
        token["type"] == "heading_open" and token["tag"] == "h1"
        for token in tokens
    )
    
    if not has_h1:
        violations.append(
            Violation(
                rule_id="doc_has_h1",
                message="Document must have at least one h1 heading",
                file=str(path),
                line=1,
                col=1,
                severity=Severity.ERROR,
                engine="markdown-ast",
                fixable=False,
            )
        )
    
    return violations
```

### 常用 Token 类型

| Token 类型 | 说明 | 常用属性 |
|-----------|------|---------|
| `heading_open` | 标题开始 | `tag` (h1/h2/...), `line` |
| `paragraph_open` | 段落开始 | `line` |
| `link_open` | 链接开始 | `attrs["href"]`, `line` |
| `image` | 图片 | `attrs["src"]`, `content` (alt text), `line` |
| `fence` | 代码块 | `info` (language), `content`, `line` |
| `inline` | 内联内容 | `content`, `children`, `line` |

### 存放位置

```
src/unified_lint/engines/your_md_rule.py
```

然后在 `src/unified_lint/engines/markdown_ast.py` 中导入。

---

## Tree-sitter 引擎：Rust 和 C# 支持

Tree-sitter 引擎使用 [tree-sitter](https://tree-sitter.github.io/) 进行精确的 AST 分析，支持 Rust 和 C# 两种语言。

### 安装

```bash
pip install tree-sitter tree-sitter-rust tree-sitter-c-sharp
```

### 编写 Rust 规则

```python
"""Your Rust rule module."""

from pathlib import Path
from unified_lint.engines.tree_sitter_engine import TreeSitterEngine
from unified_lint.engines.base import Violation, Severity


class MyRustEngine(TreeSitterEngine):
    """Custom Rust rules."""

    def _check_rust_file(self, file_path: Path, project_root: Path) -> list[Violation]:
        violations = []

        from tree_sitter import Parser
        parser = Parser(self.languages["rust"])
        content = file_path.read_text(encoding="utf-8")
        tree = parser.parse(bytes(content, "utf-8"))

        def visit(node):
            # Example: detect unwrap() calls
            if node.type == "call_expression":
                for child in node.children:
                    if child.type == "field_expression":
                        for c in child.children:
                            if c.type == "field_identifier" and c.text == b"unwrap":
                                rel_path = file_path.relative_to(project_root)
                                violations.append(Violation(
                                    rule_id="rust_no_unwrap",
                                    message="Avoid unwrap() - use expect() or proper error handling",
                                    file=str(rel_path),
                                    line=node.start_point[0] + 1,
                                    col=node.start_point[1] + 1,
                                    severity=Severity.WARN,
                                    engine=self.name,
                                ))
            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return violations
```

### 编写 C# 规则

```python
"""Your C# rule module."""

from pathlib import Path
from unified_lint.engines.tree_sitter_engine import TreeSitterEngine
from unified_lint.engines.base import Violation, Severity


class MyCSharpEngine(TreeSitterEngine):
    """Custom C# rules."""

    def _check_csharp_file(self, file_path: Path, project_root: Path) -> list[Violation]:
        violations = []

        from tree_sitter import Parser
        parser = Parser(self.languages["c_sharp"])
        content = file_path.read_text(encoding="utf-8")
        tree = parser.parse(bytes(content, "utf-8"))

        def visit(node):
            # Example: detect Console.WriteLine in production code
            if node.type == "invocation_expression":
                text = node.text.decode("utf-8")
                if "Console.WriteLine" in text:
                    rel_path = file_path.relative_to(project_root)
                    violations.append(Violation(
                        rule_id="csharp_no_console_writeline",
                        message="Use ILogger instead of Console.WriteLine",
                        file=str(rel_path),
                        line=node.start_point[0] + 1,
                        col=node.start_point[1] + 1,
                        severity=Severity.WARN,
                        engine=self.name,
                    ))
            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return violations
```

### Tree-sitter 常用节点类型

#### Rust

| 节点类型 | 说明 |
|---------|------|
| `function_item` | 函数定义 |
| `unsafe_block` | unsafe 块 |
| `visibility_modifier` | 可见性修饰符 (pub) |
| `identifier` | 标识符 |
| `call_expression` | 函数调用 |
| `field_expression` | 字段访问 |
| `line_comment` | 行注释 |

#### C#

| 节点类型 | 说明 |
|---------|------|
| `method_declaration` | 方法定义 |
| `class_declaration` | 类定义 |
| `modifier` | 修饰符 (async, public 等) |
| `identifier` | 标识符 |
| `await_expression` | await 表达式 |
| `return_statement` | return 语句 |
| `null_literal` | null 字面量 |
| `invocation_expression` | 方法调用 |

### 扩展新语言

Tree-sitter 支持 100+ 种语言。添加新语言只需：

```python
# 1. 安装 grammar
pip install tree-sitter-go  # 例如 Go

# 2. 在 TreeSitterEngine._init_languages() 中添加
import tree_sitter_go
self.languages["go"] = Language(tree_sitter_go.language())

# 3. 添加对应的 check 方法
def _check_go_file(self, file_path, project_root):
    ...
```

---

## Spec-chain 引擎：文档阶段一致性

Spec-chain 引擎检查不同阶段文档之间的契约一致性。例如：
- PRD 需求是否都在业务架构中覆盖
- 量化标准中的性能指标是否在 API 设计中满足
- API 文档中的接口是否都在代码中实现

### 配置

在 `.unified-lint/spec-chain.toml` 中定义契约链：

```toml
[[chains]]
source = "specs/prd.md"
target = "specs/biz-arch.md"
rule = "prd_coverage"

[[chains]]
source = "specs/metrics.md"
target = "specs/api.md"
rule = "metrics_api_compliance"
```

### 文档格式

每个阶段的文档使用 YAML frontmatter：

```yaml
---
stage: prd
id: prd-v1
requirements:
  - id: REQ-001
    name: 用户登录
    priority: P0
  - id: REQ-002
    name: 订单管理
    priority: P0
---

# PRD 文档正文
```

### 内置规则

| 规则 | 用途 | 检查内容 |
|------|------|----------|
| `prd_coverage` | PRD 需求覆盖 | 业务架构必须覆盖所有 PRD 需求 |
| `metrics_api_compliance` | API 性能合规 | API 延迟/可用性必须满足量化标准 |
| `api_code_compliance` | 代码实现 | 代码必须实现所有 API 接口 |

### 量化标准格式

```yaml
---
stage: metrics
id: metrics-v1
core_metrics:
  latency_p95_ms: 200      # P95 延迟目标（毫秒）
  latency_p99_ms: 500      # P99 延迟目标
  availability: 99.9       # 可用性目标（百分比）
  error_rate_percent: 0.1  # 错误率目标
important_metrics:
  throughput_qps: 1000     # 吞吐量目标
  concurrency: 500         # 并发数目标
optional_metrics:
  cache_hit_rate_percent: 80
---
```

### E2E 示例

```bash
# 运行所有引擎检查
unified-lint check .

# 输出示例（spec-chain 部分）：
# --- spec-chain ---
#    specs/biz-arch.md:0 prd_coverage: PRD requirement 'REQ-003' not covered
#    specs/api.md:0 metrics_api_compliance: Endpoint /api/v1/orders latency 250ms > 200ms
```

---

## 测试你的规则

### 测试模板

```python
"""Tests for your custom rule."""

import ast
from pathlib import Path
from unified_lint.engines.your_module import check_your_rule


def test_your_rule_detects_violation(tmp_path):
    """Test that violation is detected."""
    # 创建测试文件
    test_file = tmp_path / "test.py"
    test_file.write_text("""
def bad_function(camelCaseParam):
    pass
""")
    
    # 解析 AST
    tree = ast.parse(test_file.read_text())
    
    # 运行规则
    violations = check_your_rule(test_file, tree)
    
    # 验证
    assert len(violations) == 1
    assert "camelCaseParam" in violations[0].message
    assert violations[0].rule_id == "your_rule_id"


def test_your_rule_passes_correct_code(tmp_path):
    """Test that correct code passes."""
    test_file = tmp_path / "test.py"
    test_file.write_text("""
def good_function(snake_case_param):
    pass
""")
    
    tree = ast.parse(test_file.read_text())
    violations = check_your_rule(test_file, tree)
    
    assert len(violations) == 0
```

### 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试文件
pytest tests/test_your_rule.py

# 运行特定测试
pytest tests/test_your_rule.py::test_your_rule_detects_violation

# 显示详细输出
pytest tests/test_your_rule.py -v -s
```

---

## 完整示例：从零编写一条规则

### 需求

检查 Python 函数不超过 50 行，防止函数过长。

### 步骤 1：选择引擎

检查函数长度 → 需要访问函数定义和行号 → **Python AST 引擎**

### 步骤 2：编写规则

创建 `src/unified_lint/engines/max_function_length.py`:

```python
"""Check that functions don't exceed a maximum length."""

import ast
from pathlib import Path
from unified_lint.engines.python_ast import rule, Severity, Violation


MAX_FUNCTION_LINES = 50


@rule(
    "max_function_length",
    Severity.WARN,
    f"Functions should not exceed {MAX_FUNCTION_LINES} lines"
)
def check_max_function_length(path: Path, tree: ast.Module) -> list[Violation]:
    """Check that functions don't exceed maximum length."""
    violations = []
    
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        
        # 计算函数长度
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        function_length = end_line - start_line + 1
        
        if function_length > MAX_FUNCTION_LINES:
            violations.append(
                Violation(
                    rule_id="max_function_length",
                    message=f"Function '{node.name}' is {function_length} lines (max {MAX_FUNCTION_LINES})",
                    file=str(path),
                    line=node.lineno,
                    col=node.col_offset + 1,
                    severity=Severity.WARN,
                    engine="python-ast",
                    fixable=False,
                )
            )
    
    return violations
```

### 步骤 3：编写测试

创建 `tests/test_max_function_length.py`:

```python
"""Tests for max_function_length rule."""

import ast
from pathlib import Path
from unified_lint.engines.max_function_length import check_max_function_length


def test_short_function_passes(tmp_path):
    """Test that short function passes."""
    test_file = tmp_path / "test.py"
    test_file.write_text("""
def short_function():
    x = 1
    y = 2
    return x + y
""")
    
    tree = ast.parse(test_file.read_text())
    violations = check_max_function_length(test_file, tree)
    
    assert len(violations) == 0


def test_long_function_fails(tmp_path):
    """Test that long function fails."""
    test_file = tmp_path / "test.py"
    
    # 生成 60 行的函数
    long_body = "\n".join([f"    x{i} = {i}" for i in range(58)])
    test_file.write_text(f"""
def long_function():
{long_body}
    return x0
""")
    
    tree = ast.parse(test_file.read_text())
    violations = check_max_function_length(test_file, tree)
    
    assert len(violations) == 1
    assert "long_function" in violations[0].message
    assert "60 lines" in violations[0].message
```

### 步骤 4：运行测试

```bash
pytest tests/test_max_function_length.py -v
```

预期输出：
```
test_max_function_length.py::test_short_function_passes PASSED
test_max_function_length.py::test_long_function_fails PASSED
```

### 步骤 5：集成到 unified-lint

编辑 `src/unified_lint/engines/python_ast.py`，添加导入：

```python
from .max_function_length import check_max_function_length
```

规则会自动被 `@rule` 装饰器注册。

### 步骤 6：验证

```bash
cd examples/mario-server
unified-lint check .
```

应该看到新规则的检查结果。

---

## 最佳实践

1. **规则 ID 命名**：使用 snake_case，描述性强（如 `no_hardcoded_password`）
2. **错误消息**：具体说明违规内容和修复建议
3. **测试覆盖**：至少包含正向测试（检出违规）和反向测试（正确代码通过）
4. **Severity 选择**：
   - `ERROR`：必须修复的问题（安全、架构违规）
   - `WARN`：建议修复的问题（代码风格、最佳实践）
5. **文档**：在规则文件中包含 Bad/Good 示例

---

## 常见问题

### Q: 为什么我的 GritQL 规则不工作？

GritQL 的 Python parser 是 Alpha 版本，复杂的函数定义匹配不稳定。对于函数/类级别的检查，改用 Python AST 引擎。

### Q: 如何让规则只检查特定目录？

在规则函数中检查 `path` 参数：

```python
if "api" not in str(path).split("/"):
    return violations  # 只检查 api/ 目录
```

### Q: 如何调试规则？

在规则函数中添加 `print` 语句，然后运行 `unified-lint check . --verbose`。

### Q: 规则检出太多误报怎么办？

添加排除条件，例如：
- 排除特定命名模式
- 排除特定目录
- 排除特定文件

参考 `no_hardcoded_password` 规则的排除逻辑。

---

## 参考资源

- [Python AST 文档](https://docs.python.org/3/library/ast.html)
- [markdown-it-py 文档](https://markdown-it-py.readthedocs.io/)
- [GritQL 语法](https://docs.grit.io/language/syntax)
- [unified-lint 源码](./src/unified_lint/engines/)
