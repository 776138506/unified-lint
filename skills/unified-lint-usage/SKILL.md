---
name: unified-lint-usage
description: "Use the unified-lint CLI to lint a project — code rules + doc rules + architecture rules in one command. Load when the user asks to: 统一 linter / 自定义规则 lint / 代码+文档+架构一起检查 / 写项目级 lint 规则 / 跑 unified-lint / 配置 import-linter / 加 GritQL 规则 / 集成规范链 lint / 扩展开源 linter. Triggers: 'unified-lint', 'unified lint', '统一 linter', '自定义 lint 规则', '代码 lint', '文档 lint', '架构 lint', 'import-linter 配置', 'GritQL 规则', '扩展开源 linter'."
version: 1.0.0
created: 2026-06-12
updated: 2026-06-12
tags: [linter, unified-lint, gritql, import-linter, code-quality, docs-as-code, ci]
---

# unified-lint 使用指南（消费视角）

> 教会 AI：拿到一个项目，如何用 `unified-lint` 给它装上代码/文档/架构统一检查，
> 以及如何给这个工具**写新规则**和**扩展新引擎**。
> 工具本体仓库：https://github.com/776138506/unified-lint
> 开发视角（如何给工具加新引擎/规则）见 `unified-lint-development` skill。

## 何时加载这个 skill

当用户的请求命中以下任一场景时加载：

- 给我的项目加 lint / 统一 linter / 代码+文档一起检查
- 写一条自定义 lint 规则（针对项目级规范）
- 配置架构分层 / 禁止某模块 import 另一个模块
- 集成到 CI / pre-commit / PR 门禁
- 跑 unified-lint / unified-lint check 报错
- 扩展开源 linter / 给 unified-lint 加新引擎 / 加新规则类型
- 用户改了 `.unified-lint/config.toml`、`.importlinter`、`.grit/patterns/*.md`、`.unified-lint/rules/*.py`

不加载的场景：

- 用户问"什么是 linter"（先解释再决定要不要加载）
- 用户在开发 `unified-lint` 工具本身（→ `unified-lint-development` skill）
- 用户问通用 Python/Rust lint（→ 推荐 `ruff`/`clippy`，unified-lint 是补充）

## 第一步：判断项目阶段

| 阶段 | 特征 | 推荐动作 |
|:---|:---|:---|
| 全新项目 | 只有 `pyproject.toml` 或 `package.json`，没 .unified-lint/ | 跑 `unified-lint init .`，接受默认引擎和预置规则 |
| 已有项目，未配 lint | 有代码、有 commit，无 .unified-lint/ | 先跑 `unified-lint init .`，再按需 disable 太严的预置规则 |
| 已有项目，已用 ruff/eslint | 有内置 lint 在跑 | 不要替换，unified-lint 处理自定义规则和文档/架构 |
| 已有部分 .unified-lint/ | 配置文件存在但缺规则 | 看 `unified-lint check .` 输出，按缺失引擎补 |

## 第二步：安装

主包（通过 PyPI 标准安装）：
```
python -m pip install unified-lint
```

按需依赖（按用户的项目语言判断，不要全装）：

| 引擎 | 需要安装的包 |
|:---|:---|
| import-linter（架构） | `import-linter` |
| markdown-ast（文档） | `markdown-it-py` |
| tree-sitter（Rust/C#） | `tree-sitter`, `tree-sitter-rust`, `tree-sitter-c-sharp` |
| GritQL | 需要单独下载 Grit CLI 二进制（约 75MB，不在 PyPI 包里） |

Grit CLI 独立二进制安装方式：

| 平台 | 安装方式 |
|:---|:---|
| Windows | 从 GitHub releases 下载 `grit-x86_64-pc-windows-msvc.tar.gz` 解压后加 PATH |
| Linux | `cargo install --git https://github.com/biomejs/gritql grit` |
| macOS | 同 Linux |

