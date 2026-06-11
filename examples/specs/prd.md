---
stage: prd
id: prd-v1
requirements:
  - id: REQ-001
    name: 用户登录
    priority: P0
  - id: REQ-002
    name: 订单管理
    priority: P0
  - id: REQ-003
    name: 数据导出
    priority: P1
---

# 产品需求文档 (PRD)

## REQ-001 用户登录
- 支持用户名密码登录
- 支持 OAuth2.0 第三方登录
- 登录状态保持 7 天

## REQ-002 订单管理
- 用户可以创建订单
- 用户可以查看订单列表
- 用户可以取消未支付的订单

## REQ-003 数据导出
- 支持导出订单数据为 CSV
- 支持按时间范围筛选
- 导出文件有效期 24 小时
