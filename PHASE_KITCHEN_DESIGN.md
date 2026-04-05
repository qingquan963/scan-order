# Phase Kitchen Design - 后厨屏(KDS)模块

> 设计日期：2026-04-03
> 架构师：Architect Subagent
> 版本：v2（第2轮修订）
> 修订说明：增加并发安全、轮询优化、迁移逻辑、错误处理、PIN权限、性能索引、分页支持、数据一致性（updated_at时间戳）

---

## 一、目标概述

为扫码点餐系统设计**后厨显示系统（Kitchen Display System, KDS）**，实现顾客下单后实时推送到后厨屏幕，支持后厨人员高效处理订单。

---

## 二、现有系统分析

### 2.1 技术栈
- **后端**：FastAPI（Python），SQLAlchemy ORM，JWT 认证
- **前端**：Vue3 + Element Plus + Axios，后台管理端
- **数据库**：SQLite（`scan_order.db`）

### 2.2 现有数据模型

**Order（订单）**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | PK |
| table_id | Integer | FK → dining_tables |
| order_number | String | 订单号（唯一） |
| status | String | `pending_payment`, `pending`, `confirmed`, `paid`, `cancelled` |
| total_amount | Float | 总金额 |
| remark | Text | 整单备注 |
| created_at | DateTime | 下单时间 |

**OrderItem（订单项）**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | PK |
| order_id | Integer | FK → orders |
| dish_id | Integer | FK → dishes |
| dish_name | String | 冗余存储菜品名 |
| unit_price | Float | 单价 |
| quantity | Integer | 数量 |
| subtotal | Float | 小计 |
| note | Text | 单菜备注 |

### 2.3 现有订单状态流转
```
pending_payment → pending → confirmed → paid → completed
                    ↓
               cancelled
```

---

## 三、后厨屏数据模型设计

### 3.1 扩展 Order 表

新增 **`kitchen_status`** 字段（订单维度，后厨可见性控制）：

| 值 | 含义 | 说明 |
|----|------|------|
| `pending` | 待接单 | 顾客已付款/下单，待厨房确认 |
| `preparing` | 制作中 | 厨房已接单，正在制作 |
| `completed` | 已完成 | 所有菜品已完成，后厨屏隐藏 |

> 现有 `status` 字段保持不变（顾客端/管理端视角），新增 `kitchen_status` 仅用于后厨屏逻辑。

### 3.2 扩展 OrderItem 表

新增 **`is_done`** 字段（菜品维度，完成状态）：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| is_done | Boolean | False | 菜品是否已完成 |

### 3.3 数据库索引

为提升后厨屏查询性能和分页效率，对以下字段添加索引：

```sql
-- Order 表
CREATE INDEX idx_orders_kitchen_status ON orders(kitchen_status);
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- OrderItem 表
CREATE INDEX idx_order_items_is_done ON order_items(is_done);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
```

> 复合索引 `idx_orders_kitchen_status_created_at` 可进一步优化"待接单/制作中按时间排序"场景。

### 3.4 数据库迁移

```python
# migrate_phase_kitchen.py
# 运行命令: python -m scripts.migrate_phase_kitchen

from sqlalchemy import text
from app.database import engine

def upgrade():
    with engine.begin() as conn:
        # 1. Order 表新增 kitchen_status（默认 NULL，避免影响已存在订单）
        conn.execute(text("ALTER TABLE orders ADD COLUMN kitchen_status VARCHAR(20) DEFAULT NULL"))
        
        # 2. OrderItem 表新增 is_done
        conn.execute(text("ALTER TABLE order_items ADD COLUMN is_done BOOLEAN DEFAULT 0 NOT NULL"))
        
        # 3. Orders 表新增 updated_at（自动更新）
        conn.execute(text("ALTER TABLE orders ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
        
        # 4. 添加索引（SQLite 不支持在线加索引，迁移时一并执行）
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_orders_kitchen_status ON orders(kitchen_status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_order_items_is_done ON order_items(is_done)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id)"))

        # 4. 迁移逻辑调整：已存在订单的 kitchen_status 保持 NULL
        #    新下单由业务逻辑自然流转填充（顾客下单 → status=pending → kitchen_status=pending）
        #    不再自动设为 completed，已存在的历史订单不会出现在后厨屏
        #    （业务自然流转：pending → preparing → completed）

def downgrade():
    with engine.begin() as conn:
        conn.execute(text("DROP INDEX IF EXISTS idx_orders_kitchen_status"))
        conn.execute(text("DROP INDEX IF EXISTS idx_order_items_is_done"))
        conn.execute(text("DROP INDEX IF EXISTS idx_order_items_order_id"))
        conn.execute(text("ALTER TABLE orders DROP COLUMN kitchen_status"))
        conn.execute(text("ALTER TABLE order_items DROP COLUMN is_done"))
```

