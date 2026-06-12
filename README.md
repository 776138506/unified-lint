# Unified Lint POC

统一 Linter 端到端验证项目。

## 架构

三层检查：

1. **代码规则** (GritQL) - AST 级自定义规则
2. **文档规则** (GritQL) - 文档结构检查
3. **架构规则** (import-linter) - 分层依赖约束

## 快速开始

```bash
# 安装依赖
pip install import-linter
cargo install --git https://github.com/getgrit/gritql grit

# 跑全部检查
python lint.py

# 只跑某类
python lint.py --code
python lint.py --docs
python lint.py --arch

# 自动修复
python lint.py --fix
```

## 项目结构

```
unified-lint-poc/
├── domain/          # 核心业务层（最内层）
├── service/         # 业务服务层
├── infra/           # 基础设施层
├── api/             # API 层
├── docs/            # 文档
├── .lint-config/    # Lint 规则配置
│   ├── code-rules/  # GritQL 代码规则
│   └── doc-rules/   # GritQL 文档规则
├── .importlinter    # 架构依赖规则
└── lint.py          # 统一入口
```
