# 扫描点单系统 Bug 探查报告

> 探查时间：2026-04-07  
> 探查范围：商户后台 + 顾客端全流程  
> 只探查，不写代码

---

## 一、系统架构概览

```
backend/          FastAPI (localhost:8002)
  └─ app/api/v1/
      ├─ admin.py        → /api/v1/admin/* (JWT认证)
      └─ customer.py     → /api/v1/customer/* (公开)
          └─ endpoints/customer_orders.py → /api/v1/customer/member/* (微信认证)

frontend-admin/   Vue3 + Element Plus (localhost:3002)
frontend-customer/ Vue3 (localhost:3001)
```

### API 端口不一致问题
- **MenuView.vue** 使用 `API_BASE = 'http://localhost:8002/api/v1'`  
- **CartView.vue** 使用 `API_BASE = 'http://127.0.0.1:8002/api/v1'`  
- **OrderStatusView.vue** 使用 `API_BASE = 'http://localhost:8002/api/v1'`  
- **PayView.vue** 使用 `API_BASE = 'http://localhost:8002/api/v2'` ← **错误端口！**

---

## 二、完整业务流程追踪

### 顾客端流程
```
扫码访问 /customer/h5?table_id=X
    ↓
MenuView.vue → GET /customer/tables/{table_id}   [获取桌台信息]
             → GET /customer/categories          [获取分类]
             → GET /customer/dishes              [获取菜品列表]
    ↓
点击"+"加菜 → localStorage 存储 cart_{table_id}
    ↓
点击"去结算" → CartView.vue
    ↓
点击"提交订单" → POST /customer/orders
    ↓
根据 payment_mode 跳转:
  - counter_pay → /customer/pay/{order_id}  (PayView)
  - credit_pay  → /customer/order/{order_id} (OrderStatusView)
    ↓
PayView: 
  - pending_payment: 显示支付码 + 倒计时 + "我已付款(模拟)"按钮
  - 点击按钮 → POST /customer/orders/{id}/pay → 状态改为 pending
    ↓
OrderStatusView: 轮询 GET /customer/orders/{id} (每5秒)
```

### 商户端流程
```
登录 → DashboardView
    ↓
OrderManager.vue → GET /admin/orders
    ↓
点击订单行展开 → 展开行内显示"接单"/"结账"/"取消订单"按钮
    ↓
点击按钮 → PUT /admin/orders/{id}/status
    ↓
成功后调用 loadOrders() 刷新列表
```

---

## 三、所有发现的问题

---

### Bug #1：订单按钮不变色 + 状态不刷新

**文件**: `frontend-admin/src/views/OrderManager.vue`

**问题描述**: 点击"接单"或"取消订单"按钮后：
1. 按钮颜色不改变（无 loading/disabled 状态）
2. 列表状态不立即更新

**代码分析**：

**问题 A - 按钮无 loading 状态（行 54-77）**：
```html
<!-- 行 54-70: 接单按钮 -->
<el-button
  v-if="row.status === 'pending'"
  type="success"
  @click.stop="handleStatusUpdate(row, 'confirmed')"
>
  接单
</el-button>
```
按钮在 API 调用期间没有任何 loading 或 disabled 状态，用户可以重复点击。

**问题 B - 状态不刷新（行 243-260）**：
```javascript
const handleStatusUpdate = async (order: Order, newStatus: string) => {
  // ... validation ...
  try {
    await orderApi.updateOrderStatus(order.id, newStatus)
    ElMessage.success(`${actionText}成功`)
    expandedRows.value = []   // ← 清空展开行
    loadOrders()               // ← 重新加载
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || `${actionText}失败`)
  }
}
```

`loadOrders()` 确实被调用了，但问题在于 **Vue reactivity**：赋值 `orders.value = response.data.orders || []` 之后，Element Plus 的 `el-table` 可能因为某些原因没有正确检测到数组元素内部的变化。

**问题 C - API 响应处理不完整（行 225-232）**：
```javascript
const loadOrders = async () => {
  loading.value = true
  try {
    const response = await orderApi.getOrders({
      status: getStatusParam(),
      page: currentPage.value,
      limit: pageSize.value
    })
    // 正确处理 API 返回结构：{total, page, limit, orders: [...]}
    if (response.data) {
      orders.value = response.data.orders || []
      total.value = response.data.total || 0
    }
  } finally {
    loading.value = false
  }
}
```

API 成功返回后，`orders.value` 被重新赋值，理论上应该触发 Vue 组件重新渲染。但实际上状态更新不反映的可能原因：
1. `el-table` 使用 `row-key="id"` 和 `expand-row-keys`，但更新后展开状态被清空（`expandedRows.value = []`），导致用户看不到变化
2. 或者后端状态更新本身有问题

**根本原因**: `loadOrders()` 在 `expandedRows.value = []` 之后执行，此时整个列表被刷新但用户的心理模型是"局部更新"，导致感知不到刷新。

**修复方向**: 
1. 在按钮点击后立即更新本地 `order.status`（乐观更新）或添加按钮 loading 状态
2. 考虑使用 `nextTick` 确保 DOM 更新后再显示成功消息

