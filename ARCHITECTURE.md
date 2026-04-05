# 扫码点餐系统 - 架构设计文档

> 版本：v1.0  
> 日期：2026-04-02  
> 技术栈：Python FastAPI + SQLite + Vue3

---

## 1. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        微信内嵌 H5 浏览器                         │
│   ┌─────────────────┐    ┌─────────────────┐                   │
│   │   顾客端 (Vue3)  │    │  商户后台 (Vue3)  │                   │
│   │  /customer/h5   │    │  /admin/panel    │                   │
│   └────────┬────────┘    └────────┬────────┘                   │
└────────────┼──────────────────────┼────────────────────────────┘
             │                      │
             ▼                      ▼
┌────────────────────────────────────────────────────────────────┐
│                      FastAPI 后端服务                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ 顾客接口  │  │ 商户接口  │  │ 桌台接口  │  │  统计/报表   │   │
│  │ /api/v1  │  │ /api/v1  │  │ /api/v1  │  │  /api/v1    │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘   │
│       └─────────────┴─────────────┴───────────────┘            │
│                              │                                   │
│                      ┌──────▼──────┐                           │
│                      │   Services  │  (业务逻辑层)              │
│                      └──────┬──────┘                           │
│                             │                                   │
│                      ┌──────▼──────┐                           │
│                      │    ORM      │  (SQLAlchemy)             │
│                      └──────┬──────┘                           │
└──────────────────────────────┼──────────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │     SQLite       │
                    │  scan_order.db   │
                    └──────────────────┘
```

### 架构说明

- **顾客端**：微信内置浏览器访问 H5，无需下载 APP
- **商户后台**：PC 浏览器访问管理后台
- **后端服务**：RESTful API，统一响应格式
- **数据库**：SQLite（轻量、零配置，适合小商户单节点部署）
- **记账模式**：不做微信/支付宝支付，只记录应收、实收，对账用

---

## 2. API 接口列表

### 2.1 顾客端接口（/api/v1/customer）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/categories` | 获取菜品分类列表 |
| GET | `/dishes` | 获取菜品列表（支持分类筛选） |
| GET | `/dishes/{id}` | 获取菜品详情 |
| POST | `/orders` | 创建订单 |
| GET | `/orders/{id}` | 查询订单状态 |
| GET | `/tables/{table_id}` | 获取桌台信息 |

### 2.2 商户后台接口（/api/v1/admin）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/login` | 商户登录 |
| GET | `/categories` | 获取分类列表 |
| POST | `/categories` | 新增分类 |
| PUT | `/categories/{id}` | 编辑分类 |
| DELETE | `/categories/{id}` | 删除分类 |
| GET | `/dishes` | 获取菜品列表 |
| POST | `/dishes` | 新增菜品 |
| PUT | `/dishes/{id}` | 编辑菜品 |
| DELETE | `/dishes/{id}` | 删除菜品 |
| GET | `/tables` | 获取桌台列表 |
| POST | `/tables` | 新增桌台 |
| PUT | `/tables/{id}` | 编辑桌台 |
| DELETE | `/tables/{id}` | 删除桌台 |
| GET | `/orders` | 获取订单列表（支持状态筛选） |
| PUT | `/orders/{id}/status` | 更新订单状态 |
| GET | `/orders/{id}` | 订单详情（含菜品明细） |
| GET | `/stats/today` | 今日经营概览 |
| GET | `/stats/sales` | 销售统计（按日/周/月） |

### 2.3 公共接口（/api/v1）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |

---

## 3. 数据库表结构

### 3.1 商户表（merchant）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| name | TEXT | 商户名称 |
| username | TEXT UNIQUE | 登录用户名 |
| password_hash | TEXT | 密码哈希 |
| created_at | DATETIME | 创建时间 |

### 3.2 分类表（category）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| merchant_id | INTEGER FK | 所属商户 |
| name | TEXT | 分类名称 |
| sort_order | INTEGER | 排序序号 |
| created_at | DATETIME | 创建时间 |

### 3.3 菜品表（dish）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| merchant_id | INTEGER FK | 所属商户 |
| category_id | INTEGER FK | 所属分类 |
| name | TEXT | 菜品名称 |
| price | REAL | 单价（元） |
| description | TEXT | 描述/备注 |
| image_url | TEXT | 图片 URL |
| is_available | INTEGER | 是否可售（0/1） |
| created_at | DATETIME | 创建时间 |

### 3.4 桌台表（table）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| merchant_id | INTEGER FK | 所属商户 |
| code | TEXT | 桌台编号（如"A01"） |
| name | TEXT | 桌台名称（如"靠窗大桌"） |
| capacity | INTEGER | 可容纳人数 |
| created_at | DATETIME | 创建时间 |

