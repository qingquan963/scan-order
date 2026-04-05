# Phase 6 联调测试方案
# 扫码点餐系统 - Phase 6 Task-17

> 版本：v1.0
> 日期：2026-04-03
> 范围：Phase 1 ~ Phase 3C 所有 API
> 后端服务地址：http://127.0.0.1:8002

---

## 一、API 清单（Phase 1 ~ 3C 全部接口）

### 1.1 公共接口 `/api/v1`

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 1 | GET | `/health` | 无 | 健康检查 |

---

### 1.2 顾客端接口 `/api/v1/customer`

#### 公开接口（无需认证）

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 2 | GET | `/tables/{table_id}` | 无 | 获取桌台信息 |
| 3 | GET | `/categories` | 无 | 获取菜品分类列表 |
| 4 | GET | `/dishes` | 无 | 获取菜品列表（只返回 is_available=1） |
| 5 | GET | `/dishes/{dish_id}` | 无 | 获取菜品详情 |
| 6 | POST | `/orders` | 无 | 创建订单（Phase 1/2 简易版） |
| 7 | GET | `/orders/{order_id}` | 无 | 查询订单状态 |
| 8 | GET | `/merchants/{merchant_id}/settings` | 无 | 获取商户公开设置 |
| 9 | POST | `/orders/{order_id}/pay` | 无 | 模拟支付确认（counter_pay 模式） |

#### 微信顾客端接口（Phase 3B，需 `Authorization: Bearer <wx_customer_token>`）

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 10 | POST | `/wx/customer/login` | 无 | 顾客微信登录（code 换 token） |
| 11 | GET | `/wx/customer/me` | WX | 获取当前顾客信息（含积分/等级） |
| 12 | POST | `/wx/coupons/{coupon_id}/claim` | WX | 领取优惠券 |
| 13 | GET | `/wx/coupons/my` | WX | 我的优惠券（按状态分组） |
| 14 | GET | `/wx/coupons/available` | WX | 当前可用优惠券 |
| 15 | GET | `/wx/points/history` | WX | 积分明细 |
| 16 | GET | `/wx/points/preview` | WX | 下单前积分预览 |
| 17 | POST | `/member/orders` | WX | 创建订单（支持优惠券+积分抵扣） |
| 18 | GET | `/member/orders` | WX | 顾客订单列表 |
| 19 | GET | `/member/orders/{order_id}` | WX | 顾客订单详情 |

---

### 1.3 商户后台接口 `/api/v1/admin`

#### 认证相关

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 20 | POST | `/auth/login` | 无 | 商户登录（用户名+密码） |
| 21 | POST | `/auth/register` | 无 | 商户注册 |
| 22 | POST | `/merchant-users/login` | 无 | 商户用户登录（用户名+密码） |
| 23 | POST | `/merchant-users/register` | 无 | 注册新商户用户（需 owner） |
| 24 | GET | `/merchant-users/me` | JWT | 获取当前用户信息 |
| 25 | GET | `/merchant-users` | JWT | 列出商户用户（仅 owner） |
| 26 | PUT | `/merchant-users/{user_id}` | JWT | 更新商户用户（仅 owner） |
| 27 | DELETE | `/merchant-users/{user_id}` | JWT | 删除商户用户（仅 owner） |

#### 微信授权登录（Phase 3A）

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 28 | GET | `/wx-auth/auth-url` | 无 | 获取微信授权 URL |
| 29 | POST | `/wx-auth/callback` | 无 | 微信授权回调 |
| 30 | POST | `/wx-auth/refresh` | 无 | 刷新 Access Token |
| 31 | GET | `/wx-auth/wx-login-test` | 无 | 模拟微信登录（开发环境） |

#### 平台管理员（Phase 3A）

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 32 | POST | `/platform-admin/auth/login` | 无 | 平台管理员登录 |
| 33 | GET | `/platform-admin/merchants` | PA | 列出所有商户（含待审核） |
| 34 | PUT | `/platform-admin/merchants/{merchant_id}/approve` | PA | 审核通过商户 |
| 35 | PUT | `/platform-admin/merchants/{merchant_id}/reject` | PA | 拒绝商户入驻 |
| 36 | PUT | `/platform-admin/merchants/{merchant_id}/suspend` | PA | 暂停商户 |
| 37 | GET | `/platform-admin/admins` | PA | 列出平台管理员（仅 super_admin） |
| 38 | POST | `/platform-admin/admins` | PA | 创建平台管理员（仅 super_admin） |

