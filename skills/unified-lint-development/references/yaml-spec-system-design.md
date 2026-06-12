# YAML Spec System Design (v0.1 - 2026-06-12)

## Core Design Principles

### 1. Directory Structure = Human-Readable Hierarchy

```
specs/
├── prd.yaml                    # Parent (overall info)
├── prd/                        # Children directory
│   ├── REQ-001.yaml            # Individual child
│   ├── REQ-002.yaml
│   └── features/               # Derived children
│       ├── FEAT-001.yaml
│       └── tests/              # Further derivation
│           └── UT-001.yaml
├── biz-arch.yaml
├── biz-arch/
│   └── modules/
│       └── AuthService/
│           ├── module.yaml
│           └── interfaces/
```

**Key rule**: parent.yaml + parent/ directory are siblings. Directory tree shows derivation/ownership.

### 2. Self-Contained Objects (All Info as Fields)

```yaml
# CORRECT: Everything is a field within the object
# specs/features/FEAT-001.yaml
meta:
  id: "FEAT-001"
  version: "1.0"

name: "用户名密码登录"
requirement: "REQ-001"
priority: "P0"

# Context as FIELD (not separate file)
context:
  rationale: "核心登录功能"
  assumptions: ["Redis 可用"]

# Constraints as FIELD
constraints:
  technical:
    - constraint: "使用 Redis 实现失败计数"
  business:
    - constraint: "登录失败 3 次后锁定 30 分钟"

# Development log as FIELD (not separate file)
dev_log:
  stages:
    - stage: "design"
      status: "completed"
      decisions:
        - decision: "选择 Redis 实现"
          reason: "性能要求"
    - stage: "implementation"
      status: "in_progress"
      tasks:
        - task: "实现 Redis 失败计数"
          status: "completed"

# Prompts as FIELD
prompts:
  for_llm: "使用 Redis INCR 实现"
  for_test: "覆盖：1-2次不锁，3次锁"
  for_linter: "强制使用 Redis"

# Relations via ID references
api_endpoints: ["EP-001", "EP-002"]
test_cases: ["UT-001"]
```

**WRONG**: Splitting into separate files
```
features/FEAT-001/
├── feature.yaml        ✗ Why separate?
├── context.yaml        ✗ Should be field
├── dev_log.yaml        ✗ Should be field
└── constraints.yaml    ✗ Should be field
```

### 3. PRD as Root (Derivation Hierarchy)

```
PRD (root)
├── Requirements (direct content)
├── Features (derived from requirements)
│   └── Tests (derived from features)
├── Business Architecture (derived from PRD)
│   ├── Modules
│   ├── Data Model (derived from biz-arch)
│   └── Technical Architecture (derived from biz-arch)
│       ├── API (derived from tech-arch)
│       └── Deployment (derived from tech-arch)
```

**Key insight**: Features are UNDER prd/, not siblings. API is UNDER tech-arch/, not siblings with PRD.

### 4. Two-Layer Design

| Layer | Structure | Purpose | Who |
|-------|-----------|---------|-----|
| Directory | Tree | Human-readable hierarchy | Humans |
| File Internal | Network topology | Complex dependencies | Machines |

### 5. AI-Centric Design

**User preference**: "我是给你用的，人是次要的，基本不会去编写他"

- YAML is primarily for AI, not humans
- AI generates YAML content
- AI maintains indexes
- AI enforces structure via code validation

### 6. Layer Separation: Code vs AI

| Responsibility | Who | Why |
|---------------|-----|-----|
| YAML Schema validation | Code | Deterministic, reliable |
| Index generation | Code | Automatic, consistent |
| Structure enforcement | Code | No skipping, no arbitrary modification |
| Content generation | AI | Creative, flexible |
| Decision making | AI | Contextual, adaptive |
| Prompt generation | AI | Domain-specific |

## Reference Files

- See `references/yaml-spec-examples.md` for complete YAML examples
- See `references/spec-chain-design.md` for spec-chain engine design
