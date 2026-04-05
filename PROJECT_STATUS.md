# scan-order 项目状态

> 扫码点餐系统 — 微信 H5 + 商户后台
> 最后更新：2026-04-05

## 基本信息

| 字段 | 内容 |
|------|------|
| 项目名称 | scan-order |
| 中文名 | 扫码点餐 |
| 定位 | 面向小商户的扫码点餐解决方案 |
| 目标客户 | 餐饮小商户 |
| 负责人 | 猫爸 |
| 当前阶段 | Phase 6 完成（优化中） |
| 技术栈 | Python FastAPI + SQLite + Vue3 |
| 记账模式 | 不做微信/支付宝支付，只记录应收、实收，对账用 |

## Phase 划分

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 基础设施（脚手架 + 数据库） | ✅ 完成 |
| Phase 2 | 商户后台 API | ✅ 完成 |
| Phase 3 | 顾客端 API | ✅ 完成 |
| Phase 4 | 商户后台前端 | ✅ 完成 |
| Phase 5 | 顾客端 H5 前端 | ✅ 完成 |
| Phase 6 | 联调与验收 | ✅ 完成 |
| Phase Kitchen | 后厨屏 KDS | ✅ 设计完成，待实施 |

## 已知 Bug

| Bug | 严重性 | 状态 |
|-----|--------|------|
| BUG-001：数据库中文编码错误（UTF-8 vs GBK） | 中等 | ❌ 未修复 |

## 关键文档

| 文档 | 说明 |
|------|------|
| `ARCHITECTURE.md` | 系统架构设计 |
| `PLAN.md` | MVP 开发计划（Task 1-17） |
| `BUG_LIST.md` | Bug 列表 |
| `ERROR_RECOVERY_DESIGN.md` | 错误处理 + 检查点恢复设计 |
| `PHASE6_TEST_PLAN.md` | Phase 6 联调测试方案 |
| `PHASE_KITCHEN_DESIGN.md` | 后厨屏 KDS 模块设计 |

## 待办事项

- [ ] 修复 BUG-001（数据库中文编码错误）
- [ ] 实施后厨屏 KDS 模块（Phase Kitchen）
- [ ] 优化建议（猫爸审核后提出，待补充）

## 审核记录

> 待补充：猫爸审核后提出的优化建议（04-05）

## 备注

项目文档统一存放于 `C:\Users\Administrator\Documents\龙虾小兵项目\scan-order\` 目录下