#### 分类管理

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 39 | GET | `/categories` | JWT | 获取分类列表 |
| 40 | POST | `/categories` | JWT | 新增分类 |
| 41 | PUT | `/categories/{category_id}` | JWT | 编辑分类 |
| 42 | DELETE | `/categories/{category_id}` | JWT | 删除分类（有菜品时 409） |

#### 菜品管理

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 43 | GET | `/dishes` | JWT | 获取菜品列表（支持 category_id 筛选） |
| 44 | POST | `/dishes` | JWT | 新增菜品 |
| 45 | PUT | `/dishes/{dish_id}` | JWT | 编辑菜品 |
| 46 | PATCH | `/dishes/{dish_id}/toggle-available` | JWT | 切换上下架 |
| 47 | DELETE | `/dishes/{dish_id}` | JWT | 删除菜品 |

#### 桌台管理

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 48 | GET | `/tables` | JWT | 获取桌台列表 |
| 49 | POST | `/tables` | JWT | 新增桌台（code 唯一） |
| 50 | GET | `/tables/{table_id}` | JWT | 获取桌台详情 |
| 51 | PUT | `/tables/{table_id}` | JWT | 编辑桌台 |
| 52 | DELETE | `/tables/{table_id}` | JWT | 删除桌台（有订单时 409） |
| 53 | GET | `/tables/{table_id}/qrcode` | JWT | 生成桌台 PNG 二维码 |

#### 订单管理

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 54 | GET | `/orders` | JWT | 获取订单列表（支持 status 筛选、分页） |
| 55 | GET | `/orders/{order_id}` | JWT | 订单详情（含菜品明细） |
| 56 | PUT | `/orders/{order_id}/status` | JWT | 更新订单状态 |
| 57 | GET | `/orders/{order_id}/ticket` | JWT | 获取订单小票文本 |

#### 统计

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 58 | GET | `/stats/today` | JWT | 今日经营概览 |
| 59 | GET | `/stats/sales` | JWT | 销售统计（按日/周/月） |

#### 商户设置

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 60 | GET | `/settings` | JWT | 获取商户设置 |
| 61 | PUT | `/settings` | JWT | 更新商户设置（mode） |

#### 优惠券管理（Phase 3B）

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 62 | POST | `/coupons` | JWT | 创建优惠券（需 owner） |
| 63 | GET | `/coupons` | JWT | 优惠券列表（支持 status 筛选） |
| 64 | GET | `/coupons/{coupon_id}` | JWT | 优惠券详情 |
| 65 | GET | `/coupons/{coupon_id}/records` | JWT | 优惠券核销明细 |
| 66 | POST | `/coupons/{coupon_id}/pause` | JWT | 暂停发放 |
| 67 | POST | `/coupons/{coupon_id}/resume` | JWT | 恢复发放 |

#### 积分规则（Phase 3B）

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 68 | GET | `/merchant/settings/points` | JWT | 获取积分规则配置 |
| 69 | PUT | `/merchant/settings/points` | JWT | 修改积分规则配置（需 owner） |

#### 报表管理（Phase 3C）

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 70 | GET | `/reports/daily` | JWT | 营收日报查询 |
| 71 | GET | `/reports/monthly` | JWT | 营收月报查询 |
| 72 | GET | `/reports/dishes` | JWT | 菜品销量排行 |
| 73 | GET | `/reports/customers` | JWT | 顾客消费分析 |
| 74 | GET | `/reports/customer-segments` | JWT | 顾客群体画像 |
| 75 | POST | `/reports/regenerate` | JWT | 手动重新聚合报表（仅 owner） |
| 76 | POST | `/reports/undo` | JWT | 撤销最近一次修正（仅 owner） |
| 77 | GET | `/reports/corrections` | JWT | 查询报表修正记录 |

#### 审计日志（Phase 3A）

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 78 | GET | `/audit-logs` | JWT | 查询当前商户审计日志 |
| 79 | GET | `/audit-logs/all` | PA | 查询全平台审计日志（仅平台管理员） |

#### 其他

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 80 | GET | `/health` | 无 | 商户后台健康检查 |
| 81 | GET | `/me` | JWT | 获取当前商户信息 |
| 82 | GET | `/dashboard` | JWT | 商户后台仪表盘 |

---

## 二、冒烟测试脚本说明

测试脚本位置：`backend/smoke_test.py`

**运行方式：**
```bash
cd backend
pip install requests
python smoke_test.py
```

**前置条件：**
- 后端服务运行于 `http://127.0.0.1:8002`
- 数据库已有种子数据（商户 admin/admin123）
- 已有至少 1 个分类、1 个菜品、1 个桌台

