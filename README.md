# unified-lint

> 一个统一入口、六种引擎、一种配置与退出码。
> 代码规则 + 文档规则 + 架构规则 + 规范链 + 自定义 AST 全部合并。

```
$ unified-lint check .
[1/6] GritQL (code)        3 violations   (no_hardcoded_password, ...)
[2/6] python-ast           2 violations   (api_result_wrapper, ...)
[3/6] markdown-ast         1 violation    (doc_broken_links)
[4/6] tree-sitter          0 violations
[5/6] spec-chain           0 violations   (PRD → architecture → code consistent)
[6/6] import-linter        1 violation    (infra → domain forbidden)
FAILED - errors found (exit 1)
```

## 为什么需要它

代码 lint 已经成熟（ruff、eslint），文档 lint 散落各处（markdownlint、各种 ad-hoc 脚本），架构约束靠 PR review 人工执行。规范一致性问题（PRD 改了但代码没改、架构图改了但 API 没改）几乎完全没人查。

它们都解决同一个工程纪律问题，但用三套工具、跑三遍、读三份报告、CI 里写三段门禁。

`unified-lint` 把这些合并成一个入口：

- 一种配置（`.unified-lint/config.toml`）
- 一种输出（rich 表格 + JSON）
- 一种退出码（0 PASS / 1 ERROR / 2 WARN / 4 MISSING_TOOL）
- 一个 CLI（`unified-lint init / check / fix / rule`）
- 一个规则生态（你用任何引擎写规则都行）

## 六引擎架构

```
                      unified-lint (typer CLI)
                              │
              ┌───────────────┼───────────────┐
              │               │               │
         简单模式          精确 AST         架构 & 链
              │               │               │
        ┌─────┴─────┐    ┌────┴────┐    ┌─────┴─────┐
        │ GritQL    │    │ python  │    │ import-   │
        │ (代码+    │    │ -ast    │    │ linter    │
        │  文档)    │    │         │    │ (分层)    │
        └───────────┘    │ markdown│    │           │
                         │ -ast    │    │ spec-chain│
                         │         │    │ (PRD→code)│
                         │ tree-   │    └───────────┘
                         │ sitter  │
                         │ (Rust/  │
                         │  C#)    │
                         └─────────┘

引擎选择决策：
  简单赋值匹配？           → GritQL
  Python 精确 AST？        → python-ast
  Markdown 文档结构？      → markdown-ast
  Rust / C# 代码？         → tree-sitter
  文档→代码一致性？        → spec-chain
  分层 / 禁止 / 独立模块？ → import-linter
```

每个引擎实现同一个接口（`LintEngine.check() → EngineResult`）。新增引擎只需写一个 Python 文件 + 在 `runner.get_engines()` 注册。

## 安装

主包：
```
pip install unified-lint
```

按需依赖（按项目语言判断，不要全装）：

| 引擎 | 包 |
|:---|:---|
| import-linter（架构） | `import-linter` |
| markdown-ast（文档） | `markdown-it-py` |
| tree-sitter（Rust/C#） | `tree-sitter`, `tree-sitter-rust`, `tree-sitter-c-sharp` |

GritQL 引擎需要单独的 Grit CLI 二进制（约 75MB，不在 pip 包里）：

| 平台 | 安装方式 |
|:---|:---|
| Windows | 从 GitHub releases 下载 `grit-x86_64-pc-windows-msvc.tar.gz` 解压后加 PATH |
| Linux | `cargo install --git https://github.com/biomejs/gritql grit` |
| macOS | 同 Linux |

项目 `.gitignore` 必须包含 `grit.exe` 和 `grit.tar.gz`（`unified-lint init` 会自动加）。

从源码安装：

```
git clone https://github.com/776138506/unified-lint
cd unified-lint
pip install -e .
```

## 快速开始