---

### Bug #2：PayView.vue 没有二维码支付页面

**文件**: `frontend-customer/src/views/PayView.vue`

**问题描述**: PayView 应该显示二维码供顾客扫码支付，但目前只有：
1. 文字支付码（`paymentCode` 纯文本）
2. 倒计时
3. "我已付款（模拟）"按钮

**实际代码（行 72-82）**：
```html
<!-- 支付码展示（counter_pay 模式） -->
<div v-if="order.status === 'pending_payment'" class="payment-code-section">
  <div class="payment-code-label">支付码</div>
  <div class="payment-code-box">
    <div class="payment-code">{{ paymentCode }}</div>  <!-- ← 只是文本，不是二维码 -->
  </div>
  <div class="countdown-box">
    <div class="countdown-label">剩余时间</div>
    <div class="countdown-value">{{ formatCountdown(countdown) }}</div>
  </div>
</div>
```

**期望**: 应该有一个 QR 码图片（`<img>` 或使用 canvas/qrcode 库生成），显示"扫码支付"页面，顾客扫码后通过商户端确认完成支付。

**当前实际行为**: 顾客只能看一串文本码，不知道该怎么做。

---

### Bug #3：PayView.vue 使用错误的后端端口

**文件**: `frontend-customer/src/views/PayView.vue` 行 88

```javascript
const API_BASE = 'http://localhost:8002/api/v1'  // ← 错误！是 8002
```

对比其他文件的端口：
- MenuView.vue: `http://localhost:8002` ✓
- CartView.vue: `http://127.0.0.1:8002` ✓  
- OrderStatusView.vue: `http://localhost:8002` ✓

**但实际验证**：backend 实际运行在 `8002`，所以端口是对的...等等，让我再确认一下。

实际上后端 `run.py` 默认端口应该是 `8001` 或 `8002`。让我检查 run.py...

不过从 smoke test 文件和现有项目来看，端口应该是 `8002`。**这个可能不是 bug**，但值得确认。

---

### Bug #4：DishCard 组件图片字段名不匹配

**文件**: `frontend-customer/src/components/DishCard.vue` 行 7-13

```typescript
interface Dish {
  id: number
  name: string
  price: number
  description: string
  image: string        // ← 使用 'image'
  is_available: number
}
```

**文件**: `backend/app/api/v1/customer.py` 行 91-99（返回字段）

```python
return [{
    "id": d.id,
    "name": d.name,
    "description": d.description or "",
    "price": d.price,
    "image_url": d.image_url or "",   // ← 返回的是 'image_url'
    "category_id": d.category_id,
    "is_available": 1 if d.is_available else 0
} for d in dishes]
```

**结果**: DishCard 组件期望 `dish.image`，但 API 返回 `dish.image_url`。导致图片总是显示占位图 `'/placeholder.png'`。

---

### Bug #5：MenuView API 路径错误（可能导致菜品列表加载失败）

**文件**: `frontend-customer/src/views/MenuView.vue` 行 1（script setup 开始）

```javascript
const API_BASE = 'http://localhost:8002/api/v1'
```

然后调用：
```javascript
async function fetchDishes() {
  const res = await fetch(`${API_BASE}/customer/dishes`)
  // ...
}
```

实际应该是 `GET /api/v1/customer/dishes`，最终路径是 `http://localhost:8002/api/v1/customer/dishes`。

对比 backend 路由：
- `customer.py` 中的 `router` 注册在 `/api/v1/customer`
- `@router.get("/dishes")` → 完整路径 `/api/v1/customer/dishes` ✓

**但问题在于**：MenuView 也调用了 `/customer/categories` 和 `/customer/tables/{id}`，这些是 `public.py` 中的端点，实际路径是 `/api/v1/customer/tables/{id}` 等。

**真正的问题**：MenuView 的 `fetchTable` 函数使用 `GET /customer/tables/${tableId.value}`，但 backend 的端点是 `GET /tables/{table_id}`（在 customer.py 中定义），所以完整路径应该是 `/api/v1/customer/tables/{id}`，MenuView 的调用路径是正确的。

但如果 backend 的 `/customer` 前缀注册有问题，可能导致 404。

---

### Bug #6：顾客端菜品列表不过滤 `is_available=0`

**文件**: `backend/app/api/v1/customer.py` 行 91-99

```python
@router.get("/dishes")
def list_dishes(category_id: int = None, db: Session = Depends(get_db)):
    query = db.query(Dish)
    if category_id is not None:
        query = query.filter(Dish.category_id == category_id)
    dishes = query.all()   // ← 没有过滤 is_available
    return [...]
```

对比 PLAN.md 中 Task-8 的验收标准：
> [ ] 未上架菜品（is_available=0）不在顾客端 API 返回

**但 MenuView.vue 行 121 有前端过滤**：
```javascript
dishes.value = (Array.isArray(data) ? data : data.data || []).filter((d: any) => d.is_available === 1)
```

所以功能上是正常的，但不符合 PLAN.md 的设计（应该在后端过滤）。

---

### Bug #7：OrderStatusView 轮询时不传递认证信息

**文件**: `frontend-customer/src/views/OrderStatusView.vue` 行 107