重要：项目 `.gitignore` 必须有 `grit.exe` 和 `grit.tar.gz`（`unified-lint init` 会自动加）。

安装验证：
```
unified-lint --help
unified-lint check .
```

第二条应跑通（可能报违规，但不应该报"missing tool"）。

## 第三步：四命令工作流

### init — 初始化

```
unified-lint init <project-dir>
```

做的事：

1. 检测主语言（pyproject.toml → python, package.json → js, go.mod → go, Cargo.toml → rust）
2. 生成 `.unified-lint/config.toml`
3. 生成 `.importlinter`（按检测到的语言和推断的分层）
4. 复制预置规则到 `.grit/patterns/` 和 `.unified-lint/rules/`
5. 更新 `.gitignore`（加 `grit.exe`、`grit.tar.gz`、缓存目录）

坑点：如果项目已有 `.importlinter`，init 不会覆盖；它会提示你手动合并。

### check — 跑检查

```
unified-lint check .
unified-lint check . --verbose
unified-lint check . --engine gritql
unified-lint check . --severity error
```

退出码（统一约定，可直接做 CI 门禁）：

| Exit | 含义 |
|:---:|:---|
| 0 | ALL PASS |
| 1 | 至少一个 ERROR 违规 |
| 2 | 只有 WARN，无 ERROR |
| 4 | 工具缺失（grit / import-linter 未装） |

### fix — 自动修复

```
unified-lint fix .
```

只对声明了 `fixable=True` 的规则生效。当前预置规则里大部分 fixable=False，需要在写规则时实现修复逻辑。

### rule — 规则管理

```
unified-lint rule list
unified-lint rule list --engine gritql
unified-lint rule show no_hardcoded_password
unified-lint rule add my_rule
```

## 第四步：引擎选择决策树

这是最重要的部分——先看清要查什么，再选引擎。

```
你要检查什么？
│
├─ 简单的赋值模式（如把敏感字段写成字面量）
│   └─→ GritQL  一行 pattern 就够
│
├─ Python 函数/类的精确结构
│   │  （函数签名、返回值、循环内调用、装饰器）
│   └─→ python-ast  100% 准确，GritQL parser 对这些场景 Alpha 不稳
│
├─ Markdown 文档结构
│   │  （frontmatter 字段、断链、heading 层级、代码块语言）
│   └─→ markdown-ast  用 markdown-it-py 解析
│
├─ Rust / C# 代码
│   │  （unsafe 块、pub API、async/await、命名规范）
│   └─→ tree-sitter  通过 tree-sitter-language-pack 解析 AST
│
├─ 文档→代码的一致性
│   │  （PRD 改了但代码没改、API 文档对不上实现、数据模型字段对不上 ORM）
│   └─→ spec-chain  加载 .unified-lint/spec-chain.toml 里定义的 chain
│
└─ 分层 / 禁止 / 独立模块
    │  （api 不可 import infra、模块 A 和 B 必须独立）
    └─→ import-linter  用 .importlinter 声明契约
```

取舍经验法则：

1. 先试 GritQL（写起来最快，约 1 行），跑不通降级到 python-ast（10-30 行）
2. 不要混用——同一条规则要么 GritQL 要么 python-ast，不要两个引擎同时写一遍
3. spec-chain 的代价：要维护 PRD/架构文档的 YAML/JSON 形式，规则才能查
4. import-linter 只查 import 关系，不能查"模块是否用了某个函数"

## 第五步：写自定义规则（三种最常见）

### 场景 A：检测敏感字段字面量赋值 → GritQL

在 `.grit/patterns/no_literal_secret.md`：