```
# 1. 生成配置 + 预置规则
cd my-project
unified-lint init .

# 2. 故意植入一个违规看效果
echo 'db_password = "literal-string"' >> src/auth.py

# 3. 跑检查
unified-lint check .
# → [1/6] GritQL (code)  1 violation  no_hardcoded_password @ src/auth.py:1

# 4. 修复后改成从环境变量读取
# 5. 重新跑检查
unified-lint check .
# → ALL PASS
```

## CLI 命令

| 命令 | 说明 |
|:---|:---|
| `unified-lint init <dir>` | 检测语言、安装依赖、生成 `.unified-lint/`、复制预置规则 |
| `unified-lint check <dir>` | 跑所有引擎，返回统一退出码 |
| `unified-lint fix <dir>`   | 对 fixable 规则执行自动修复 |
| `unified-lint rule list`   | 列出所有可用规则 |
| `unified-lint rule show <id>` | 显示某条规则的详细定义 |
| `unified-lint rule add <id>` | 添加一条新规则到项目 |

`check` 退出码：

| Exit | 含义 |
|:---:|:---|
| 0 | ALL PASS |
| 1 | 至少一个 ERROR 违规 |
| 2 | 只有 WARN，无 ERROR |
| 4 | 工具缺失，需要安装 |

## 引擎选择指南

| 你的场景 | 用这个引擎 | 例子 |
|:---|:---|:---|
| 检测敏感字段字面量赋值 | GritQL | `no_hardcoded_password` |
| 检测 Python 函数返回值类型 | python-ast | `api_result_wrapper`（排除 Result 类） |
| 检测 Markdown frontmatter 缺字段 | markdown-ast | `doc_frontmatter_fields` |
| 检测 Rust `unsafe` 块 / `pub` API | tree-sitter | `rust_unsafe_block` |
| 检测 PRD 改了但代码没改 | spec-chain | `prd_feature_implemented` |
| 检测 `infra` import 了 `domain` | import-linter | `no-infra-to-domain` |

**GritQL vs python-ast 的取舍**：
- GritQL 写起来快（一行模式），但 Python parser 是 Alpha，复杂结构（函数定义、装饰器、嵌套类）匹配不准
- python-ast 写起来长（要 `ast.walk` 遍历节点），但精确且 100% 可靠
- 经验：先用 GritQL 试，写出 pattern 跑不通就降级到 python-ast

## 写自定义规则

### GritQL 规则（`.grit/patterns/<name>.md`）

```markdown
---
name: no_literal_secret
title: "No literal sensitive assignment"
description: "Use env or config, never literal strings"
level: error
tags:
  - security
---

```grit
language python

`$name = $value` where {
  $name <: r"(?i)password|passwd|pwd|secret",
  $value <: not r"os\.getenv",
  $value <: not r"^None$",
  $value <: not r'^""$',
}
```
```

**坑点**：`register_diagnostic` 是 Biome 扩展，standalone Grit CLI 不支持。standalone Grit 直接用模式匹配做诊断输出。

### python-ast 规则

```python
# .unified-lint/rules/no_raw_dict_return.py
from pathlib import Path
import ast
from unified_lint.engines.python_ast import rule, Violation, Severity

@rule(
    rule_id="no_raw_dict_return",
    severity=Severity.WARN,
    description="API functions should return a Result wrapper, not raw dict",
)
def check(path: Path, tree: ast.Module) -> list[Violation]:
    violations = []
    for node in tree.body:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Dict):
                violations.append(Violation(
                    rule_id="no_raw_dict_return",
                    message=f"Function {node.name} returns raw dict",
                    file=str(path), line=sub.lineno, col=sub.col_offset + 1,
                    severity=Severity.WARN, engine="python-ast", fixable=False,
                ))
    return violations
```

### spec-chain 规则（文档→代码一致性）

```toml
# .unified-lint/spec-chain.toml
[[chains]]
source = "specs/prd.yaml"
target = "src/"
rule = "feature_implemented"

[chains.params]
feature_field = "features"
code_marker = "def "
```

spec-chain 内置三条规则：`feature_implemented` / `api_endpoint_exists` / `datamodel_field_used`，并支持插件机制。

## 配置文件

`.unified-lint/config.toml`：

