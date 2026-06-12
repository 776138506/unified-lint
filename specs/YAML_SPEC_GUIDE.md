# YAML 规范编写指南

本指南定义了如何使用 YAML 完全替代传统项目文档，实现结构化存储、渐进式披露、前端可视化、项目进度管理、版本控制、自动化等优势。

## 目录

1. [核心理念](#核心理念)
2. [文件体系](#文件体系)
3. [Schema 规范](#schema-规范)
4. [扩展性设计](#扩展性设计)
5. [CLI 命令设计](#cli-命令设计)
6. [自动化派生](#自动化派生)

---

## 核心理念

### 为什么用 YAML 替代传统文档？

| 传统文档 | YAML 规范 | 优势 |
|:---|:---|:---|
| Word/PDF/Markdown | 结构化 YAML | 机器可读，可自动化处理 |
| 自然语言描述 | 字段+类型+约束 | 无歧义，可验证 |
| 手动维护 | 自动生成 | 一致性保证 |
| 版本控制困难 | Git 友好 | 变更追溯 |
| 无法可视化 | 可渲染 | 前端可视化 |
| 无法自动化 | 可派生 | 测试/Lint/代码生成 |

### 设计原则

1. **结构化存储**：所有信息以 YAML 字段存储，机器可直接读取
2. **渐进式披露**：AI 按需检索，不加载全量
3. **扩展性**：`x_*` 前缀字段支持任意扩展
4. **版本控制**：每个文件独立版本，变更可追溯
5. **自动化派生**：从 YAML 自动生成测试、Lint、代码骨架

---

## 文件体系

### 阶段划分

| 阶段 | 文件名 | 核心内容 | 覆盖关系 |
|:---|:---|:---|:---|
| 1 | `prd.yaml` | 需求、验收标准 | - |
| 2 | `biz-arch.yaml` | 领域模块、覆盖关系 | → prd |
| 3 | `features.yaml` | 功能点、优先级 | → prd |
| 4 | `metrics.yaml` | 性能指标、阈值 | → features |
| 5 | `tech-arch.yaml` | 技术选型、分层 | → biz-arch |
| 6 | `api.yaml` | 接口定义、参数 | → metrics |
| 7 | `deployment.yaml` | 环境、监控 | → tech-arch |
| 8 | `decisions.yaml` | 决策记录、选型理由 | - |
| 9 | `changelog.yaml` | 变更历史 | → all |
| 10 | `datamodel.yaml` | 实体、字段、关系 | → biz-arch |
| 11 | `tests.yaml` | 测试用例、覆盖 | → requirements, api |
| 12 | `roles.yaml` | 角色、权限矩阵 | - |

### 文件依赖图

```
prd.yaml
├── biz-arch.yaml
│   └── tech-arch.yaml
│       └── deployment.yaml
├── features.yaml
│   └── metrics.yaml
│       └── api.yaml
├── datamodel.yaml
├── tests.yaml
└── roles.yaml

decisions.yaml (独立)
changelog.yaml (全局)
```

---

## Schema 规范

### 通用字段

每个 YAML 文件必须包含以下通用字段：

```yaml
stage: string          # 阶段标识（prd, biz-arch, features, etc.）
id: string             # 版本标识（prd-v1, biz-arch-v1, etc.）
metadata:              # 元数据
  author: string       # 作者
  created: datetime    # 创建时间
  updated: datetime    # 更新时间
  version: string      # 版本号
  status: enum         # 状态（draft, reviewed, approved, deprecated）
  x_*: any             # 扩展字段
```

### 字段类型

| 类型 | 说明 | 示例 |
|:---|:---|:---|
| `string` | 字符串 | `"用户登录"` |
| `integer` | 整数 | `200` |
| `number` | 浮点数 | `99.9` |
| `boolean` | 布尔值 | `true` |
| `datetime` | 日期时间 | `"2026-06-12T10:00:00Z"` |
| `enum` | 枚举值 | `["P0", "P1", "P2"]` |
| `array` | 数组 | `["REQ-001", "REQ-002"]` |
| `object` | 对象 | `{name: "AuthService"}` |

### 必填 vs 可选

- **必填字段**：无默认值，必须显式提供
- **可选字段**：有默认值，可省略
- **扩展字段**：`x_*` 前缀，任意添加

---

## 扩展性设计

### 扩展字段规范

所有自定义字段必须使用 `x_` 前缀：

```yaml
# 标准字段
name: "用户登录"
priority: "P0"

# 扩展字段
x_security_level: "high"
x_ui_complexity: "medium"
x_story_points: 5
x_sprint: 1
x_assignee: "后端开发"
```

### 扩展点设计

每个阶段都有明确的扩展点：

```yaml
# 需求扩展点
requirements:
  - id: REQ-001
    name: "用户登录"
    # 业务规则扩展点
    business_rules:
      - condition: "连续登录失败 5 次"
        action: "锁定账户"
        x_severity: "high"
    # 自定义扩展
    x_security_level: "high"
    x_ui_complexity: "medium"
```

### 扩展字段命名规范

| 前缀 | 用途 | 示例 |
|:---|:---|:---|
| `x_` | 通用扩展 | `x_story_points`, `x_sprint` |
| `x_team_` | 团队相关 | `x_team_size`, `x_team_lead` |
| `x_tech_` | 技术相关 | `x_tech_stack`, `x_tech_debt` |
| `x_biz_` | 业务相关 | `x_biz_value`, `x_biz_risk` |
| `x_process_` | 流程相关 | `x_process_stage`, `x_process_owner` |

---

## CLI 命令设计

### 基础命令

```bash
# 初始化项目规范
spec init

# 验证规范格式
spec validate

# 查看规范状态
spec status

# 生成可视化
spec visualize

# 导出规范
spec export

# 导入规范
spec import
```

### 验证命令

```bash
# 验证所有规范
spec validate

# 验证特定文件
spec validate prd.yaml

# 验证依赖关系
spec validate --dependencies

# 验证扩展字段
spec validate --extensions
```

### 可视化命令

```bash
# 生成架构图
spec visualize architecture

# 生成决策树
spec visualize decisions

# 生成进度看板
spec visualize progress

# 生成依赖图
spec visualize dependencies
```

### 自动化命令

```bash
# 生成测试用例
spec generate tests

# 生成 Lint 规则
spec generate lint

# 生成代码骨架
spec generate code

# 生成 API 文档
spec generate api-docs
```

---

## 自动化派生

### 从 YAML 生成测试

```yaml
# tests.yaml 中的测试用例
test_cases:
  unit:
    - id: UT-001
      name: "用户登录成功"
      requirement: "REQ-001"
      steps:
        - "创建测试用户"
        - "调用 authenticate 方法"
        - "验证返回 Token"
      expected_result: "返回有效的 JWT Token"
```

自动生成：
```python
def test_user_login_success():
    # 创建测试用户
    user = create_test_user()
    # 调用 authenticate 方法
    token = auth_service.authenticate(user.username, "password")
    # 验证返回 Token
    assert token is not None
    assert len(token) > 0
```

### 从 YAML 生成 Lint 规则

```yaml
# prd.yaml 中的业务规则
business_rules:
  - id: BR-001
    condition: "用户连续登录失败 5 次"
    action: "锁定账户 30 分钟"
```

自动生成 Lint 规则：
```python
@chain_rule("br_001_check")
def check_login_lockout(source, target, source_file, target_file):
    """检查登录锁定逻辑是否实现"""
    violations = []
    # 检查 AuthService 是否有锁定逻辑
    if "lock_account" not in target.get("implemented_methods", []):
        violations.append(Violation(
            rule_id="br_001_check",
            message="业务规则 BR-001 未实现：登录锁定逻辑",
            file=target_file,
        ))
    return violations
```

### 从 YAML 生成代码骨架

```yaml
# api.yaml 中的接口定义
endpoints:
  - path: "/api/v1/auth/login"
    method: "POST"
    request:
      body:
        type: "object"
        properties:
          username:
            type: "string"
          password:
            type: "string"
    responses:
      - status: 200
        body:
          type: "object"
          properties:
            token:
              type: "string"
```

自动生成：
```python
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str

@app.post("/api/v1/auth/login")
async def login(request: LoginRequest) -> LoginResponse:
    # TODO: 实现登录逻辑
    pass
```

---

## 最佳实践

### 1. 渐进式披露

```yaml
# Level 0: 项目摘要
metadata:
  x_project_summary: "用户管理系统"

# Level 1: 任务相关
requirements:
  - id: REQ-001
    name: "用户登录"
    # 只加载当前任务需要的字段

# Level 2: 详细信息
business_rules:
  - id: BR-001
    condition: "连续登录失败 5 次"
    action: "锁定账户"
    # 按需加载
```

### 2. 版本控制

```yaml
# 每次变更更新版本
metadata:
  version: "1.1"
  updated: "2026-06-12"

# 变更记录
changelog:
  - version: "1.1"
    date: "2026-06-12"
    changes:
      - "新增 OAuth2.0 登录需求"
```

### 3. 依赖管理

```yaml
# 明确声明依赖
dependencies:
  - from: "FEAT-002"
    to: "FEAT-001"
    type: "strong"
    reason: "OAuth 登录依赖基础登录功能"
```

### 4. 扩展性

```yaml
# 使用 x_ 前缀扩展
x_custom_field: "value"
x_team_specific:
  x_team_size: 5
  x_team_lead: "张三"
```

---

## 总结

YAML 规范体系的核心优势：

1. **结构化存储**：机器可读，可自动化处理
2. **渐进式披露**：按需检索，不加载全量
3. **前端可视化**：可渲染为图表、看板
4. **项目进度管理**：功能点、迭代计划
5. **版本控制**：Git 友好，变更可追溯
6. **自动化派生**：测试/Lint/代码生成

通过这套规范，我们实现了"规范即真相"的目标，让 AI 从"模糊理解"升级为"精确执行"，让人专注于设计和决策。
