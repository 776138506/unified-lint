---
name: unified-lint-development
description: "unified-lint 统一 Linter 开发工作流。六引擎架构：GritQL (简单模式) + python-ast (精确 Python AST) + markdown-ast (精确文档分析) + tree-sitter (Rust/C#) + spec-chain (文档阶段一致性+插件) + import-linter (架构依赖)。typer CLI + 引擎抽象层 + Runner 聚合器。设计哲学：文档即代码，用一个支持自定义规则的增强 Linter 同时审查代码、文档、架构。"
version: 0.6.0
created: 2026-06-10
updated: 2026-06-12
---

# unified-lint 开发技能

## 何时加载这个 skill

当用户的请求命中以下任一场景时加载：

- 给 unified-lint 工具**加新引擎**（实现 `LintEngine` 基类）
- 给 unified-lint **加新规则**（GritQL pattern / python-ast 函数 / spec-chain 插件）
- 排查统一 linter 内部问题（runner、engine、rule 注册机制）
- 修改统一 linter 的架构或扩展点
- 写自定义 spec-chain 规则（插件机制）
- 实现 engine 的 `fix()` 方法（自动修复逻辑）

不加载的场景：

- 用 unified-lint 检查项目 → 用 `unified-lint-usage`
- 想了解整体架构设计哲学 → 用 `unified-custom-linter`
- 用 ruff / pylint / eslint 等通用 linter（不是 unified-lint 相关）

## 设计哲学

"文档即代码" — 文档应享受代码的全部工程纪律（lint/测试/CI/自动修复）。
一个统一 Linter，多种规则源，统一配置、统一输出、统一 CI 门禁。

底层组合现有工具（Grit CLI / import-linter / Python ast / markdown-it-py），不重新造轮子。
架构哲学：吸收多工具精华，把代码 / 文档 / 架构 / 规范链合并到一个 lint 入口。

## 架构（v0.6.0 六引擎）

```
unified-lint (typer CLI, 4 commands: init/check/fix/rule)
├── engines/base.py          ← LintEngine ABC (check/fix/is_available)
├── engines/grit.py          ← GritEngine: 调用 grit CLI (简单赋值模式)
├── engines/python_ast.py    ← PythonAstEngine: Python ast 模块 (精确函数/类分析)
├── engines/markdown_ast.py  ← MarkdownAstEngine: markdown-it-py (精确文档分析)
├── engines/tree_sitter.py   ← TreeSitterEngine: tree-sitter (Rust/C# AST)
├── engines/spec_chain.py    ← SpecChainEngine: 文档阶段一致性 + 插件机制
├── engines/import_linter.py ← ImportLinterEngine: 调用 lint-imports (架构依赖)
├── runner.py                ← 聚合执行 + 统一退出码
├── installer.py             ← init: 检测语言/安装依赖/生成配置/复制规则
└── rules/registry.py        ← 规则发现 + 6 条预置 GritQL 规则
```

**六引擎分工**：
- GritQL：简单赋值模式匹配（`$name = $value` 等）
- python-ast：精确 AST 分析（函数签名、返回值、循环内查询、硬编码密钥）
- markdown-ast：精确文档分析（frontmatter、断链、heading、代码块、图片）
- tree-sitter：Rust/C# 代码分析（unsafe、pub API、async/await、命名规范）
- spec-chain：文档阶段一致性（PRD→架构→API→代码）+ 自定义插件
- import-linter：架构层级依赖约束（layers/forbidden/independence）

引擎插件化：新增引擎只需实现 LintEngine 基类 + 在 runner.py 的 get_engines() 注册。

## 规则清单（16 条）

### GritQL (6 条)
| 规则 | severity | 说明 |
|:---|:---|:---|
| no_hardcoded_password | error | 排除 os.getenv/config/空字符串 |
| service_ctx_first | warn | Service 方法第一个参数必须是 ctx |
| api_result_wrapper | error | API 函数不能返回裸 dict/list |
| doc_frontmatter | warn | 文档必须有 frontmatter |
| no_bare_except | warn | 禁止裸 except |
| no_n_plus_one | error | 禁止循环内 SELECT |

### python-ast (5 条)
| 规则 | severity | 说明 |
|:---|:---|:---|
| service_ctx_first | warn | AST 精确版，检查 *Service 结尾类 |
| api_result_wrapper | error | 只检查顶层函数，排除 Result 类方法 |
| no_bare_except | warn | ast.ExceptHandler.type is None |
| no_hardcoded_secret | error | 排除 os.getenv/空字符串/安全调用 |
| no_n_plus_one | error | for 循环内的 execute("SELECT...") |

