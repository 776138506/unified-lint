# 统一 Linter 设计文档 v1.0

## 产品定位

一个 CLI 工具 + 预置规则库，让团队在 5 分钟内获得三层 lint 能力：
- 代码自定义规则（AST/regex）
- 文档结构规则
- 架构依赖规则

底层组合现有工具（Grit CLI / import-linter / 未来的 depguard），不重新造轮子。


## 设计决策记录

| 问题 | 选择 | 理由 |
|:---|:---|:---|
| 产品形态 | C. 编排层+安装器+规则库 | 一个工具搞定安装和运行，规则可复用 |
| 规则体系 | B. 分散+索引 | 各工具用原生配置格式，统一入口自动发现 |
| 架构规则 | B. 抽象层 | Python 用 import-linter，未来扩展 Go/Rust |
| GritQL 调试 | 按业务情况 | 简单规则用 GritQL，复杂降级 regex 或 semgrep |


## 架构图

```
用户执行
    │
    ▼
unified-lint (Python CLI)
    │
    ├── init        → 生成项目配置 + 安装依赖 + 复制规则模板
    ├── check       → 聚合三层检查结果
    ├── fix         → 自动修复可修复的问题
    └── rule list   → 列出可用规则
            │
            ├─── Layer 1: 代码规则
            │    引擎: Grit CLI (grit check)
            │    配置: .grit/patterns/*.md
            │    备选: semgrep (Python AST 更成熟时切换)
            │
            ├─── Layer 2: 文档规则
            │    引擎: Grit CLI (grit check)
            │    配置: .grit/patterns/*.md (language markdown)
            │    备选: markdownlint-cli2
            │
            └─── Layer 3: 架构规则
                 引擎: [可插拔]
                   python → import-linter
                   go     → depguard (未来)
                   rust   → cargo-deny (未来)
                 配置: .unified-lint/arch.toml (统一格式)
                 适配: unified-lint 将 arch.toml 转换为各引擎原生格式
```


## 文件结构

```
unified-lint/                    ← 工具本体
├── pyproject.toml               ← pip installable
├── src/
│   └── unified_lint/
│       ├── __init__.py
│       ├── cli.py               ← CLI 入口 (click/typer)
│       ├── runner.py            ← 聚合执行器
│       ├── engines/             ← 引擎适配层
│       │   ├── base.py          ← 抽象基类
│       │   ├── grit.py          ← Grit CLI 适配
│       │   ├── import_linter.py ← import-linter 适配
│       │   └── semgrep.py       ← semgrep 适配 (预留)
│       ├── installer.py         ← 依赖安装 (grit/import-linter)
│       └── rules/               ← 规则库管理
│           ├── registry.py      ← 规则发现+索引
│           └── builtin/         ← 预置规则
│               ├── code/
│               ├── doc/
│               └── arch/
├── tests/
│   ├── test_cli.py
│   ├── test_grit_engine.py
│   ├── test_import_linter_engine.py
│   └── test_runner.py
└── README.md

目标项目/                        ← 用户使用
├── .unified-lint/
│   ├── config.toml              ← 主配置 (启用哪些规则集)
│   └── arch.toml                ← 架构规则 (统一格式)
├── .grit/
│   └── patterns/                ← 项目级 GritQL 规则 (覆盖/扩展预置)
└── .importlinter                ← 由 arch.toml 生成 (自动生成，不手写)
```


## 核心流程

### init 流程
```
1. 检测项目语言 (Python/Go/JS/Rust)
2. 生成 .unified-lint/config.toml (按语言预设)
3. 安装引擎依赖 (pip install import-linter / 下载 grit binary)
4. 复制预置规则到 .grit/patterns/ (用户可改)
5. 从 config.toml 中的 arch 配置生成 .importlinter
```

### check 流程
```
1. 读取 .unified-lint/config.toml
2. 按启用顺序跑各引擎:
   a. grit check .grit/patterns/ → 代码+文档规则
   b. 读取 arch.toml → 转换为引擎原生格式 → 执行
3. 聚合所有引擎输出
4. 统一格式报告 (按 severity 排序)
5. 退出码: 0=全过, 1=有error, 2=只有warn, 3=工具缺失
```

### 架构规则抽象层
```toml
# .unified-lint/arch.toml
[layers]
order = ["api", "infra", "service", "domain"]

[contracts.forbidden]
# infra 不能直接导入 domain
from = "myapp.infra"
to = "myapp.domain"

[contracts.forbidden]
# api 不能导入 infra
from = "myapp.api"
to = "myapp.infra"
```

unified-lint 将 arch.toml 转换为:
- Python → .importlinter (import-linter 格式)
- Go → .depguard.yml (未来)
- Rust → deny.toml (未来)


## 预置规则库 (v0.1)

### 代码规则 (GritQL)
| 规则 | 说明 | severity |
|:---|:---|:---|
| no_hardcoded_secrets | 禁止硬编码密码/密钥 | error |
| service_ctx_first | Service 方法第一个参数必须是 ctx | warn |
| no_raw_dict_return | API 层禁止返回裸 dict | error |
| no_bare_except | 禁止裸 except | warn |

### 文档规则 (GritQL/Markdown)
| 规则 | 说明 | severity |
|:---|:---|:---|
| doc_frontmatter | 文档必须包含 frontmatter | warn |
| doc_no_broken_links | 禁止断链 | warn |

### 架构规则 (arch.toml)
| 规则 | 说明 | severity |
|:---|:---|:---|
| layers_order | 分层依赖方向 | error |
| forbidden_import | 禁止特定跨层导入 | error |
| no_circular | 禁止循环依赖 | error |


## 技术选型

| 组件 | 选择 | 理由 |
|:---|:---|:---|
| CLI 框架 | typer | 类型安全，自动生成帮助 |
| 配置格式 | TOML | Python 生态标准 |
| 测试框架 | pytest | 标准选择 |
| 包管理 | uv / pip | 兼容性 |
| 规则引擎 | Grit CLI | 多语言 AST + 模式匹配 |
| 架构引擎 | import-linter | Python 生态最佳 |


## 版本规划

### v0.1 (本次实施)
- CLI: init / check / fix
- 引擎: Grit + import-linter
- 预置规则: 6 条
- 测试: 基本覆盖

### v0.2
- 规则市场: 从 GitHub repo 安装社区规则
- semgrep 引擎备选
- pre-commit hook 集成

### v0.3
- Go/Rust 架构引擎
- 多语言项目支持
- 规则组合集 (security / architecture / style)