```markdown
---
name: no_literal_secret
title: "No literal sensitive assignment"
description: "Read sensitive fields from env or config, never literal strings"
level: error
tags: [security]
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

**GritQL 模式编写要点**：

| 元素 | 含义 | 例子 |
|:---|:---|:---|
| `` `$name = $value` `` | 简单赋值（Python 仅支持这一种） | `` `password = "x"` `` |
| `$x <: r"pattern"` | 字符串字面量正则匹配 | `$name <: r"(?i)password"` |
| `$x <: not r"pattern"` | 负向正则匹配（排除） | `$value <: not r"os\.getenv"` |
| `$...args` | 变长参数 | `` `print($...args)` `` |
| `where { ... }` | 模式守卫 | 多条件组合 |

**GritQL 的边界**（写之前要清楚）：

- Python parser 是 Alpha：函数定义、装饰器、嵌套类都匹配不准
- 字符串内插、复杂表达式匹配不到
- 同一文件多条规则用换行分隔，rule 块用 markdown fence 包

### 场景 B：检测 Python 函数返回裸 dict → python-ast

在 `.unified-lint/rules/no_raw_dict_return.py`：

```python
from pathlib import Path
import ast
from unified_lint.engines.python_ast import rule, Violation, Severity

@rule(
    rule_id="no_raw_dict_return",
    severity=Severity.WARN,
    description="API functions should return a Result wrapper, not raw dict",
)
def check(path: Path, tree: ast.Module) -> list[Violation]:
    violations: list[Violation] = []
    for node in tree.body:           # 只看顶层函数
        if not isinstance(node, ast.FunctionDef):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Dict):
                violations.append(Violation(
                    rule_id="no_raw_dict_return",
                    message=f"Function {node.name} returns raw dict",
                    file=str(path),
                    line=sub.lineno,
                    col=sub.col_offset + 1,
                    severity=Severity.WARN,
                    engine="python-ast",
                    fixable=False,
                ))
    return violations
```

**python-ast 规则编写模板**：

```python
from pathlib import Path
import ast
from unified_lint.engines.python_ast import rule, Violation, Severity

@rule(
    rule_id="<your_rule_id>",          # 必须唯一
    severity=Severity.WARN,             # INFO / WARN / ERROR
    description="<一句话描述>",
)
def check_<your_rule>(path: Path, tree: ast.Module) -> list[Violation]:
    violations: list[Violation] = []
    # 用 ast.walk(tree) 遍历所有节点
    # 或用 tree.body 只看顶层
    for node in ast.walk(tree):
        if isinstance(node, ast.<NodeType>):
            # 构造 Violation
            violations.append(Violation(
                rule_id="<your_rule_id>",
                message="<具体错误信息>",
                file=str(path),
                line=node.lineno,
                col=node.col_offset + 1,
                severity=Severity.WARN,
                engine="python-ast",
                fixable=False,
            ))
    return violations
```

**ast 节点类型速查**：

| 节点 | 含义 | 常用属性 |
|:---|:---|:---|
| `ast.FunctionDef` | 函数定义 | `name`, `args`, `body`, `decorator_list` |
| `ast.AsyncFunctionDef` | 异步函数定义 | 同上 |
| `ast.ClassDef` | 类定义 | `name`, `bases`, `body`, `decorator_list` |
| `ast.Call` | 函数调用 | `func`, `args`, `keywords` |
| `ast.Return` | return 语句 | `value` |
| `ast.Assign` | 赋值 | `targets`, `value` |
| `ast.Constant` | 字面量 | `value`, `kind` (str/int/bool/None) |
| `ast.Name` | 名字引用 | `id` |
| `ast.Attribute` | 属性访问 | `value.attr`, `attr` |
| `ast.ExceptHandler` | except 子句 | `type` (None 即裸 except) |
| `ast.For / ast.While` | 循环 | `body` |

**坑点**：

- 用 `tree.body` 不用 `ast.walk(tree)`：嵌套函数返回 dict 是允许的
- `ast.Constant` 取代了 Python 3.8 之前的 `ast.Num`/`ast.Str`
- 字符串拼接 `a + b` 是 `ast.BinOp`，不是 `ast.Call`
- 装饰器在 `decorator_list`，要先单独判断再走 body

### 场景 C：PRD feature → 代码函数 → spec-chain

在 `.unified-lint/spec-chain.toml`：

```toml
[[chains]]
source = "specs/prd.yaml"
target = "src/"
rule = "feature_implemented"