### 3.5 订单表（order）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| merchant_id | INTEGER FK | 所属商户 |
| table_id | INTEGER FK | 所属桌台 |
| order_no | TEXT UNIQUE | 订单号（年月日时分秒+随机） |
| total_amount | REAL | 订单总金额 |
| status | TEXT | 状态（pending/confirmed/paid/cancelled） |
| remark | TEXT | 顾客备注 |
| created_at | DATETIME | 下单时间 |
| confirmed_at | DATETIME | 接单时间 |
| paid_at | DATETIME | 结账时间 |

### 3.6 订单明细表（order_item）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| order_id | INTEGER FK | 所属订单 |
| dish_id | INTEGER FK | 菜品 ID |
| dish_name | TEXT | 菜品名称（冗余，下单快照） |
| unit_price | REAL | 单价（冗余，下单快照） |
| quantity | INTEGER | 数量 |
| subtotal | REAL | 小计金额 |

### 订单状态流转

```
pending（待接单） → confirmed（已接单） → paid（已结账）
       ↓                                    ↓
   cancelled（已取消）              （可退款→ cancelled）
```

---

## 4. 目录结构建议

```
scan-order/
├── backend/                          # 后端目录
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI 入口
│   │   ├── config.py                # 配置（数据库路径等）
│   │   ├── database.py              # SQLite / SQLAlchemy 连接
│   │   ├── models/                  # ORM 模型
│   │   │   ├── __init__.py
│   │   │   ├── merchant.py
│   │   │   ├── category.py
│   │   │   ├── dish.py
│   │   │   ├── table.py
│   │   │   └── order.py
│   │   ├── schemas/                 # Pydantic 请求/响应模型
│   │   │   ├── __init__.py
│   │   │   ├── category.py
│   │   │   ├── dish.py
│   │   │   ├── order.py
│   │   │   └── auth.py
│   │   ├── api/                     # 路由层
│   │   │   ├── __init__.py
│   │   │   ├── customer.py          # 顾客端接口
│   │   │   ├── admin.py             # 商户后台接口
│   │   │   └── public.py            # 公共接口
│   │   ├── services/                 # 业务逻辑层
│   │   │   ├── __init__.py
│   │   │   ├── order_service.py
│   │   │   └── stats_service.py
│   │   └── utils/                    # 工具函数
│   │       ├── __init__.py
│   │       └── order_no.py          # 订单号生成
│   ├── requirements.txt
│   └── run.py                       # 启动脚本
│
├── frontend-customer/                # 顾客端 H5（Vue3）
│   ├── src/
│   │   ├── views/
│   │   │   ├── MenuView.vue         # 菜单页
│   │   │   ├── CartView.vue         # 购物车/下单页
│   │   │   └── OrderStatusView.vue  # 订单状态页
│   │   ├── components/
│   │   │   ├── DishCard.vue
│   │   │   ├── CategoryNav.vue
│   │   │   └── CartBar.vue
│   │   ├── api/
│   │   │   └── index.ts
│   │   └── router/
│   │       └── index.ts
│   └── vite.config.ts
│
├── frontend-admin/                   # 商户后台（Vue3）
│   ├── src/
│   │   ├── views/
│   │   │   ├── LoginView.vue
│   │   │   ├── DashboardView.vue    # 今日概览
│   │   │   ├── CategoryView.vue     # 分类管理
│   │   │   ├── DishView.vue         # 菜品管理
│   │   │   ├── TableView.vue        # 桌台管理
│   │   │   ├── OrderView.vue        # 订单管理
│   │   │   └── StatsView.vue        # 销售统计
│   │   └── components/
│   └── vite.config.ts
│
└── ARCHITECTURE.md                   # 本文档
```

---

## 5. 技术风险

| # | 风险 | 级别 | 应对建议 |
|---|------|------|---------|
| 1 | SQLite 并发写入瓶颈 | 中 | SQLite 适合单商户单机部署；多商户或高并发时需迁移 PostgreSQL/MySQL |
| 2 | 微信内 H5 鉴权 | 高 | 微信 H5 需通过微信授权或手机号验证码；当前设计先以 `table_id` 直接访问，补充登录逻辑 |
| 3 | 订单并发重复提交 | 中 | 后端对 `table_id + created_at` 窗口内加唯一约束；前端提交按钮防抖 |
| 4 | 数据备份 | 中 | SQLite 文件定期自动备份；或改用文件型数据库（如 JSON）定时导出 |
| 5 | 打印小票/后厨通知 | 低 | 当前后厨屏暂不做；后续可接入 USB 小票打印机或 WebSocket 推送 |
| 6 | 图片存储 | 低 | 当前 `image_url` 存外链；后续可接入对象存储（OSS/七牛）或本地 static 目录 |
| 7 | 多端登录状态 | 低 | 商户后台用 JWT Token；Token 有效期建议 7 天，支持刷新 |
| 8 | 移动端适配 | 中 | 顾客端 H5 需在 iOS Safari / Android 微信 WebView 验证兼容性 |