### markdown-ast (5 条)
| 规则 | severity | 说明 |
|:---|:---|:---|
| doc_frontmatter_fields | error | 验证 frontmatter 必填字段 (last_updated) |
| doc_broken_links | error | 内部链接必须指向存在的文件 |
| doc_heading_structure | warn | heading 层级不能跳级 (h1→h3) |
| doc_code_block_lang | warn | 代码块必须指定语言标记 |
| doc_image_alt | warn | 图片必须有 alt 文本 |

## 关键设计决策

1. **编排层 + 安装器 + 规则库**（不是独立 binary，不重新造轮子）
2. **规则分散在各工具原生格式 + 统一入口自动发现**
3. **架构规则抽象层**：arch.toml（统一格式）→ 转换为各引擎原生格式
4. **GritQL 做简单模式，复杂规则用 python-ast / markdown-ast**（GritQL parser Alpha 限制）

## 新增引擎的标准流程

1. 实现 `engines/<name>.py`，继承 `LintEngine`
2. 实现 `check(project_root, config)` 返回 `EngineResult`
3. 用 `@rule` 装饰器注册规则
4. 在 `runner.py` 的 `get_engines()` 注册引擎实例
5. 在 `cli.py` 的 `rule_list()` 添加引擎的 `get_rules()`
6. 写 `tests/test_<name>.py`（每条规则正向+反向）

## python-ast 规则编写模板

```python
@rule("rule_id", Severity.ERROR, "Description")
def check_my_rule(path: Path, tree: ast.Module) -> list[Violation]:
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            violations.append(Violation(
                rule_id="rule_id", message="具体错误信息",
                file=str(path), line=node.lineno, col=node.col_offset + 1,
                severity=Severity.ERROR, engine="python-ast", fixable=False,
            ))
    return violations
```

## 已知坑点（Pitfalls）

### markdown-it-py token 结构（CRITICAL）

**link_open 和 image 是 inline token 的 CHILDREN，不是顶层 token！**

```
tokens = md.parse(content)
# 顶层: heading_open, inline, heading_close, paragraph_open, inline, ...
# inline.children: link_open, text, link_close / image, ...
```

引擎必须**递归展平 token 树**才能找到 link_open / image：

```python
token_dicts = []
def collect_tokens(tok_list):
    for tok in tok_list:
        token_dicts.append({...})
        if tok.children:
            collect_tokens(tok.children)
collect_tokens(tokens)
```

测试中也要用同样的展平逻辑，否则 link/image 规则永远匹配不到。

### GritQL 相关

- **Python parser 是 Alpha**：函数定义完全不匹配，只有简单赋值可靠
- **Pattern name 禁止 hyphen**：必须用 underscore
- **`register_diagnostic` 是 Biome 专有**：standalone Grit CLI 不支持
- **grit check 需要 git 仓库**：必须先 `git init && git commit`
- **GritEngine._find_bin() 用相对路径**：`Path("grit.exe")` 相对于 cwd

### python-ast 相关

- **api_result_wrapper 只检查顶层函数**：用 `tree.body` 而非 `ast.walk(tree)`
- **Result 类方法（to_dict 等）必须排除**：它们合法返回 dict
- **no_hardcoded_secret 排除安全赋值**：os.getenv/os.environ/config.*/settings.*/None/空字符串
- **service_ctx_first 只检查 *Service 结尾的类**

### import-linter 相关

- **`include_external_packages=True`**：forbidden_modules 包含外部包时必须设
- **root_package 必须匹配实际目录结构**

### Runner 退出码

- **ERROR 覆盖 WARN**：聚合时用 min(severity) 而非 max
- **missing-tool (exit 4) 是最高优先级**

### 发布到 GitHub 前的 .gitignore 审计（2026-06-12 教训）

**问题**：unified-lint 第一次 push 时 GH 报 advisory "File grit-x86_64-pc-windows-msvc/grit.exe is 75.45 MB"，因为工具开发时把 grit CLI binary 直接 `git add` 进仓库了，79MB grit.exe + 19MB grit.tar.gz 全在 tracking 里。

**发布前必做清单**：

1. **审计被 tracking 的大文件**：
   ```bash
   git ls-files | xargs -I{} sh -c 'echo "$(git cat-file -s $(git rev-parse HEAD:{}) 2>/dev/null) {}"' | sort -rn | head -20
   ```
   任何 >1MB 的非必要二进制（binary/压缩包/build artifact）都要从 tracking 移除。

2. **从 tracking 移除（保留本地文件）**：
   ```bash
   git rm --cached grit.exe grit.tar.gz grit-x86_64-pc-windows-msvc/grit.exe
   ```
   注意 `--cached`：只取消 tracking，不删本地文件。空目录会被一并清理。