**迁移逻辑要点（修订）：**
- `kitchen_status` 默认 `NULL` 而非 `pending`，未流转过的历史订单不会进入后厨屏
- 已存在订单无需批量回填，由业务逻辑自然流转：新单 → `kitchen_status=pending`
- `is_done` 默认可为 `False`（新单无完成项）

---

## 四、API 设计

### 4.1 路由前缀
`/api/v1/admin/kitchen`

### 4.2 接口列表

#### ① 获取后厨订单列表（支持分页）
```
GET /api/v1/admin/kitchen/orders
```

**Query 参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| status | string | `preparing` | 筛选状态：`pending`(待接单) / `preparing`(制作中) / `all` |
| page | int | `1` | 页码（从1开始） |
| page_size | int | `50` | 每页条数（上限50） |

**响应：**
```json
{
  "orders": [
    {
      "id": 1,
      "order_number": "20260403001234",
      "table_number": "A01",
      "kitchen_status": "preparing",
      "created_at": "2026-04-03T10:30:00",
      "updated_at": "2026-04-03T10:31:00",
      "remark": "不要辣",
      "items": [
        {
          "id": 101,
          "dish_name": "蒜蓉龙虾",
          "quantity": 2,
          "note": "多蒜蓉",
          "is_done": false
        },
        {
          "id": 102,
          "dish_name": "啤酒鸭",
          "quantity": 1,
          "note": null,
          "is_done": true
        }
      ]
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 50,
  "pages": 1
}
```

**业务逻辑：**
- 返回 `kitchen_status != 'completed'` 的订单（`kitchen_status IS NULL` 或 `!= 'completed'`）
- 按 `created_at` **升序**排列（最早的订单排在最前面，厨房优先处理）
- 如果订单所有 `items` 的 `is_done == True`，则订单 `kitchen_status` 自动变为 `completed`，不出现在列表中
- **`updated_at` 时间戳**：每次 `kitchen_status` 或 `is_done` 变更时更新，前端据此判断数据新鲜度

---

#### ② 接单（厨房确认开始制作）
```
PUT /api/v1/admin/kitchen/orders/{order_id}/accept
```

**请求体：**
```json
{}
```

**响应（成功）：**
```json
{
  "id": 1,
  "kitchen_status": "preparing",
  "updated_at": "2026-04-03T10:31:00",
  "message": "已接单"
}
```

**响应（并发冲突 — 乐观锁失败）：**
```json
{
  "error": "conflict",
  "message": "订单状态已被其他屏幕修改，请刷新重试",
  "current_kitchen_status": "preparing"
}
```

**业务逻辑（并发安全 — 乐观锁）：**
- SQL: `UPDATE orders SET kitchen_status = 'preparing', updated_at = NOW() WHERE id = :id AND kitchen_status = 'pending'`
- `WHERE kitchen_status = 'pending'` 即乐观锁：检查当前状态再更新
- 影响行数为 0 时，说明已被其他屏抢先操作，返回 409 Conflict
- 调用时机：厨房看到新订单后，点击"接单"按钮

---

#### ③ 标记菜品完成
```
PUT /api/v1/admin/kitchen/orders/{order_id}/items/{item_id}/done
```

**请求体：**
```json
{}
```

**响应（成功）：**
```json
{
  "item_id": 101,
  "is_done": true,
  "order_id": 1,
  "order_all_done": false,
  "updated_at": "2026-04-03T10:32:00"
}
```

**响应（并发冲突）：**
```json
{
  "error": "conflict",
  "message": "订单状态已被其他屏幕修改，请刷新重试"
}
```