[chains.params]
feature_field = "features"
code_marker = "def "
```

内置规则 `feature_implemented` 会读取 `specs/prd.yaml` 的 `features` 列表，对每条 feature 在 `src/` 下找包含对应 feature id 的代码标记。

**内置 spec-chain 规则**（v0.5 起）：

| 规则 | 含义 |
|:---|:---|
| `feature_implemented` | PRD 的每个 feature 在代码里有对应标记 |
| `api_endpoint_exists` | API 文档里的 endpoint 在路由里实现 |
| `datamodel_field_used` | 数据模型定义的字段在代码里被使用 |

**自定义 spec-chain 规则（插件机制 v0.5+）**：

```python
# .unified-lint/rules/my_chain_rule.py
from unified_lint.engines.spec_chain import chain_rule, Violation
from typing import Optional

@chain_rule("api_docs_match")
def check(
    source: dict,
    target: dict,
    source_file: str,
    target_file: str,
    params: Optional[dict] = None,
) -> list[Violation]:
    """Verify all API endpoints in source have corresponding routes in target."""
    violations: list[Violation] = []
    # source 字典来自 source 文件（YAML/JSON 已解析）
    # target 字典来自 target 文件或目录扫描结果
    # params 来自 .unified-lint/spec-chain.toml 的 [chains.params]
    return violations