3. **升级 .gitignore**（unified-lint 的最终版）：
   ```
   # Grit CLI binary (download separately, see README)
   grit.exe
   grit.tar.gz
   grit-x86_64-pc-windows-msvc/

   # Grit internal cache (keep .grit/patterns/ tracked)
   .grit/.gritmodules
   .grit/modules/

   # Python / venv / caches
   __pycache__/  *.pyc  *.egg-info/  dist/  build/
   .venv/  venv/  env/  ENV/
   .pytest_cache/  .import_linter_cache/  .coverage  htmlcov/
   ```
   **关键陷阱**：`.grit/` 整体不能忽略，必须保留 `.grit/patterns/` 的 GritQL 规则 tracking。只排除 `.grit/.gritmodules` 和 `.grit/modules/` 这两个缓存目录。

4. **README 必须写明 grit 二进制怎么装**（用户在 Windows 上单独下载 tarball 解压）：
   ```
   ## 安装
   1. pip install unified-lint
   2. 下载 grit CLI: https://github.com/biomejs/gritql/releases
      解压到 PATH 或项目根目录的 grit.exe
   ```
   把 binary 排除出仓是正确选择，但必须告诉用户怎么拿。

5. **子模块示例的 dirty 状态不影响 push**：
   - `examples/mario-server` 是 git submodule，内部可能 working tree dirty
   - 父仓库的 `git push` 不会因为子模块 dirty 而失败（除非子模块 HEAD 变了）
   - 不必为了发布把示例项目重置

**单次发布工作流**（验证过）：
```bash
cd <repo-root>
git rm --cached grit.exe grit.tar.gz
git rm --cached grit-x86_64-pc-windows-msvc/grit.exe   # 空目录一起清
# 升级 .gitignore
git add -A
git commit -m "chore: clean up repo for public release"
gh repo create unified-lint --public --description "..." \
  --source . --remote origin --push
```

**GH advisory warning 不是 blocker**：即使 push 时报 "Large files detected"，只要 commit 历史里没真正的大文件对象，仓库就健康。warning 是 advisory，push 仍然成功。但要在 README 里写清楚 grit 怎么单独装。

## E2E 测试流程

```
1. 创建测试项目（4层 Python 项目 + docs/）
2. 故意植入违规（代码违规 + 文档违规 + 架构违规）
3. cd project && unified-lint check .
4. 验证：检出所有植入的违规 + 退出码 = 1
5. 修复违规 → 重新 check → 验证 ALL PASS + 退出码 = 0
6. 改进误报的规则 → 重新验证
```

## 项目位置

```
工具本体:  <repo-root>\
示例项目:  <repo-root>\examples\mario-server\
Grit CLI:  <repo-root>\grit.exe
```

## 测试统计

```
tests/test_core.py:         5 tests (engine/result/runner 基础)
tests/test_python_ast.py:  11 tests (5 条规则 × 正向+反向 + 1 额外)
tests/test_markdown_ast.py: 10 tests (5 条规则 × 正向+反向)
Total: 26 tests, all passing
```

## 版本历史

