---
stage: metrics
id: metrics-v1
covers_features:
  - feature-login
  - feature-order

# 核心指标（必填）
core_metrics:
  latency_p95_ms: 200
  latency_p99_ms: 500
  availability: 99.9
  error_rate_percent: 0.1

# 重要指标（推荐填）
important_metrics:
  throughput_qps: 1000
  concurrency: 500
  response_size_kb: 100

# 次要指标（可选）
optional_metrics:
  cache_hit_rate_percent: 80
  cpu_usage_percent: 70
---

# 量化标准文档

## 核心性能要求

### 延迟
- P95 < 200ms（用户感知流畅）
- P99 < 500ms（极端情况可接受）

### 可用性
- 99.9%（每月宕机 < 43 分钟）

### 错误率
- < 0.1%（千分之一容忍度）

## 容量要求
- 支持 1000 QPS 峰值
- 支持 500 并发用户
- 单页响应 < 100KB
