# 扫码点餐系统 MVP 开发计划

> 版本：v1.0  
> 日期：2026-04-02  
> 基于：ARCHITECTURE.md  
> MVP 范围：微信 H5 顾客端 + 商户后台 + 记账模式（无支付）

---

## 一、阶段划分与任务总览

| 阶段 | 内容 | 任务 |
|------|------|------|
| **Phase 1** | 基础设施（脚手架 + 数据库） | Task-1 ~ Task-3 |
| **Phase 2** | 商户后台 API | Task-4 ~ Task-7 |
| **Phase 3** | 顾客端 API | Task-8 |
| **Phase 4** | 商户后台前端 | Task-9 ~ Task-13 |
| **Phase 5** | 顾客端 H5 前端 | Task-14 ~ Task-16 |
| **Phase 6** | 联调与验收 | Task-17 |

---

## 二、任务详表

### 【Phase 1】基础设施

---

#### Task-1：项目脚手架搭建

**负责 Agent**：coder（后端）  
**工作内容**：
- 按 ARCHITECTURE.md 目录结构创建所有目录
- 初始化 FastAPI 后端项目（main.py、config.py、requirements.txt、run.py）
- 初始化两个 Vue3 前端项目（frontend-customer、frontend-admin），使用 Vite + Vue3 + TypeScript
- 配置 Vite 代理（开发环境 API 转发到 FastAPI）
- 编写 docker-compose.yml（可选，单节点 SQLite 部署）
- 创建 `.gitignore`、`README.md`

**验收标准**：
- [ ] `cd backend && python run.py` 能启动 FastAPI 服务（uvicorn），无报错
- [ ] `cd frontend-customer && npm run dev` 能启动 Vue3 开发服务器
- [ ] `cd frontend-admin && npm run dev` 能启动 Vue3 开发服务器
- [ ] 三个服务端口不冲突（建议：backend=8001, customer=3001, admin=3002）

**依赖**：无  
**风险**：低

---

#### Task-2：数据库层

**负责 Agent**：coder（后端）  
**工作内容**：
- 配置 SQLAlchemy + SQLite 连接（scan_order.db）
- 创建 ORM 模型：Merchant、Category、Dish、Table、Order、OrderItem
- 定义各表字段、约束、外键关系
- 创建 `database.py` 的 `init_db()` 初始化函数（建表）
- 创建种子数据脚本 `seed.py`：生成一个演示商户（username: admin / password: admin123）
- ORM 模型中定义基础查询方法（get_by_id, get_by_merchant）

**验收标准**：
- [ ] 运行 `python -c "from app.database import init_db; init_db()"` 能成功建表，无报错
- [ ] 运行 `python seed.py` 生成演示商户，可登录
- [ ] 所有模型字段与 ARCHITECTURE.md 表结构一致（字段名、类型、约束）
- [ ] 外键关系正确：Category→Merchant, Dish→Merchant/Category, Table→Merchant, Order→Merchant/Table, OrderItem→Order/Dish

**依赖**：Task-1（完成后解锁）  
**风险**：低

---

#### Task-3：商户认证模块

