# 工具全景对比（2026-06 调研）

## 候选方案矩阵

```
方案                代码规则    文档规则    架构规则    多语言    自定义插件     部署方式
─────────────────────────────────────────────────────────────────────────────────────
Grit CLI            ✓ AST     ✓ MD/JSON   ✗          14种     ✓ GritQL      Rust binary
Biome v2            ✓ AST     ✗ JS/TS     ✗          JS/TS    ✓ GritQL      npm
MegaLinter          ✓ 聚合    ✓ 聚合      ✗          48+      ✓ 添加linter  Docker
ESLint              ✓ AST     ✗ JS/TS     部分       JS/TS    ✓ npm plugin  npm
Super Linter        ✓ 聚合    ✓ 聚合      ✗          40+      有限          Docker Action
import-linter       ✗         ✗           ✓ Python   Python   ✓ contracts   pip
deptry              ✗         ✗           ✓ deps     Python   有限          pip
ArchUnitPython      ✗         ✗           ✓ arch     Python   ✓ Python API  pip
Structurelint       ✓ 结构    ✗           ✓ 依赖图   Go/Py/TS 有限           binary
Vale                ✗         ✓ prose     ✗          语言无关 ✓ YAML rules  binary
markdownlint        ✗         ✓ MD格式    ✗          MD only  ✓ JS plugin   npm
doc-gov             ✗         ✓ 结构      ✗          语言无关 ✓(v0.2计划)    Rust binary
```

## GritQL vs 替代方案

### GritQL 优势
- 一种语法覆盖 14 种语言，不需要为每种 linter 学不同 API
- 模式匹配直观：代码片段本身就是有效查询
- 支持自动修复（`grit check --fix`）
- Rust binary，单文件部署

### GritQL 局限
- 单文件分析，不做 import 图 / 跨文件依赖分析
- 无状态机概念（不能做文档生命周期）
- Markdown/YAML/Go/Java 仍是 Alpha 支持
- standalone CLI 不支持 `register_diagnostic`（Biome 专有）

## 推荐组合

```
Python 项目:  Grit CLI + import-linter + lint.py
JS/TS 项目:   Biome v2 (内置 GritQL plugin)
Go 项目:      Grit CLI + 自建架构规则（或用 deptry 等价物）
多语言:       Grit CLI + 各语言架构工具 + 统一入口脚本
```

## 关键发现

1. **Biome v2 的 GritQL plugin 系统**是 JS/TS 生态最有前途的方案，但仅限 JS/TS
2. **import-linter** 是 Python 架构规则的事实标准，import graph 分析精准
3. **Vale** 适合 prose 风格检查（Google/Microsoft 风格指南），与 GritQL 互补
4. **MegaLinter / Super Linter** 是聚合器不是引擎，不适合做自定义规则的底座
5. **LintCFG 论文**（arxiv 2602.07783）提出用 DSL + LLM 自动编译编码标准为 linter 配置，未来方向