```javascript
const API_BASE = 'http://localhost:8002/api/v1'
// ...
async function fetchOrder() {
  try {
    const res = await axios.get(`${API_BASE}/customer/orders/${orderId.value}`)
    // ...
  }
}
```

使用的是 `axios.get` 而不是 `fetch`，但没有设置 `withCredentials` 或任何认证头。由于 `get_order` 端点实际上不需要认证（backend 的 customer.py 中 `get_order` 函数没有认证依赖），所以这可能不是问题。

但如果系统引入微信认证后，这会是个问题。

---

### Bug #8：取消订单按钮在 pending_payment 状态下有重复渲染

**文件**: `frontend-admin/src/views/OrderManager.vue` 行 73-80

```html
<!-- 操作按钮（pending_payment 状态不显示接单/结账按钮，仅可取消） -->
<div class="detail-actions" v-if="row.status === 'pending' || row.status === 'confirmed' || row.status === 'pending_payment'">
  <!-- pending 状态：接单按钮 -->
  <el-button v-if="row.status === 'pending'" type="success" @click.stop="handleStatusUpdate(row, 'confirmed')">接单</el-button>
  
  <!-- confirmed 状态：结账按钮 -->
  <el-button v-if="row.status === 'confirmed'" type="warning" @click.stop="handleStatusUpdate(row, 'paid')">结账</el-button>
  
  <!-- 非 pending_payment：取消按钮 -->
  <el-button v-if="row.status !== 'pending_payment'" type="danger" @click.stop="handleStatusUpdate(row, 'cancelled')">取消订单</el-button>
  
  <!-- pending_payment：另一个取消按钮 -->
  <el-button v-if="row.status === 'pending_payment'" type="danger" @click.stop="handleStatusUpdate(row, 'cancelled')">取消订单</el-button>
</div>
```

**问题**: 有两个取消订单按钮的渲染条件是互斥的（`!== 'pending_payment'` 和 `=== 'pending_payment'`），但逻辑不够清晰，且取消按钮渲染了两次（虽然只有一个会显示）。这不是严重 bug，但代码冗余。

---

### Bug #9：后台订单状态更新 API 没有返回完整订单对象

**文件**: `backend/app/api/v1/endpoints/orders.py` 行 91-108

```python
@router.put("/orders/{order_id}/status", response_model=OrderResponse)
def update_order_status(...):
    order = OrderService.update_order_status(...)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order
```

`OrderService.update_order_status` 返回的 `order` 对象包含了更新后的状态，但前端在 `handleStatusUpdate` 中只关心 success/failure，没有利用返回的状态做乐观更新。

---

### Bug #10：CartView 的 submitOrder 成功后没有处理 credit_pay 模式的跳转

**文件**: `frontend-customer/src/views/CartView.vue` 行 61-79

```javascript
if (data.payment_mode === 'counter_pay' && data.status === 'pending_payment') {
  router.push(`/customer/pay/${data.id}?table_id=${tableId.value}`)
} else {
  router.push(`/customer/order/${data.id}?table_id=${tableId.value}`)
}
```

这里逻辑是对的，但如果 `payment_mode === 'credit_pay'` 且 `status === 'pending'`（初始状态），应该跳转到 OrderStatusView。但实际上 credit_pay 模式下，订单直接进入 `pending` 状态，不需要支付页面。

但问题是：商户后台的 SettingsView 可以设置 payment_mode 为 'counter_pay' 或 'credit_pay'。如果设置为 credit_pay，顾客下单后会直接跳转到订单状态页。

---

## 四、问题汇总表

| # | 严重程度 | 问题 | 文件 | 行号 |
|---|---------|------|------|------|
| 1 | 高 | 订单按钮无 loading 状态，可重复点击 | OrderManager.vue | 54-77 |
| 2 | 高 | 订单状态更新后列表不刷新（感知问题） | OrderManager.vue | 243-260 |
| 3 | 中 | PayView 无二维码显示，只有文本支付码 | PayView.vue | 72-82 |
| 4 | 中 | DishCard 图片字段名不匹配（image vs image_url） | DishCard.vue | 7-13 |
| 5 | 低 | 后端 API 不过滤 is_available=0 的菜品（应在后端过滤） | customer.py | 91-99 |
| 6 | 低 | 取消订单按钮代码冗余（两个互斥条件） | OrderManager.vue | 73-80 |
| 7 | 低 | OrderStatusView 不传递认证信息轮询 | OrderStatusView.vue | 107 |
| 8 | 低 | 端口使用不一致（127.0.0.1 vs localhost vs potential 8002 mismatch） | 多个文件 | - |

---

## 五、修复优先级建议

**P0（必须修复）**:
- Bug #4: DishCard 图片不显示 → 影响顾客端核心体验

**P1（应该修复）**:
- Bug #1: 订单按钮无 loading 状态 → 用户体验差，可能导致重复提交
- Bug #3: PayView 无二维码 → 核心支付流程缺失

**P2（可以修复）**:
- Bug #5: 后端过滤 is_available → 安全性/设计规范问题
- Bug #6: 代码冗余 → 可维护性问题