**覆盖范围：**
- 核心 API 冒烟测试（约 30 个关键接口）
- 顾客端全流程：浏览菜品 → 创建订单 → 支付 → 查看状态
- 商户后台全流程：登录 → 增删改查 → 订单状态流转
- Phase 3A/3B/3C 核心功能验证

---

## 三、手动验证清单

### 3.1 顾客端全流程（扫码点餐）

- [ ] **扫码入口**：微信扫描桌台二维码，打开 `/customer/h5?table_id=X`
- [ ] **桌台信息**：页面顶部正确显示桌台编号/名称
- [ ] **分类导航**：左侧分类列表正确显示，点击跳转菜品区域
- [ ] **菜品列表**：只显示 is_available=1 的菜品，显示图片/名称/价格/描述
- [ ] **已售罄**：is_available=0 的菜品显示"已售罄"标签，无法加入购物车
- [ ] **购物车**：加减按钮实时更新数量和总价，底部购物车栏同步
- [ ] **备注**：备注输入框可用，下单时传递 remark
- [ ] **下单**：提交订单成功，跳转订单状态页
- [ ] **订单状态**：pending → confirmed → paid 状态流转正确展示
- [ ] **订单轮询**：每 5 秒自动刷新订单状态
- [ ] **返回菜单**：订单完成后可返回菜单继续点餐
- [ ] **30秒幂等**：30秒内同一桌台重复下单，返回已有 pending 订单，不产生重复

### 3.2 微信顾客端（Phase 3B）

- [ ] **微信登录**：通过 `/wx/customer/login` 获取 token
- [ ] **领取优惠券**：领取成功，状态变为 unused
- [ ] **我的优惠券**：三个分组（unused/used/expired）正确显示
- [ ] **积分预览**：下单前正确显示可抵扣金额
- [ ] **积分扣减**：下单使用积分，余额正确扣减
- [ ] **积分明细**：历史积分变动记录正确
- [ ] **优惠券核销**：下单时正确扣减优惠券数量
- [ ] **订单含优惠**：优惠券+积分同时使用，金额计算正确

### 3.3 商户后台全流程

#### 登录与认证
- [ ] **用户名密码登录**：`/auth/login` 正确返回 JWT
- [ ] **登录失败**：错误密码返回 401
- [ ] **JWT 验证**：过期/无效 token 返回 401
- [ ] **商户用户登录**：`/merchant-users/login` 支持 owner/staff
- [ ] **商户用户注册**：owner 可注册新用户
- [ ] **权限隔离**：staff 用户无法操作 owner 专属接口（如创建优惠券）

#### 分类管理
- [ ] **新增分类**：名称重复时提示
- [ ] **编辑分类**：修改后列表实时更新
- [ ] **删除分类**：分类下有菜品时返回 409，无法删除
- [ ] **排序**：sort_order 控制分类排列顺序

#### 菜品管理
- [ ] **新增菜品**：必填字段校验（name, price, category_id）
- [ ] **价格边界**：price=0 或负数时前端/后端校验拒绝
- [ ] **上下架切换**：toggle-available 立即生效
- [ ] **分类筛选**：按 category_id 筛选只返回该分类菜品
- [ ] **商户隔离**：无法操作其他商户菜品（返回 404）
- [ ] **图片预览**：image_url 输入后正确预览

#### 桌台管理
- [ ] **code 唯一性**：重复 code 返回 409
- [ ] **二维码生成**：`/tables/{id}/qrcode` 返回有效 PNG
- [ ] **QR 内容正确**：二维码扫描后 URL 格式为 `/customer/h5?table_id=X`
- [ ] **删除保护**：有关联订单的桌台无法删除（409）

#### 订单管理
- [ ] **订单列表**：支持 status 筛选和分页
- [ ] **订单详情**：含菜品明细（名称/单价/数量/小计）
- [ ] **接单**：pending → confirmed 状态正确
- [ ] **结账**：confirmed → paid 状态正确
- [ ] **取消**：pending/confirmed 可取消（cancelled）
- [ ] **逆向拒绝**：paid 状态不可逆向操作（如 paid → pending）
- [ ] **小票生成**：`/orders/{id}/ticket` 返回格式正确的小票文本
- [ ] **payment_mode**：counter_pay 和 credit_pay 模式区分正确

#### 统计
- [ ] **今日概览**：`/stats/today` 显示订单数/营业额/已完成数
- [ ] **销售统计**：`/stats/sales` 支持 day/week/month 切换