**业务逻辑：**
- 将 `OrderItem.is_done = True`
- 检查该订单所有 items 是否 `is_done == True`
- 如果全部完成：自动将 `Order.kitchen_status = 'completed'`，订单从后厨屏消失
- 返回 `order_all_done: true` 供前端提示"订单已完成"
- **乐观锁**：基于 item 级别或 order 级别版本号防并发

---

#### ④ 撤销菜品完成（支持误操作）
```
PUT /api/v1/admin/kitchen/orders/{order_id}/items/{item_id}/undone
```
- 响应和错误处理同 ③
- 撤销时如果订单当前 `kitchen_status == 'completed'`，需先将其重置为 `preparing`（乐观锁保护）

---

#### ⑤ 重置订单到待接单（管理员操作）
```
PUT /api/v1/admin/kitchen/orders/{order_id}/reset
```
- 将 `kitchen_status` 重置为 `pending`，所有 `items.is_done = False`
- **乐观锁**：`WHERE kitchen_status = 'preparing'`，冲突时返回 409

---

#### ⑥ PIN 码验证（获取后厨访问令牌）
```
POST /api/v1/admin/kitchen/auth
```

**请求体：**
```json
{
  "pin": "1234"
}
```

**响应（成功）：**
```json
{
  "token": "kitchen_token_xxxxx",
  "expires_in": 28800
}
```

**响应（失败）：**
```json
{
  "error": "unauthorized",
  "message": "PIN 码错误"
}
```

**业务逻辑：**
- 后厨专用固定 PIN 存储于后端 `config.yaml`（`kitchen.pin: "1234"`）
- 返回短期令牌（JWT 或自定义 token，默认 8 小时），后续请求携带
- **不暴露 PIN 明文传输**，仅比对哈希

---

## 五、后厨屏前端页面设计

### 5.1 路由
```
/admin/kitchen
```

### 5.2 PIN 码保护（权限控制）

进入 `/admin/kitchen` 时：
1. 显示 PIN 输入界面（4位数字键盘）
2. 调用 `POST /api/v1/admin/kitchen/auth` 验证
3. 验证通过后缓存 token（`localStorage`），有效期 8 小时
4. 验证失败显示错误提示，重新输入
5. token 过期或无效时，自动弹出 PIN 重新输入

> PIN 固定存储于后端 `config.yaml`，不存储在前端。

```
┌─────────────────────────────┐
│     🍳 后厨中心              │
│                             │
│      请输入 PIN 码           │
│      [ _  _  _  _ ]         │
│                             │
│   [1] [2] [3]               │
│   [4] [5] [6]               │
│   [7] [8] [9]               │
│       [0] [×]               │
│                             │
└─────────────────────────────┘
```

### 5.3 页面布局

```
┌─────────────────────────────────────────────────────────┐
│  🍳 后厨中心          [待接单 3] [制作中 5]    🔄 刷新  │
├─────────────────────────────────────────────────────────┤
│  [Tab: 待接单]  [Tab: 制作中]  [Tab: 已完成(最近)]       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │
│  │ A01     │  │ B03     │  │ A05     │  │ C02     │   │
│  │ 10:30   │  │ 10:25   │  │ 10:20   │  │ 10:15   │   │
│  │─────────│  │─────────│  │─────────│  │─────────│   │
│  │ 蒜蓉龙虾│  │ 啤酒鸭  │  │ 香辣蟹  │  │ 口味虾  │   │
│  │    x2   │  │    x1   │  │    x3   │  │    x2   │   │
│  │[多蒜蓉] │  │  ✅已完 │  │         │  │         │   │
│  │         │  │         │  │         │  │         │   │
│  │[接单✓]  │  │         │  │         │  │         │   │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘   │
│                                                         │
│  ← 第 1 页 / 共 2 页 →                                   │
└─────────────────────────────────────────────────────────┘
```

### 5.4 卡片设计

**订单卡片（Order Card）**

```
┌──────────────────────────┐
│  A01          10:30:22   │  ← 桌台号 + 下单时间
│  ─────────────────────── │
│  ✓ 蒜蓉龙虾    x2        │  ← 已完成项（划线 + 绿色勾）
│     多蒜蓉              │
│  ○ 啤酒鸭      x1        │  ← 未完成项
│  ─────────────────────── │
│  备注：不要辣           │  ← 订单备注（醒目显示）
│  ─────────────────────── │
│  [  接  单  ]            │  ← 仅"待接单"状态显示
└──────────────────────────┘
```

