---
stage: biz-arch
id: biz-arch-v1
covers_requirements:
  - REQ-001
  - REQ-002
modules:
  - name: AuthService
    covers: REQ-001
    responsibilities:
      - 用户认证
      - Token 管理
  - name: OrderService
    covers: REQ-002
    responsibilities:
      - 订单创建
      - 订单查询
      - 订单取消
---

# 业务架构文档

## AuthService 模块
负责用户认证和授权，支持多种登录方式。

## OrderService 模块
负责订单的完整生命周期管理。

## 缺失：REQ-003 数据导出
（故意遗漏，用于测试 spec-chain 引擎检测能力）