**负责 Agent**：coder（后端）  
**工作内容**：
- 实现商户登录 API：`POST /api/v1/admin/auth/login`（用户名+密码 → JWT Token）
- 实现 JWT Token 生成与验证工具（HS256，7天有效期）
- 实现 Token 中间件 `AdminAuthMiddleware`（验证 /api/v1/admin/** 路由的 Authorization Header）
- 实现 `GET /api/v1/health` 健康检查接口
- 登录响应包含 token 和 merchant_id

**验收标准**：
- [ ] 正确的用户名密码 → 返回 200 + JWT Token
- [ ] 错误密码 → 返回 401
- [ ] 请求 `/api/v1/admin/**` 时无 Authorization Header → 返回 401
- [ ] `GET /api/v1/health` 无需认证，返回 200 + `{"status": "ok"}`
- [ ] JWT Token 有效期为 7 天，过期后请求被拒绝

**依赖**：Task-2（完成后解锁）  
**风险**：低（JWT 实现成熟）

---

### 【Phase 2】商户后台 API

---

#### Task-4：分类管理 API

**负责 Agent**：coder（后端）  
**工作内容**：
- `GET /api/v1/admin/categories` — 获取当前商户所有分类（按 sort_order 排序）
- `POST /api/v1/admin/categories` — 新增分类（name, sort_order）
- `PUT /api/v1/admin/categories/{id}` — 编辑分类
- `DELETE /api/v1/admin/categories/{id}` — 删除分类（有菜品时禁止删除，返回 409）
- 路由受 AdminAuthMiddleware 保护

**验收标准**：
- [ ] 未登录请求 → 401
- [ ] 新增分类后立即 GET 可查到
- [ ] 编辑后数据正确更新
- [ ] 删除有菜品关联的分类 → 返回 409 Conflict
- [ ] 属于其他商户的分类无法操作 → 返回 404

**依赖**：Task-3（完成后解锁）  
**风险**：低

---

#### Task-5：菜品管理 API

**负责 Agent**：coder（后端）  
**工作内容**：
- `GET /api/v1/admin/dishes` — 列表（支持 category_id 筛选、is_available 筛选）
- `POST /api/v1/admin/dishes` — 新增菜品（name, price, description, image_url, category_id, is_available）
- `GET /api/v1/admin/dishes/{id}` — 详情
- `PUT /api/v1/admin/dishes/{id}` — 编辑菜品
- `DELETE /api/v1/admin/dishes/{id}` — 删除菜品（软删或硬删均可）
- image_url 字段支持存外链

**验收标准**：
- [ ] 菜品列表按 category_id 筛选正确
- [ ] is_available=0 的菜品在顾客端不展示（由 Task-8 保证）
- [ ] CRUD 操作均受商户隔离保护（只能操作自己商户的数据）
- [ ] price 字段只接受 > 0 的数值（POST/PUT 校验）

**依赖**：Task-4（完成后解锁）  
**风险**：低

---

#### Task-6：桌台管理 API

**负责 Agent**：coder（后端）  
**工作内容**：
- `GET /api/v1/admin/tables` — 列表
- `POST /api/v1/admin/tables` — 新增桌台（code 必须唯一）
- `GET /api/v1/admin/tables/{id}` — 详情
- `PUT /api/v1/admin/tables/{id}` — 编辑桌台
- `DELETE /api/v1/admin/tables/{id}` — 删除（有订单关联时禁止删除）

**验收标准**：
- [ ] code 重复时 POST 返回 409
- [ ] 删除有关联订单的桌台 → 返回 409
- [ ] 各操作均受商户数据隔离保护

**依赖**：Task-5（完成后解锁）  
**风险**：低

---

#### Task-7：订单管理 + 统计 API

**负责 Agent**：coder（后端）  
**工作内容**：
- `GET /api/v1/admin/orders` — 订单列表（支持 status 筛选、分页，limit=20 default）
- `GET /api/v1/admin/orders/{id}` — 订单详情（含 order_items）
- `PUT /api/v1/admin/orders/{id}/status` — 更新状态（pending→confirmed→paid，或取消）
- `GET /api/v1/admin/stats/today` — 今日经营概览（订单数、营业额、已完成订单数）
- `GET /api/v1/admin/stats/sales` — 销售统计（按日/周/月，支持 date_range 参数）
- 订单号生成：年月日时分秒 + 4位随机数（Task-8 共用）
- 实现订单状态流转校验（不能逆向操作，如 paid→pending）

**验收标准**：
- [ ] 状态流转符合：pending → confirmed → paid / cancelled，不能跳跃
- [ ] 只能查看/操作自己商户的订单
- [ ] stats/today 返回今日订单数、营业额、已完成数
- [ ] stats/sales 支持 day/week/month 粒度
- [ ] 订单号全局唯一，无重复

**依赖**：Task-6（完成后解锁）  
**风险**：中（统计查询 SQL 复杂度）

---

### 【Phase 3】顾客端 API

---

#### Task-8：顾客端 API

**负责 Agent**：coder（后端）  
**工作内容**：
- `GET /api/v1/customer/tables/{table_id}` — 获取桌台信息（验证桌台存在，返回 name/code）
- `GET /api/v1/customer/categories` — 获取有可售菜品的分类列表（过滤 is_available=0）
- `GET /api/v1/customer/dishes` — 菜品列表（支持 category_id 筛选，**只返回 is_available=1**）
- `GET /api/v1/customer/dishes/{id}` — 菜品详情
- `POST /api/v1/customer/orders` — 创建订单（table_id, items[{dish_id, quantity}], remark）
  - 幂等性保护：同一 table_id 在 30 秒内重复提交 → 返回上一笔 pending 订单（前端防抖兜底）
  - 扣减库存（dish is_available 标记，暂不做真实库存数）
- `GET /api/v1/customer/orders/{id}` — 查询订单状态

**验收标准**：
- [ ] 未上架菜品（is_available=0）不在顾客端 API 返回
- [ ] POST /orders 返回订单号、total_amount、status=pending
- [ ] 30秒内同一桌台重复提交 → 返回已创建的 pending 订单，不产生重复订单
- [ ] 菜品价格取下单时刻快照（冗余字段 unit_price）
- [ ] table_id 不存在 → 返回 404

**依赖**：Task-7（完成后解锁）  
**风险**：**高**（微信 H5 鉴权问题，见风险评估）

---

### 【Phase 4】商户后台前端

---

#### Task-9：商户后台 — 登录页 + Dashboard

**负责 Agent**：coder（前端）  
**工作内容**：
- `LoginView.vue`：用户名/密码表单 → 调用 `POST /api/v1/admin/auth/login`
  - 登录成功存 JWT 到 localStorage，跳转 /dashboard
  - 登录失败显示错误提示
- `DashboardView.vue`：今日概览
  - 数字卡片：今日订单数、今日营业额、待接单数
  - 最近 10 条订单列表（时间倒序）
  - 调用 `GET /api/v1/admin/stats/today`
- 全局路由守卫：未登录访问 /dashboard → 重定向 /login

**验收标准**：
- [ ] 正确的 admin/admin123 可登录
- [ ] 错误的用户名密码显示"用户名或密码错误"
- [ ] 刷新页面 JWT 存在则保持登录态
- [ ] JWT 过期后自动跳转登录页
- [ ] Dashboard 数据正确渲染

**依赖**：Task-3（完成后解锁）  
**风险**：低

---

#### Task-10：商户后台 — 分类管理页面

**负责 Agent**：coder（前端）  
**工作内容**：
- `CategoryView.vue`：分类列表（表格）+ 新增/编辑/删除
- 新增弹窗：输入 name、sort_order
- 编辑弹窗：预填当前数据
- 删除确认框（菜品关联检测前端提示）
- 操作后刷新列表

**验收标准**：
- [ ] 增删改查功能完整，无报错
- [ ] 删除有菜品的分类 → 前端提示"请先删除该分类下的菜品"
- [ ] 排序字段 sort_order 控制列表顺序

**依赖**：Task-4（完成后解锁）  
**风险**：低

---

#### Task-11：商户后台 — 菜品管理页面

**负责 Agent**：coder（前端）  
**工作内容**：
- `DishView.vue`：菜品列表（卡片/表格切换视图）
- 支持按分类筛选（联动 CategoryView 的数据）
- 新增/编辑菜品：name, price, description, image_url, category_id, is_available
- 图片预览（image_url 输入后实时预览）
- 上下架开关（is_available toggle）
- 分页（每页 20 条）

**验收标准**：
- [ ] 菜品新增后立即在列表显示
- [ ] 价格输入校验（>0）
- [ ] 图片 URL 预览正确显示
- [ ] 上下架切换立即生效（顾客端能感知）

**依赖**：Task-5（完成后解锁）  
**风险**：低

---

#### Task-12：商户后台 — 桌台管理页面

**负责 Agent**：coder（前端）  
**工作内容**：
- `TableView.vue`：桌台列表（卡片展示：编号、名称、容量）
- 新增/编辑桌台：code（唯一）、name、capacity
- code 重复时后端返回 409，前端提示"桌台编号已存在"
- 删除桌台（确认框）

**验收标准**：
- [ ] code 唯一性校验正确
- [ ] 只能查看/操作自己商户的桌台

**依赖**：Task-6（完成后解锁）  
**风险**：低

---

#### Task-13：商户后台 — 订单管理页面

**负责 Agent**：coder（前端）  
**工作内容**：
- `OrderView.vue`：订单列表（状态 tabs：全部/待接单/已接单/已结账/已取消）
- 列表字段：订单号、桌台、金额、状态、下单时间
- 点击订单 → 展开/跳转详情（含菜品明细）
- 状态操作按钮：
  - pending 订单 → "接单"按钮 → confirmed
  - confirmed 订单 → "结账"按钮 → paid
  - pending/confirmed → "取消"按钮 → cancelled
- 调用 `GET /api/v1/admin/orders`（支持 status 筛选、分页）

**验收标准**：
- [ ] 状态 tabs 正确筛选
- [ ] 各状态按钮流转符合规范
- [ ] 订单详情展示菜品列表（含数量、单价、小计）
- [ ] 状态更新后列表实时刷新

**依赖**：Task-7（完成后解锁）  
**风险**：低

---

### 【Phase 5】顾客端 H5 前端

---

#### Task-14：顾客端 H5 — 菜单页

**负责 Agent**：coder（前端）  
**工作内容**：
- `MenuView.vue`：
  - 顶部：桌台名称（从 `/tables/{table_id}` 获取）
  - 左侧分类导航（CategoryNav.vue）：竖向滚动，点击跳转分类
  - 右侧菜品列表（DishCard.vue）：
    - 展示：图片、名称、价格、描述（截断）
    - 加减数量按钮（购物车联动）
    - 已售罄状态（is_available=0 的视觉区分）
  - 底部吸底购物车栏（CartBar.vue）：显示已选数量和总价，点击跳转 CartView
- 菜品数据来自 `GET /api/v1/customer/dishes`
- 分类数据来自 `GET /api/v1/customer/categories`

**验收标准**：
- [ ] 扫码访问 `/customer/h5?table_id=1` 正确加载菜单
- [ ] 分类切换滚动到对应区域（锚点跳转）
- [ ] 加减数量操作不跳页，实时更新 CartBar
- [ ] is_available=0 的菜品显示"已售罄"标签，不可点击加入购物车

**依赖**：Task-8（完成后解锁）  
**风险**：中（微信 WebView 兼容性）

---

#### Task-15：顾客端 H5 — 购物车 + 下单页

**负责 Agent**：coder（前端）  
**工作内容**：
- `CartView.vue`：
  - 展示已选菜品列表（数量可调整）
  - 总价实时计算
  - 备注输入框（remark）
  - "提交订单"按钮 → `POST /api/v1/customer/orders`
  - 提交后跳转 `/customer/order/{order_id}`（订单状态页）
  - 提交时按钮防抖（1 秒内禁止重复点击）
  - 购物车为空时显示空状态提示

**验收标准**：
- [ ] 购物车数据持久化（刷新不丢失，可用 localStorage）
- [ ] 提交订单成功 → 跳转订单状态页
- [ ] 提交后清空购物车
- [ ] 购物车为空时无法提交（按钮禁用）

**依赖**：Task-14（完成后解锁）  
**风险**：中（幂等性兜底见 Task-8）

---

#### Task-16：顾客端 H5 — 订单状态页

**负责 Agent**：coder（前端）  
**工作内容**：
- `OrderStatusView.vue`：
  - 展示：订单号、总金额、状态、菜品明细列表
  - 状态流转展示（pending/confirmed/paid/cancelled）
  - 轮询：每 5 秒调用 `GET /api/v1/customer/orders/{id}` 刷新状态
  - 状态为 paid → 显示"支付成功"（记账模式：显示"结账完成"）
  - 状态为 cancelled → 显示"订单已取消"
  - 底部"返回菜单"按钮

**验收标准**：
- [ ] 订单状态实时轮询更新
- [ ] 各状态文案和样式正确展示
- [ ] 订单明细正确展示（菜品、数量、价格）
- [ ] 返回菜单 → 跳转 MenuView

**依赖**：Task-15（完成后解锁）  
**风险**：低

---

### 【Phase 6】联调与验收

---

#### Task-17：联调测试 + 冒烟验收

**负责 Agent**：tester（验收主导）+ coder（修复）  
**工作内容**：
- **后端冒烟测试**：用 curl/Postman 逐接口测试 Phase 1~3 所有 API
- **前后端联调**：顾客端 H5 全流程测试（扫码 → 浏览 → 下单 → 查看状态）
- **商户后台全流程**：登录 → 菜品管理 → 桌台管理 → 接单 → 结账
- **边界测试**：
  - 删除有数据的分类/桌台
  - 订单状态逆向操作
  - 重复下单幂等性
  - 登录失败
  - 价格边界值（0、负数、超大数）
- **兼容性测试**：iOS Safari + Android 微信 WebView 各一台真机验证
- **Bug 修复**：记录并关闭所有发现的问题

**验收标准**：
- [ ] 所有 API 接口响应格式统一（统一封装 `{code, data, message}`）
- [ ] 顾客端全流程可跑通（无需截图，覆盖核心路径即可）
- [ ] 商户后台增删改查全链路可用
- [ ] 0 个 P0 级别 Bug 遗留
- [ ] 输出测试报告（BUG_LIST.md）

**依赖**：Task-16（完成后解锁），但可与 Task-9~16 并行部分联调  
**风险**：中（微信 WebView 兼容性不确定，可能发现额外问题）

---

## 三、依赖关系图

```
Task-1 (脚手架)
   │
   ├── Task-2 (数据库) ──── Task-3 (商户认证)
   │                               │
   │                         Task-4 (分类API)
   │                               │
   │                         Task-5 (菜品API)
   │                               │
   │                         Task-6 (桌台API)
   │                               │
   │                         Task-7 (订单+统计API)
   │                               │
   │                         Task-8 (顾客端API) ──────────┐
   │                                                       │
   └──────────────────────────────────────────────────┐    │
                                                        │    │
                                              Task-9 (登录+Dashboard)
                                                        │    │
                                              Task-10 (分类管理页)     │
                                                        │    │
                                              Task-11 (菜品管理页)     │
                                                        │    │
                                              Task-12 (桌台管理页)     │
                                                        │    │
                                              Task-13 (订单管理页)     │
                                                        │    │
                                              Task-14 (菜单页H5)      │
                                                        │    │
                                              Task-15 (购物车+下单页)   │
                                                        │    │
                                              Task-16 (订单状态页)     │
                                                        │    │
                                              Task-17 (联调+验收) ◄────┘
```

---

## 四、风险评估

| # | 风险 | 级别 | 缓解措施 | 涉及任务 |
|---|------|------|---------|---------|
| 1 | **微信 H5 鉴权**（微信内置浏览器 User-Agent 限制，某些微信 API 需要微信授权登录） | **高** | MVP 阶段以 `table_id` 直接访问，跳过微信授权；后续接入微信 JS-SDK | Task-8, Task-14 |
| 2 | **微信 WebView 兼容性**（iOS Safari/Android 微信浏览器 CSS/JS 兼容性差异） | 中 | 真机测试（Task-17）；优先使用标准 CSS，避免实验性特性 | Task-14, Task-15, Task-16 |
| 3 | **SQLite 并发写入**（高并发下写锁竞争） | 中 | MVP 单商户单节点，SQLite 无问题；设计阶段已告知未来可迁移 PostgreSQL | Task-2 |
| 4 | **订单重复提交**（网络抖动导致用户多点一次） | 中 | 后端 30 秒窗口幂等保护（Task-8）+ 前端按钮 1 秒防抖（Task-15） | Task-8, Task-15 |
| 5 | **移动端适配**（H5 页面在各种手机屏幕尺寸表现） | 中 | 使用 rem/vw 单位；关键按钮不低于 44px；参考移动端设计规范 | Task-14, Task-15, Task-16 |
| 6 | **JWT Token 安全**（前端 localStorage 存储 XSS 风险） | 低 | MVP 阶段可接受；生产环境应迁移到 HttpOnly Cookie | Task-3, Task-9 |
| 7 | **图片存储**（image_url 外链可能失效） | 低 | MVP 接受外链；后续接入 OSS/七牛 | Task-5, Task-11 |

---

## 五、验收标准索引（按任务）

| 任务 | 验收项数量 | 关键验收点 |
|------|-----------|-----------|
| Task-1 | 4 | 三服务均可启动 |
| Task-2 | 4 | 建表成功、种子数据可登录 |
| Task-3 | 5 | JWT 正确验证、过期拒绝 |
| Task-4 | 5 | 商户数据隔离、409 保护 |
| Task-5 | 4 | 价格校验、商户隔离 |
| Task-6 | 3 | code 唯一性、商户隔离 |
| Task-7 | 4 | 状态流转、统计正确 |
| Task-8 | 5 | 幂等性、价格快照、商户可见性 |
| Task-9 | 5 | 登录态、Dashboard 渲染 |
| Task-10 | 3 | CRUD 完整、关联删除提示 |
| Task-11 | 4 | 价格校验、图片预览、上下架 |
| Task-12 | 2 | code 唯一性、商户隔离 |
| Task-13 | 4 | 状态流转、实时刷新 |
| Task-14 | 4 | 全流程加载、分类滚动、售罄状态 |
| Task-15 | 4 | 持久化、清空购物车、防抖 |
| Task-16 | 4 | 轮询更新、状态展示、返回菜单 |
| Task-17 | 5 | 全链路可跑通、0 P0 Bug |