- **待接单**（pending）：橙色边框，大按钮"接单"
- **制作中**（preparing）：蓝色边框，每道菜可点击标记完成
- **已完成**（completed 最近）：绿色，只读展示，供确认

### 5.5 交互设计

| 操作 | 触发 | 效果 |
|------|------|------|
| 输入 PIN | 首次进入 | 调用 auth API，缓存 token |
| 点击"接单"按钮 | 待接单卡片 | 调用 `accept` API，卡片变为"制作中" |
| 点击菜品项 | 制作中卡片 | 调用 `done` API，菜品标记划线✅ |
| 点击已完成菜品 | 制作中卡片 | 调用 `undone` API，撤销完成 |
| 刷新 | 页面刷新按钮 / 自动轮询 | 调用 `GET /orders` 刷新数据 |
| 切换 Tab | 点击 Tab | 筛选不同状态的订单 |
| 分页 | 点击"上一页/下一页" | 调用 `GET /orders?page=N` |

### 5.6 智能轮询机制（修订）

前端 JS 实现，根据当前订单状态动态调整轮询间隔：

```javascript
// kitchenPolling.js

let pollingTimer = null;
let currentOrderCount = 0;

async function fetchOrders(status = 'all', page = 1) {
  try {
    const response = await kitchenApi.getOrders({ status, page });
    currentOrderCount = response.orders.length;

    // 更新页面数据（Vue响应式）
    updateOrderCards(response.orders);

    // 智能调整轮询间隔
    scheduleNextPoll();

  } catch (error) {
    // 错误处理：弹窗提示 + 3秒后重试
    showErrorToast('网络异常，正在重试...');
    setTimeout(() => {
      scheduleNextPoll();
    }, 3000);
  }
}

function scheduleNextPoll() {
  // 清除之前的定时器
  if (pollingTimer) clearTimeout(pollingTimer);

  const interval = currentOrderCount === 0
    ? 30_000   // 无订单时：30秒
    : 5_000;   // 有订单时：5秒

  pollingTimer = setTimeout(() => {
    fetchOrders(getCurrentTabStatus());
  }, interval);
}

// 页面加载时启动轮询
document.addEventListener('DOMContentLoaded', () => {
  fetchOrders('preparing'); // 默认显示制作中
  scheduleNextPoll();
});

// Tab 切换时重新拉取并调整轮询
function switchTab(status) {
  fetchOrders(status);
  scheduleNextPoll();
}
```

**轮询策略：**
| 场景 | 轮询间隔 | 原因 |
|------|----------|------|
| 当前有订单（任意状态） | 5 秒 | 高峰期需要快速同步状态 |
| 当前无订单 | 30 秒 | 降低服务器压力，厨房空闲时无需频繁请求 |
| Tab 切换 | 立即拉取一次 | 确保新 Tab 数据是最新的 |

### 5.7 错误处理（修订）

```javascript
// kitchenApi.js（Axios 拦截器）

api.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config;

    // 网络错误（如断网、超时）
    if (!error.response) {
      showErrorToast('网络异常，正在重试...');
      setTimeout(() => {
        // 3秒后重试一次
        return api.request(originalRequest);
      }, 3000);
      return; // 不再向下传播，避免多个错误提示
    }

    // 409 Conflict：并发冲突（乐观锁失败）
    if (error.response.status === 409) {
      showWarningDialog({
        title: '数据已更新',
        message: error.response.data.message || '订单状态已被其他屏幕修改，请刷新后重试',
        confirmText: '刷新',
        onConfirm: () => window.location.reload()
      });
      return;
    }

    // 401 Unauthorized：PIN token 失效
    if (error.response.status === 401) {
      clearKitchenToken();
      showPinInput(); // 弹出 PIN 重新输入
      return;
    }

    // 其他错误
    showErrorToast(`请求失败: ${error.response.data.message || '未知错误'}`);
    return Promise.reject(error);
  }
);
```

### 5.8 数据新鲜度检测

API 响应中的 `updated_at` 用于前端检测数据一致性：