```toml
[project]
root = "."
name = "my-project"

[engines]
gritql = true
python_ast = true
markdown_ast = true
tree_sitter = true
spec_chain = true
import_linter = true

[severity]
# 自定义严重级别覆盖（默认用规则定义的级别）
override."no_print_in_prod" = "error"
```

`.importlinter` 由 `init` 自动生成，包含基础分层契约。

## CI 集成

```yaml
# .github/workflows/lint.yml
name: unified-lint
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - name: Install Python deps
        run: python -m pip install unified-lint import-linter markdown-it-py
      - name: Install Grit CLI
        run: |
          curl -L -o /tmp/grit.tar.gz \
            https://github.com/biomejs/gritql/releases/download/v0.1.0-alpha.1743007075/grit-x86_64-unknown-linux-gnu.tar.gz
          tar xzf /tmp/grit.tar.gz -C /tmp/
          mv /tmp/grit-*/grit /usr/local/bin/
          chmod +x /usr/local/bin/grit
      - name: Run lint
        run: unified-lint check .
```

`check .` 退出非 0 自动 block PR 合并。

## 示例项目

`examples/mario-server/` 是一个完整 demo：

- 四层 Python 项目（api/service/infra/domain）
- 故意植入违规代码（`*_buggy.py` 文件）
- 故意植入违规文档
- 自带 `.unified-lint/` 配置 + `.importlinter` 架构契约

```bash
cd examples/mario-server
unified-lint check .
# 预期：检出所有 *_buggy.py 的违规 + 缺 frontmatter 的文档 + 架构分层违规
```

## 跟其他工具的关系

| 工具 | 关系 |
|:---|:---|
| `ruff` / `pylint` / `eslint` | 处理内置规则，unified-lint 处理自定义规则——**互补不冲突** |
| `MegaLinter` | 是 linter 聚合器，unified-lint 是统一引擎 |
| `Biome v2 + GritQL plugin` | 只覆盖 JS/TS，unified-lint 覆盖多语言 |
| `doc-gov` | 思想已被吸收进 spec-chain 引擎 |
| `Structure101` / `dependency-cruiser` | 商业或 JS 专用，统一架构层用 import-linter |

**推荐组合**：`ruff`（内置规则）+ `unified-lint`（自定义规则 + 文档 + 架构）。

## 已知坑点

1. **GritQL Python parser 是 Alpha**：函数定义匹配不准，复杂规则降级到 python-ast
2. **grit CLI 二进制约 75MB**：必须从 GitHub releases 下载，不在 pip 包里；项目 `.gitignore` 必须排除 `grit.exe`
3. **markdown-it-py 的 link/image token 是 inline children 不是顶层**：markdown-ast 引擎内部已递归展平，写自定义规则时记得同样处理
4. **import-linter 的 forbidden_modules 包含外部包**：必须设 `include_external_packages=True`
5. **Runner 退出码聚合**：ERROR 覆盖 WARN，用 `min(severity)` 而非 `max`

## 开发本工具

详见 `unified-lint-development` skill（开发工作流、引擎抽象层、插件机制）。

## Skills

仓库自带三个 agent skill 定义，位于 [skills/](skills/)：

| Skill | 视角 | 用途 |
|:---|:---|:---|
| [unified-lint-usage/SKILL.md](skills/unified-lint-usage/SKILL.md) | 消费视角 | 怎么用 unified-lint 给项目加代码/文档/架构检查 |
| [unified-lint-development/SKILL.md](skills/unified-lint-development/SKILL.md) | 开发视角 | 怎么给 unified-lint 加新引擎/新规则 |
| [unified-custom-linter/SKILL.md](skills/unified-custom-linter/SKILL.md) | 架构哲学 | GritQL + import-linter + 薄编排层的设计思路 |

每个 skill 目录结构：



集成到 agent：



## 项目链接

仓库: https://github.com/776138506/unified-lint
示例: `examples/mario-server/`（完整的 4 层 Python 项目 + 故意植入的违规代码）

## License

MIT