#### 优惠券（Phase 3B）
- [ ] **创建优惠券**：填写所有字段后创建成功
- [ ] **限量控制**：total_count 耗尽后无法继续领取
- [ ] **暂停/恢复**：pause 后无法领取，resume 后恢复
- [ ] **使用门槛**：订单金额不满足 threshold 时无法使用
- [ ] **核销明细**：使用后 records 显示核销时间/顾客

#### 积分规则（Phase 3B）
- [ ] **积分开关**：points_enabled=0 时顾客无法使用积分
- [ ] **积分比例**：points_per_yuan 正确影响积分计算
- [ ] **抵扣上限**：points_max_discount_percent 限制最大抵扣比例

#### 报表（Phase 3C）
- [ ] **日报查询**：指定日期范围返回每日营收数据
- [ ] **月报查询**：按月聚合返回营收数据
- [ ] **日期范围校验**：start_date > end_date 返回 400
- [ ] **未来日期拒绝**：end_date 为未来日期返回 400
- [ ] **菜品排行**：指定日期范围返回菜品销量排序
- [ ] **顾客分析**：返回消费金额/频次等统计
- [ ] **修正记录**：查询历史修正记录
- [ ] **修正恢复**：undo 后数据恢复到修正前

#### 平台管理员（Phase 3A）
- [ ] **商户审核**：pending 商户可 approve/reject
- [ ] **商户暂停**：active 商户可 suspend
- [ ] **审计日志**：记录关键操作（登录/创建/修改状态等）

### 3.4 边界测试

| 场景 | 预期结果 |
|------|---------|
| 菜品价格 = 0 | 后端返回 422 校验错误 |
| 菜品价格 = 负数 | 后端返回 422 校验错误 |
| 菜品价格超长小数（如 1.999） | 取两位小数 |
| 数量 = 0 的订单项 | 前端拒绝（最少为 1） |
| 数量为负数 | 后端返回 422 |
| 删除有菜品的分类 | 返回 409 Conflict |
| 删除有订单的桌台 | 返回 409 Conflict |
| 订单状态逆向操作（如 paid→pending） | 返回 400 |
| 无效的 JWT token | 返回 401 |
| 过期 JWT token | 返回 401 |
| 访问其他商户数据 | 返回 404（数据隔离） |
| counter_pay 订单不调用 pay 接口 | 订单保持 pending_payment |
| 重复领取同一优惠券 | 返回错误（已领取） |
| 积分不足时使用超出 | 返回错误 |
| 优惠券 + 积分抵扣后金额为负 | 最终金额 = 0 |
| 报表日期范围超过 366 天 | 返回 400 |

### 3.5 兼容性测试

| 平台 | 验证点 |
|------|--------|
| Windows Chrome | 顾客端 H5 + 商户后台 |
| macOS Safari | 顾客端 H5 |
| iOS Safari | 顾客端 H5（微信 WebView） |
| Android 微信 | 顾客端 H5（微信 WebView） |
| iOS 微信 | 顾客端 H5（微信 WebView） |

**微信 WebView 特别验证：**
- [ ] 页面可正常加载（无白屏）
- [ ] 微信扫码回调正确跳转
- [ ] 微信支付/静默授权（如有）
- [ ] 缓存问题：退出重进数据正确

---

## 四、Bug 报告模板

```markdown
## Bug #N

**标题**：[简要描述问题]

**严重级别**：P0 / P1 / P2 / P3
- P0：核心流程完全不可用（如无法下单）
- P1：核心功能受阻（如无法登录、无法查看订单）
- P2：功能异常但有 workaround
- P3：体验问题（样式/文案等）

**复现步骤**：
1. 
2. 
3. 

**实际结果**：

**预期结果**：

**环境**：
- 操作系统：
- 浏览器/微信版本：
- 后端版本：

**截图/日志**：

**是否可复现**：是/否
```

---

## 五、测试进度跟踪

| 测试项 | 测试员 | 日期 | 结果 | Bug 数 |
|-------|-------|------|------|--------|
| 冒烟测试（脚本） |  |  |  |  |
| 顾客端全流程 |  |  |  |  |
| 商户后台全流程 |  |  |  |  |
| Phase 3B 微信顾客端 |  |  |  |  |
| Phase 3C 报表 |  |  |  |  |
| 平台管理员 |  |  |  |  |
| 边界测试 |  |  |  |  |
| 兼容性测试 |  |  |  |  |

---

## 六、交付物

1. ✅ `PHASE6_TEST_PLAN.md` — 本文档（API清单 + 测试用例 + 验证清单）
2. ✅ `backend/smoke_test.py` — Python 冒烟测试脚本
3. `BUG_LIST.md` — 测试中发现的所有 Bug 列表（测试后更新）