```javascript
// 每次拉取数据后，比对本地缓存的 updated_at
const cachedUpdatedAt = localStorage.getItem('kitchen_orders_updated_at');
const latestUpdatedAt = response.updated_at; // 列表中最新订单的 updated_at

if (cachedUpdatedAt && new Date(latestUpdatedAt) > new Date(cachedUpdatedAt)) {
  // 服务端有更新，强制刷新
  refreshOrderCards();
}

localStorage.setItem('kitchen_orders_updated_at', latestUpdatedAt);
```

若某订单 `updated_at` 超过 60 秒未变化且处于 `pending` 状态，可显示弱警告（橙色闪烁），提醒厨房及时处理。

### 5.9 组件结构

```
src/views/KitchenView.vue           # 主页面（含 PIN 输入 + 订单列表）
src/components/kitchen/
  PinInput.vue                      # 4位 PIN 输入组件
  OrderCard.vue                     # 订单卡片组件
  KitchenHeader.vue                 # 顶栏（状态统计 + 刷新）
  KitchenTabs.vue                   # Tab 切换
  KitchenPagination.vue             # 分页控件
src/services/kitchenApi.ts         # 后厨 API 调用封装
src/utils/kitchenPolling.ts         # 智能轮询逻辑（独立模块）
```

---

## 六、技术实现清单

### 6.1 后端文件变更

| 文件 | 变更内容 |
|------|----------|
| `backend/models/models.py` | Order 新增 `kitchen_status`（默认NULL）+ `updated_at`，OrderItem 新增 `is_done` |
| `backend/app/schemas/kitchen.py` | **新建** — KitchenOrderResponse（含 updated_at）、KitchenItemResponse、PIN 验证请求/响应 |
| `backend/app/api/v1/admin.py` | 注册 kitchen_router |
| `backend/app/api/v1/endpoints/kitchen.py` | **新建** — 后厨所有 API（含乐观锁 + PIN 验证） |
| `backend/migrations/migrate_phase_kitchen.py` | **新建** — 数据库迁移脚本（含索引） |
| `backend/services/kitchen_service.py` | **新建** — 后厨业务逻辑（乐观锁实现） |
| `backend/config.yaml` | 新增 `kitchen.pin` 配置项 |

### 6.2 前端文件变更

| 文件 | 变更内容 |
|------|----------|
| `frontend-admin/src/router/index.ts` | 新增 `/admin/kitchen` 路由 |
| `frontend-admin/src/services/kitchenApi.ts` | **新建** — API 调用封装（含 401/409 处理） |
| `frontend-admin/src/utils/kitchenPolling.ts` | **新建** — 智能轮询逻辑 |
| `frontend-admin/src/views/KitchenView.vue` | **新建** — 后厨屏主页面（含 PIN 保护） |
| `frontend-admin/src/components/kitchen/` | **新建目录** — 子组件（PinInput、OrderCard、KitchenHeader、KitchenTabs、KitchenPagination） |
| `frontend-admin/package.json` | 无需新增依赖（Vue3 + Element Plus + Axios 已有） |

### 6.3 后端配置变更

```yaml
# config.yaml 新增
kitchen:
  pin: "1234"          # 后厨4位PIN码（生产环境建议复杂密码）
  token_ttl: 28800     # token有效期（秒），默认8小时
```

---

## 七、状态流转总览

### 7.1 订单维度（kitchen_status）

```
pending → preparing → completed
    │           │
    │           └── 所有 item.is_done == True 时自动触发
    │
    └── 厨房点击"接单"触发（乐观锁保护）
```

### 7.2 菜品维度（is_done）

```
False → True → False (undo)
   │       │
   │       └── 点击菜品标记完成（乐观锁保护）
   └── 初始化 / 撤销操作
```

### 7.3 完整订单生命周期

```
顾客下单
   ↓
商户后台确认付款 → status: pending → kitchen_status: pending (新单默认)
   ↓
后厨屏看到订单 → 点击"接单"（乐观锁） → kitchen_status: preparing
   ↓
逐个完成菜品 → is_done: True（乐观锁）
   ↓
全部完成 → kitchen_status: completed → 订单从后厨屏消失
   ↓
订单 status 后续流转（paid → completed）
```

### 7.4 并发安全 — 乐观锁模式

