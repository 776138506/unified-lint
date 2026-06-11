---
stage: api
id: api-v1
covers_metrics: metrics-v1
endpoints:
  - path: /api/v1/login
    method: POST
    estimated_latency_ms: 150
    target_availability: 99.9
  - path: /api/v1/orders
    method: GET
    estimated_latency_ms: 250
    target_availability: 99.8
  - path: /api/v1/orders
    method: POST
    estimated_latency_ms: 180
    target_availability: 99.9
---

# API 文档

## POST /api/v1/login
用户登录接口

**预估延迟**: 150ms ✓  
**目标可用性**: 99.9% ✓

## GET /api/v1/orders
订单列表查询接口

**预估延迟**: 250ms ✗ (超过 P95 标准 200ms)  
**目标可用性**: 99.8% ✗ (低于标准 99.9%)

## POST /api/v1/orders
创建订单接口

**预估延迟**: 180ms ✓  
**目标可用性**: 99.9% ✓