- v0.1 (2026-06-11): CLI + Grit + import-linter + 6 预置规则
- v0.2 (2026-06-11): python-ast 引擎 + 5 条精确规则 + 11 测试
- v0.3 (2026-06-11): tree-sitter 引擎 (Rust/C#) + 7 条规则 + 8 测试
- v0.4 (2026-06-11): spec-chain 引擎 (文档阶段一致性) + 3 条规则 + 4 测试
- v0.5 (2026-06-11): spec-chain 插件机制 + params 支持 + 3 插件测试
- v0.6 (2026-06-12): YAML 规范体系设计 (12 阶段文件 + 扩展性设计)
- v0.2 (2026-06-11): python-ast 引擎 + 5 条精确规则 + 16 测试
- v0.3 (2026-06-11): markdown-ast 引擎 + 5 条文档规则 + 26 测试
- v0.4 (next): pre-commit hook + semgrep 引擎备选 + 规则市场

## Spec-chain 插件机制（v0.5.0）

插件自动从 `.unified-lint/rules/` 目录加载，通过 `@chain_rule` 装饰器注册。

### 插件规则写法

```python
# .unified-lint/rules/my_rule.py
from unified_lint.engines.spec_chain import chain_rule, Violation, Severity
from typing import Optional

@chain_rule("my_rule_id")
def check_my_rule(
    source: dict, target: dict, source_file: str, target_file: str,
    params: Optional[dict] = None
) -> list[Violation]:
    """Rule description."""
    violations = []
    # Custom logic
    return violations
```

### 配置引用

```toml
# .unified-lint/spec-chain.toml
[[chains]]
source = "specs/design.md"
target = "src/"
rule = "my_rule_id"    # 自动从 rules/ 加载

[chains.params]
threshold = 100        # 传递给插件的参数
```

### 已知坑点

- 内置规则必须支持 `params` 参数（Optional[dict]），否则带参数的配置会报错
- 插件加载失败会打印警告但不中断执行
- 规则函数必须返回 `list[Violation]`，不能返回其他类型

## 用户设计偏好（重要）

用户明确表达的设计原则：

1. **AI 写规范，不是人写** — 人说意图，AI 生成结构化 YAML，人审批
2. **结构化存储 + 渐进式披露** — YAML 字段有类型，AI 按需检索
3. **审查是独立项目** — unified-lint 做一致性检查，规范平台做格式/结构审查
4. **不要混合方案** — 插件机制比配置+代码混合更清晰
5. **字段保留扩展性** — `x_*` 前缀支持任意扩展

详细设计见 `references/yaml-spec-system-design.md`。

## YAML Spec System Design (v0.6.0)

unified-lint is evolving into a broader **spec-platform** that uses YAML to replace traditional project documents.

**Core Design**:
- Directory structure = human-readable hierarchy (tree)
- File internal fields = logical relationships (network topology)
- PRD is root, everything else derives from it
- Each object is self-contained (all info as fields, not separate files)
- Development logs, constraints, prompts are FIELDS within objects

**Key References**:
- `references/yaml-spec-system-design.md` — complete design principles
- `references/yaml-spec-pitfalls.md` — common mistakes to avoid

**User Preference**: YAML is primarily for AI, not humans. AI generates content, code enforces structure.

## 相关 Skills

- `unified-lint-usage` — 消费视角（怎么用 unified-lint 检查项目）
- `unified-custom-linter` — 架构哲学（GritQL + import-linter + 薄编排层的设计思路）

## Support Files

- `references/markdown-it-py-token-gotcha.md` — token 展平问题的详细分析和解决方案
- `references/gritql-working-patterns.md` — GritQL 可靠匹配的模式清单

## Skill 文件发布到仓库

unified-lint 项目有三个 skill（`unified-custom-linter` / `unified-lint-development` / `unified-lint-usage`），用户经常希望把这些 skill 一起发布到仓库，让别人 clone 后能直接用。

### 三 audience 的 skill 分类

| Skill | Audience | 触发场景 |
|:---|:---|:---|
| `unified-lint-usage` | 消费方（用工具的人） | "怎么给我的项目加 lint"、"跑 unified-lint" |
| `unified-lint-development` | 开发方（贡献代码的人） | "怎么给工具加新引擎"、"怎么写新规则" |
| `unified-custom-linter` | 设计方（理解架构的人） | "为什么用 GritQL + import-linter"、"架构哲学" |

每个 skill 的 SKILL.md 顶部 description 必须包含清晰触发词，让 agent 框架能正确路由。三个 skill 互相独立、不重复，按 audience 切分。

### 仓库内标准结构

```
skills/
├── unified-custom-linter/
│   ├── SKILL.md
│   └── references/
│       ├── gritql-python-recipes.md
│       └── tool-landscape.md
├── unified-lint-development/
│   ├── SKILL.md
│   └── references/
│       ├── gritql-working-patterns.md
│       ├── import-linter-config.md
│       ├── markdown-it-py-token-gotcha.md
│       ├── yaml-spec-pitfalls.md
│       └── yaml-spec-system-design.md
└── unified-lint-usage/
    └── SKILL.md
```

### 迁移步骤

1. **复制**：`cp -r ~/.hermes/skills/software-development/<name>/ skills/<name>/`（保留 references/ 子目录）
2. **扫描 + 修复**：源文件本身可能含作者本机路径（如 `C:\Users\<local-user>\...`），必须 grep 替换为占位符
3. **README 加 Skills 索引段**：表格列出三个 skill + 触发词 + 路径 + 集成命令
4. **commit + push**

### 集成到其他 agent

```bash
# Hermes
cp -r skills/<name> ~/.hermes/skills/software-development/

# Claude Code
cp -r skills/<name> .claude/skills/
```

### 坑点

- SKILL.md 的 description 含触发词，必须保持准确，否则 agent 不会加载
- references/ 子目录里的相对路径要保持有效（不要写绝对路径）
- 复制后必须 `git ls-files | grep skills/` 检查所有文件都跟踪了（references 容易漏）