```
后厨屏A                    后厨屏B                    数据库
   │                          │                          │
   │  GET /orders             │                          │
   │─────────────────────────>│                          │
   │  kitchen_status=pending  │                          │
   │<─────────────────────────│                          │
   │                          │                          │
   │  PUT /accept             │                          │
   │  (WHERE status='pending')│                          │
   │─────────────────────────>│  UPDATE ...              │
   │  200 OK                  │  WHERE kitchen_status=   │
   │<─────────────────────────│  'pending' (1 row)       │
   │                          │                          │
   │                          │  PUT /accept             │
   │                          │  (WHERE status='pending')│
   │                          │─────────────────────────>│
   │                          │  409 Conflict (0 rows)   │
   │                          │<─────────────────────────│
   │                          │  → 弹窗"已被其他屏修改" │
```

---

## 八、关键设计决策

### 8.1 轮询 vs WebSocket

| 维度 | 轮询（采用） | WebSocket |
|------|-------------|-----------|
| 实现复杂度 | 低 | 高 |
| 实时性 | 5~30秒动态 | 实时 |
| 多屏支持 | 天然 | 需要广播机制 |
| 断线重连 | 自动 | 需要心跳机制 |
| 服务器压力 | 较低 | 维护长连接开销 |
| 推荐场景 | 初版上线 | 高峰期 > 100单/分钟 |

**结论**：初版采用 **智能轮询（5秒/30秒动态）**，后续如需更高实时性可升级 WebSocket。

### 8.2 kitchen_status vs 复用 status 字段

| 方案 | 优点 | 缺点 |
|------|------|------|
| 新增 kitchen_status（采用） | 解耦，顾客端状态不受影响 | 多一个字段 |
| 复用现有 status | 无需改表 | 混淆顾客端和管理端语义 |

### 8.3 乐观锁 vs 悲观锁

| 方案 | 优点 | 缺点 |
|------|------|------|
| 乐观锁（采用）：`WHERE status = expected` | 性能高，无锁竞争，适合多屏并发 | 并发冲突时需重试 |
| 悲观锁：`SELECT ... FOR UPDATE` | 一定能成功 | 阻塞其他写操作，高并发时有性能瓶颈 |

**结论**：后厨屏并发冲突是小概率事件（两屏同时操作同一订单），乐观锁 + 409 返回前端刷新是最佳平衡。

### 8.4 PIN 码存储安全

- PIN 明文不传输，前端传递到后端后比对 bcrypt/sha256 哈希
- 后端 `config.yaml` 存储哈希值，不存储明文
- token 默认 8 小时过期，到期需重新输入 PIN

---

## 九、验收标准

1. ✅ 顾客下单后，新订单在 ≤5 秒内出现在后厨屏
2. ✅ 后厨屏显示：桌台号、菜品列表（含数量）、单菜备注、整单备注、`updated_at` 时间戳
3. ✅ 后厨人员能清晰分辨"待接单"和"制作中"订单
4. ✅ 按下单时间升序排列（最早的订单在最前面）
5. ✅ 点击菜品能标记完成，已完成项视觉上明显区分
6. ✅ 所有菜品完成，订单自动从后厨屏消失
7. ✅ 多台后厨屏同时使用，数据一致（乐观锁保护）
8. ✅ 页面有 4 位 PIN 码保护（明厨固定 PIN，存储于后端 config）
9. ✅ 进入页面时显示 PIN 输入界面
10. ✅ 网络错误时弹窗提示 + 3秒后自动重试
11. ✅ 无订单时轮询间隔 30 秒，有订单时 5 秒
12. ✅ 支持分页（每页 50 条）
13. ✅ `kitchen_status` 和 `is_done` 字段有数据库索引
14. ✅ API 响应包含 `updated_at` 时间戳，前端可检测数据新鲜度
15. ✅ `kitchen_status` 默认 NULL，已存在订单不自动填充

---

## 十、后续扩展方向（Phase 2 后厨）

- **WebSocket 推送**：商户接单时主动推送到后厨屏（0延迟）
- **菜品分类分组**：同一订单按菜品类别分组（如"凉菜区""热菜区"）
- **超时预警**：订单超过 N 分钟未完成，高亮提醒
- **打印联动**：接单时自动打印厨房小票
- **后厨叫号**：完成后语音/声音提醒