```

引擎自动从 `.unified-lint/rules/*.py` 发现带 `@chain_rule` 装饰器的函数。

### 场景 D：架构分层 → import-linter

`.importlinter`（由 `init` 自动生成，可手动调整）：

```ini
[importlinter]
root_package = myapp

[importlinter:contract:layers]
name = 分层架构依赖规则
type = layers
layers =
    myapp.api
    myapp.infra
    myapp.service
    myapp.domain

[importlinter:contract:no-infra-to-domain]
name = 禁止 infra 直接依赖 domain
type = forbidden
source_modules =
    myapp.infra
forbidden_modules =
    myapp.domain
include_external_packages = true
```

**三种契约类型**：

| 类型 | 用途 | 例子 |
|:---|:---|:---|
| `layers` | 声明层级顺序（上层依赖下层，下层不可依赖上层） | api → service → domain |
| `forbidden` | 禁止特定模块间的 import | infra 不可 import domain |
| `independence` | 声明两个模块互相独立 | billing 模块和 ui 模块互不依赖 |

## 第六步：扩展开源 linter（如何扩展）

### 扩展 1：写一个新规则（最常见）

任何已注册的引擎都可以加新规则。三种方法：

**方法 A：纯 GritQL**（无需写 Python）

新建 `.grit/patterns/<rule_id>.md`，写 YAML frontmatter + grit 代码块。引擎下次 check 自动发现。

**方法 B：python-ast 规则**（需要写 Python）

在 `.unified-lint/rules/<rule_name>.py` 写一个带 `@rule` 装饰器的函数。引擎自动从该目录发现。

**方法 C：spec-chain 插件**（需要写 Python）

在 `.unified-lint/rules/<rule_name>.py` 写一个带 `@chain_rule` 装饰器的函数，并在 `.unified-lint/spec-chain.toml` 引用。

### 扩展 2：写一个新引擎（高级）

新增引擎的标准流程：

1. **实现 `engines/<name>.py`**，继承 `LintEngine` 基类（参见 `src/unified_lint/engines/base.py`）

   ```python
   from unified_lint.engines.base import LintEngine, EngineResult, Violation

   class MyEngine(LintEngine):
       name = "my-engine"
       is_available = lambda self: check_my_dep()  # 检查依赖是否安装

       def check(self, project_root, config) -> EngineResult:
           violations = []
           # 你的检查逻辑
           return EngineResult(engine=self.name, violations=violations)
   ```

2. **在 `runner.py` 的 `get_engines()` 注册**：

   ```python
   def get_engines() -> list[LintEngine]:
       return [
           GritEngine(),
           PythonAstEngine(),
           MyEngine(),  # ← 新增
       ]
   ```

3. **在 `cli.py` 的 `rule_list()` 添加引擎的规则列表**

4. **写测试** `tests/test_<engine>.py`（每条规则正向+反向）

5. **更新 `.unified-lint/config.toml` 模板**（`init` 时生成）

### 扩展 3：自定义配置格式

`.unified-lint/config.toml` 支持任意引擎配置段：

```toml
[engines]
gritql = true
python_ast = true
my_engine = true        # 你的新引擎

[engines.my_engine]
option_a = "value"
option_b = 42

[severity]
override."my_custom_rule" = "error"
```

`runner.load_config()` 会自动解析所有 `[engines.*]` 段，并传给对应引擎的 `check(project_root, config)`。

### 扩展 4：分发插件（团队内部共享规则）

把写好的规则打包成 Python 包，目录结构：

```
my-team-lint-rules/
├── pyproject.toml
└── src/
    └── my_team_rules/
        └── rules/
            ├── no_legacy_import.py
            └── require_docstring.py
```

团队成员 `pip install my-team-lint-rules`，然后在 `.unified-lint/config.toml` 加：

```toml
[plugins]
paths = [".unified-lint/rules", "my_team_rules.rules"]
```

## 第七步：CI 集成（标准 GitHub Actions）

直接给用户一份可复制的 yml：

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

`check .` 退出非 0 即自动 block PR。

## 第八步：故障排查（按错误信息查表）

| 错误信息 | 原因 | 修复 |
|:---|:---|:---|
| `Failed to open cache file` | `.grit/.gritmodules` 不存在 | 跑 `unified-lint init .` 或手动 `grit init`（需要先 `git add -A && git commit`） |
| `Failed to get branch: reference 'refs/heads/main' not found` | git 仓库没有 commit | 先 `git commit` 空仓库再跑 |
| `pattern name must match /^[A-Za-z_][A-Za-z0-9_]*$/` | GritQL 规则名含连字符 | 改名用下划线：`service-ctx-first` → `service_ctx_first` |
| `YAML parse error` in `.grit/patterns/*.md` | frontmatter 的 description 含冒号没加引号 | `description: "你的描述"` |
| import-linter 报 `forbidden` 但外部包未识别 | 没设 `include_external_packages` | 在 `[importlinter:contract:...]` 加 `include_external_packages = true` |
| check 退出码 4 | grit 或 import-linter 没装 | 按第二步安装 |
| check 不报任何违规但你确定有 | 规则没被加载 | `unified-lint rule list` 看是否有你的规则；GritQL 看 `.grit/.gritmodules` 是否有 patterns 目录 |
| markdown-ast 检不到 link/image | link/image 是 inline token 的 children 不是顶层 | 这是引擎内部已处理的；如果是自定义规则，需要递归展平 token（见 `references/markdown-it-py-token-gotcha.md`） |

## 第九步：典型工作流（教 AI 按这个顺序做）

场景："用户说给我的 Python 项目加自定义 lint 检查硬编码敏感字段和禁止 API 层 import domain 层"

```
1. 装包：python -m pip install unified-lint import-linter
2. 初始化：cd my-project && unified-lint init .
3. 看默认规则：unified-lint rule list
4. 试跑一次看现状：unified-lint check .
5. 在测试文件加一条违规（让敏感字段直接写成字面量）
6. 跑检查：unified-lint check .
7. 编辑文件把字面量改为从环境变量读取
8. 重新检查：unified-lint check .
9. 加 CI：写 .github/workflows/lint.yml（参考第七步模板）
10. 提交 .unified-lint/ .importlinter .gitignore .github/
```

## 教 AI 的关键判断

1. 不要替用户装 grit CLI：75MB 二进制，应该让用户自己决定下载方式。告诉用户在哪下载，别替他做。
2. 不要全装所有可选依赖：按用户项目语言判断（Python 项目装 markdown-it-py 就行，不用装 tree-sitter-rust）。
3. GritQL 写规则前先 `grit check --pattern <name>` 验证：不要写完不测就 check 整个项目。
4. CI 里跑两次 check：一次 PR 时（warn 也算 fail），一次 main merge 后（只算 error），平衡严格度和实用度。
5. 看到 import-linter 报"forbidden"，先看是不是真的需要禁止：有时候是初始化时生成的规则过于激进，按需 disable。
6. 写新引擎前先看 `src/unified_lint/engines/base.py` 的 `LintEngine` 接口——三个方法 `name` / `is_available` / `check`，缺一不可。
7. 规则 ID 必须全局唯一：跨引擎也不能重复，会被 Runner 覆盖。建议用 `<engine>_<subject>` 命名（如 `gritql_no_hardcoded_secret`）。
8. 写自定义规则先在 `.unified-lint/rules/` 单文件测试，再考虑打包成团队插件。
9. **发布前必跑隐私扫描**：本机路径 / 邮箱 / token / 内网 IP 四类。复制 skill 文件时尤其要扫，因为源文件可能含作者本机路径。
10. **git history 残留不等于文件层泄漏**：GitHub UI 默认显示当前 main 内容，普通浏览看不到旧 commit 里的泄漏。但 `git clone + git log -p` 能看到。彻底清理需要 force push。

## 发布前必做：隐私与历史审查

发布一个用了 unified-lint 的项目到 GitHub 前，必须扫描四类泄漏：

```bash
# 1. 本机路径（用户名/家目录）
grep -rE "<local-user>|C:\\\\Users|/c/Users|/Users/[^/]+" --include="*.md" --include="*.py" --include="*.toml" .

# 2. 邮箱 / 账号
grep -rEi "@(qq|163|gmail|outlook)\\.com|user[nN]ame" .

# 3. API key / token / 密码（排除故意示例）
grep -rE "(api[_-]?key|token|password)\\s*=\\s*['\"][A-Za-z0-9]{16,}" --include="*.py" .

# 4. 内网 IP / 域名
grep -rE "10\\.|192\\.168\\.|172\\.(1[6-9]|2[0-9]|3[01])\\.|\\.local|\\.internal" .
```

替换规则：

| 泄漏类型 | 替换为 |
|:---|:---|
| 本机绝对路径 | `<repo-root>` 或相对路径 |
| 邮箱 / QQ | 删掉或换成占位符 `<your-email>` |
| 真 token / API key | 立刻 revoke + 用 `git filter-repo` 或 BFG 清理历史 |
| 内网 IP / 域名 | RFC 5737 TEST-NET-1 `192.0.2.1` |

### 复制 skill 文件时的二次污染

如果把 `~/.hermes/skills/` 下的 SKILL.md 复制到仓库 `skills/`，**源文件本身可能含本机路径**（写 skill 时粘进去的）。复制后**必须重新扫描**：

```bash
grep -rE "<local-user>|C:\\\\Users|/c/Users" skills/
```

发现就改：把 `C:\Users\<local-user>\...` 改为 `<repo-root>` 或 `examples/mario-server/` 等相对路径。

### git history 残留

即使当前 main 的文件层干净，git history 里某个旧 commit 可能仍含泄漏内容：

```bash
curl https://raw.githubusercontent.com/<owner>/<repo>/<old-sha>/README.md | grep <local-user>
```

彻底清理需要 force push（被 harness 拦截时见 `github-publish-restricted` skill 的 git data API 工作流）。

## SEE ALSO

- `unified-lint-development` skill — 给统一 linter 加新引擎/新规则（开发视角）
- `unified-custom-linter` skill — 整体架构哲学（GritQL + import-linter + 薄编排层）
- 工具仓库: https://github.com/776138506/unified-lint