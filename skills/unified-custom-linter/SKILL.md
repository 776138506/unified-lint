---
name: unified-custom-linter
description: "统一自定义 Linter 架构 — GritQL(代码+文档规则) + import-linter(架构规则) + 薄编排层。将代码规范、文档规范、架构约束统一到一个 lint 入口。触发词：自定义 linter、统一 linter、GritQL、import-linter、架构检查、代码规范自动化、文档即代码"
version: 1.0.0
created: 2026-06-10
updated: 2026-06-10
tags: [linter, architecture, gritql, import-linter, custom-rules, docs-as-code]
---

# Unified Custom Linter

> 用户哲学："我们最后只需要一个自定义 rule 的增强 linter"
> "文档即代码，linter 可以自定义 rule 像审查代码一样审查文档"

## 何时加载这个 skill

当用户的请求命中以下任一场景时加载：

- 评估"统一 linter 想法"是否可行 / 调研类似架构
- 选择 GritQL vs import-linter vs 其他方案的取舍
- 想了解 unified-lint 的整体设计理念（为什么 GritQL + import-linter + 薄编排层）
- 对比 unified-lint 与 MegaLinter / Biome / ESLint 的差异
- 写"统一 lint"工具的架构决策（怎么把多类检查合并到一个入口）

不加载的场景：

- 用 unified-lint 检查项目 → 用 `unified-lint-usage`
- 给 unified-lint 加新引擎或规则 → 用 `unified-lint-development`
- 用 ruff / pylint / eslint 等通用 linter（不是统一 linter）

## 1. 核心理念

将三层检查统一到一个入口：

```
统一 Lint 入口 (lint.py)
  ├── GritQL 代码规则 → AST 模式匹配
  ├── GritQL 文档规则 → Markdown/JSON/YAML 结构检查
  └── import-linter    → Python 分层架构依赖约束
```

不需要"代码 Linter + 文档 Linter + 架构 Linter"三套工具。一个入口，多种规则源，统一的配置、输出、CI 门禁。

## 2. 工具选型决策

| 层 | 工具 | 选择理由 |
|:---|:---|:---|
| 代码自定义规则 | Grit CLI + GritQL | 14 语言 AST 支持，规则用一种语法写 |
| 文档自定义规则 | Grit CLI + GritQL | 同一工具，Markdown Alpha 支持 |
| 架构依赖规则 | import-linter (Python) | 零配置开箱用，layers/forbidden/independence |
| 编排层 | ~100 行 Python 脚本 | 极薄，不需要重型框架 |

### 否决方案

- **MegaLinter**：需要 Docker，太重，只是 linter 聚合器不是统一引擎
- **Biome v2 + GritQL plugin**：仅 JS/TS，不支持 Python/Go/Rust
- **ESLint**：仅 JS/TS，插件生态成熟但语言限制

## 3. GritQL 关键知识

### 支持的语言（2026-06）

```
稳定：JS/TS, Python, JSON, Rust, CSS
Beta：Ruby, PHP
Alpha：Go, Java, SQL, Markdown, YAML, Terraform, Solidity
```

### 规则文件格式

GritQL 规则存在 `.grit/patterns/` 目录下，格式为 Markdown + YAML frontmatter + grit 代码块：

```markdown
---
name: rule_name_underscore
title: 规则标题
description: "描述（含冒号必须加引号）"
level: error  # info / warn / error
tags:
  - security
---

# 规则说明

```grit
language python

`$name = $value` where {
  $name <: r"(?i)password|secret",
}
```
```

### Pitfalls

1. **`register_diagnostic` 不存在于 standalone Grit CLI** — 这是 Biome 专有扩展。standalone Grit 用模式匹配本身作为诊断输出，不需要 register_diagnostic。

2. **Pattern name 必须匹配 `/^[A-Za-z_][A-Za-z0-9_]*$/`** — 不支持连字符。`service-ctx-first` 报错，必须用 `service_ctx_first`。

3. **YAML frontmatter 中含冒号的 description 必须加引号** — `description: 所有 Service 类的方法，第一个参数必须是 ctx: Context` 会 YAML parse error（冒号被当 key-value 分隔符）。必须写 `description: "..."`。

4. **`grit init` 需要 git 仓库有至少一个 commit** — 空仓库（unborn branch）会报 `Failed to get branch: reference 'refs/heads/main' not found`。先 `git add -A && git commit -m "init"` 再 `grit init`。

5. **Grit check 需要 `.grit/.gritmodules` 目录** — 首次运行前必须 `grit init`，否则会报 `Failed to open cache file`。

6. **`--level info` 显示所有级别** — 默认只显示 warn/error，info 级别规则需要 `--level info` 才显示。

7. **`cargo install grit` 编译极慢** — Windows 上建议直接下载预编译 binary：`https://github.com/biomejs/gritql/releases` 的 `grit-x86_64-pc-windows-msvc.tar.gz`。
   **发布到 GitHub 时的关键决策**：Grit binary（grit.exe ~79MB, grit.tar.gz ~19MB）**绝不入仓**。在 `.gitignore` 里排除后，README 必须写明用户单独下载方式（Windows/Mac/Linux 各一条命令）。`.grit/patterns/` 的 GritQL 规则必须保留 tracking（这是项目的核心资产，不是二进制）。完整发布清理流程见 `unified-lint-development` skill 的"发布到 GitHub 前的 .gitignore 审计"小节。

## 4. import-linter 关键知识

### 安装

```bash
pip install import-linter
```

### 配置（.importlinter）

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
```

### 三种契约类型

- **layers**：声明层级顺序，上层可依赖下层，下层不可依赖上层
- **forbidden**：禁止特定模块间的导入
- **independence**：声明两个模块互相独立

### 运行

```bash
lint-imports
```

精确输出违规的 import 路径和行号。

## 5. 项目结构模板

```
project/
├── .grit/
│   └── patterns/           # GritQL 规则
│       ├── no_hardcoded_password.md
│       ├── service_ctx_first.md
│       ├── api_result_wrapper.md
│       └── doc_frontmatter_required.md
├── .importlinter           # 架构规则配置
├── lint.py                 # 统一入口（~100 行）
├── grit.exe                # Grit CLI binary
└── myapp/                  # 被测项目
    ├── domain/
    ├── service/
    ├── infra/
    └── api/
```

## 6. 验证结果（2026-06-10 POC）

```
[1/3] 代码规则 (GritQL)
  检出: myapp/infra/user_repo.py:8 硬编码密码 ✓

[2/3] 文档规则 (GritQL)
  框架就绪，文档规则需迭代（Markdown Alpha 解析器限制）

[3/3] 架构规则 (import-linter)
  检出: myapp.infra.user_repo → myapp.domain.models (l.4) ✓

FAILED - 发现 2 个问题
```

## 8. 扩展路径

- **JS/TS 项目**：Biome v2 + GritQL plugin 系统
- **Go 项目**：Grit CLI (Alpha) + 自建架构规则
- **多语言项目**：Grit CLI 覆盖大部分 + 语言特定的架构工具

## 9. 参考资源

- GritQL 官方文档：https://docs.grit.io
- GritQL GitHub：https://github.com/biomejs/gritql
- import-linter 文档：https://import-linter.readthedocs.io
- Biome GritQL Recipes：https://biomejs.dev/recipes/gritql-plugins
- POC 项目：`<repo-root>`

## SEE ALSO

- references/tool-landscape.md — 工具全景对比（GritQL/Biome/MegaLinter/ESLint/Structurelint）
- references/gritql-python-recipes.md — Python GritQL 规则示例集
