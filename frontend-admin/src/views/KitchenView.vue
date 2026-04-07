<template>
  <div class="kitchen-view">
    <!-- PIN 输入界面 -->
    <div v-if="!isAuthenticated" class="pin-screen">
      <div class="pin-card">
        <div class="pin-icon">🍳</div>
        <h2>后厨中心</h2>
        <p class="pin-hint">请输入 PIN 码</p>
        <div class="pin-dots">
          <span v-for="i in 4" :key="i" :class="{ filled: pin.length >= i }">●</span>
        </div>
        <p v-if="pinError" class="pin-error">{{ pinError }}</p>
        <div class="pin-keypad">
          <button v-for="n in [1,2,3,4,5,6,7,8,9]" :key="n" @click="pushDigit(n)" class="key-btn">{{ n }}</button>
          <button @click="clearPin" class="key-btn clear">×</button>
          <button @click="pushDigit(0)" class="key-btn">0</button>
          <button @click="backspace" class="key-btn backspace">⌫</button>
        </div>
      </div>
    </div>

    <!-- 后厨主界面 -->
    <div v-else class="kitchen-main">
      <!-- 顶栏 -->
      <div class="kitchen-header">
        <div class="header-left">
          <span class="header-icon">🍳</span>
          <span class="header-title">后厨中心</span>
        </div>
        <div class="header-stats">
          <el-tag type="warning" size="large">待接单 {{ stats.pending }}</el-tag>
          <el-tag type="primary" size="large">制作中 {{ stats.preparing }}</el-tag>
        </div>
        <div class="header-actions">
          <el-button @click="refresh" :loading="loading" circle title="刷新">
            <span style="font-size:18px">🔄</span>
          </el-button>
          <el-button @click="logout" circle title="退出">
            <span style="font-size:18px">🚪</span>
          </el-button>
        </div>
      </div>

      <!-- Tab 切换 -->
      <div class="kitchen-tabs">
        <el-tabs v-model="activeTab" @tab-change="onTabChange">
          <el-tab-pane label="待接单" name="pending">
            <span slot="label"><el-badge :value="stats.pending" :hidden="stats.pending === 0" type="warning"> 待接单</el-badge></span>
          </el-tab-pane>
          <el-tab-pane label="制作中" name="preparing">
            <span slot="label"><el-badge :value="stats.preparing" :hidden="stats.preparing === 0" type="primary"> 制作中</el-badge></span>
          </el-tab-pane>
          <el-tab-pane label="已完成（最近）" name="all"></el-tab-pane>
        </el-tabs>
      </div>

      <!-- 订单列表 -->
      <div class="order-list" v-if="!loading && orders.length > 0">
        <div class="order-grid">
          <OrderCard
            v-for="order in orders"
            :key="order.id"
            :order="order"
            @accept="onAccept"
            @item-done="onItemDone"
            @item-undone="onItemUndone"
            @reset="onReset"
          />
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="!loading" class="empty-state">
        <div class="empty-icon">🍽️</div>
        <p>{{ activeTab === 'all' ? '暂无已完成订单' : '暂无' + tabLabel + '订单' }}</p>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading && orders.length === 0" class="loading-state">
        <el-icon class="is-loading" :size="40"><Loading /></el-icon>
        <p>加载中...</p>
      </div>

      <!-- 分页 -->
      <div class="pagination-bar" v-if="totalPages > 1">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="onPageChange"
        />
      </div>

      <!-- 冲突提示弹窗 -->
      <el-dialog
        v-model="conflictDialogVisible"
        title="数据已更新"
        width="400px"
        :close-on-click-modal="false"
      >
        <p>订单状态已被其他屏幕修改，请刷新后重试。</p>
        <template #footer>
          <el-button type="primary" @click="conflictDialogVisible = false; refresh()">刷新</el-button>
        </template>
      </el-dialog>

      <!-- 网络错误提示 -->
      <el-dialog
        v-model="networkDialogVisible"
        title="网络异常"
        width="350px"
        :close-on-click-modal="false"
      >
        <p>网络连接异常，将于 3 秒后自动重试...</p>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElIcon } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { kitchenAuthApi, kitchenOrderApi } from '@/services/kitchenApi'

// ─── 类型定义 ────────────────────────────────────────────────

interface KitchenItem {
  id: number
  dish_name: string
  quantity: number
  note: string | null
  is_done: boolean
}

interface KitchenOrder {
  id: number
  order_number: string
  table_number: string
  kitchen_status: string | null
  created_at: string
  updated_at: string | null
  remark: string | null
  items: KitchenItem[]
}

// ─── 状态 ────────────────────────────────────────────────────

const isAuthenticated = ref(!!localStorage.getItem('kitchen_token'))
const pin = ref('')
const pinError = ref('')
const activeTab = ref('preparing')
const currentPage = ref(1)
const pageSize = ref(50)
const total = ref(0)
const totalPages = computed(() => Math.ceil(total.value / pageSize.value) || 1)
const orders = ref<KitchenOrder[]>([])
const loading = ref(false)
const conflictDialogVisible = ref(false)
const networkDialogVisible = ref(false)

const stats = reactive({ pending: 0, preparing: 0 })

let pollingTimer: ReturnType<typeof setTimeout> | null = null

// ─── 计算属性 ────────────────────────────────────────────────

const tabLabel = computed(() => {
  return { pending: '待接单', preparing: '制作中', all: '已完成' }[activeTab.value] || ''
})

// ─── PIN 输入 ────────────────────────────────────────────────

function pushDigit(d: number) {
  if (pin.value.length < 4) {
    pin.value += String(d)
    pinError.value = ''
    if (pin.value.length === 4) {
      doLogin()
    }
  }
}

function clearPin() {
  pin.value = ''
  pinError.value = ''
}

function backspace() {
  pin.value = pin.value.slice(0, -1)
  pinError.value = ''
}

async function doLogin() {
  try {
    const res = await kitchenAuthApi.login(pin.value)
    localStorage.setItem('kitchen_token', res.data.token)
    isAuthenticated.value = true
    pin.value = ''
    ElMessage.success('验证成功')
    await fetchOrders()
    scheduleNextPoll()
  } catch (e: any) {
    pinError.value = 'PIN 码错误'
    pin.value = ''
  }
}

function logout() {
  localStorage.removeItem('kitchen_token')
  isAuthenticated.value = false
  clearPolling()
}

// ─── 数据获取 ────────────────────────────────────────────────

async function fetchOrders() {
  if (!isAuthenticated.value) return
  loading.value = true
  try {
    const statusParam = activeTab.value === 'all' ? 'all' : activeTab.value
    const res = await kitchenOrderApi.getOrders({
      status: statusParam,
      page: currentPage.value,
      page_size: pageSize.value
    })
    orders.value = res.data.orders
    total.value = res.data.total

    // 更新统计（不改变当前 tab）
    await fetchStats()
  } catch (e: any) {
    if (e.unauthorized) {
      isAuthenticated.value = false
      ElMessage.warning('会话已过期，请重新输入 PIN')
    } else if (e.networkError) {
      handleNetworkError()
    }
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const [pendingRes, preparingRes] = await Promise.all([
      kitchenOrderApi.getOrders({ status: 'pending', page: 1, page_size: 1 }),
      kitchenOrderApi.getOrders({ status: 'preparing', page: 1, page_size: 1 })
    ])
    stats.pending = pendingRes.data.total
    stats.preparing = preparingRes.data.total
  } catch {
    // 静默失败
  }
}

function refresh() {
  currentPage.value = 1
  fetchOrders()
}

// ─── Tab / 分页切换 ─────────────────────────────────────────

function onTabChange() {
  currentPage.value = 1
  fetchOrders()
  scheduleNextPoll()
}

function onPageChange() {
  fetchOrders()
}

// ─── 操作 ───────────────────────────────────────────────────

async function onAccept(orderId: number) {
  try {
    await kitchenOrderApi.acceptOrder(orderId)
    ElMessage.success('已接单')
    await fetchOrders()
    scheduleNextPoll()
  } catch (e: any) {
    if (e.conflict) {
      conflictDialogVisible.value = true
    } else {
      ElMessage.error((e.response?.data?.detail) || '操作失败')
    }
  }
}

async function onItemDone(orderId: number, itemId: number) {
  try {
    const res = await kitchenOrderApi.markItemDone(orderId, itemId)
    // 更新本地状态
    const order = orders.value.find(o => o.id === orderId)
    if (order) {
      const item = order.items.find(i => i.id === itemId)
      if (item) item.is_done = true
    }
    if (res.data.order_all_done) {
      ElMessage.success('订单已完成！')
      await fetchOrders()
    }
    scheduleNextPoll()
  } catch (e: any) {
    if (e.conflict) {
      conflictDialogVisible.value = true
    } else {
      ElMessage.error((e.response?.data?.detail) || '操作失败')
    }
  }
}

async function onItemUndone(orderId: number, itemId: number) {
  try {
    await kitchenOrderApi.markItemUndone(itemId)
    ElMessage.success('已撤销')
    await fetchOrders()
    scheduleNextPoll()
  } catch (e: any) {
    if (e.conflict) {
      conflictDialogVisible.value = true
    } else {
      ElMessage.error((e.response?.data?.detail) || '操作失败')
    }
  }
}

async function onReset(orderId: number) {
  try {
    await kitchenOrderApi.resetOrder(orderId)
    ElMessage.success('订单已重置')
    await fetchOrders()
    scheduleNextPoll()
  } catch (e: any) {
    if (e.conflict) {
      conflictDialogVisible.value = true
    } else {
      ElMessage.error((e.response?.data?.detail) || '操作失败')
    }
  }
}

// ─── 智能轮询 ────────────────────────────────────────────────

function scheduleNextPoll() {
  if (pollingTimer) {
    clearTimeout(pollingTimer)
    pollingTimer = null
  }
  const hasOrders = stats.pending > 0 || stats.preparing > 0
  const interval = hasOrders ? 5000 : 30000
  pollingTimer = setTimeout(() => {
    fetchOrders()
    scheduleNextPoll()
  }, interval)
}

function clearPolling() {
  if (pollingTimer) {
    clearTimeout(pollingTimer)
    pollingTimer = null
  }
}

// ─── 网络错误处理 ───────────────────────────────────────────

function handleNetworkError() {
  networkDialogVisible.value = true
  setTimeout(() => {
    networkDialogVisible.value = false
    fetchOrders()
    scheduleNextPoll()
  }, 3000)
}

// ─── 生命周期 ────────────────────────────────────────────────

onMounted(async () => {
  if (isAuthenticated.value) {
    await fetchOrders()
    scheduleNextPoll()
  }
})

onUnmounted(() => {
  clearPolling()
})
</script>

<!-- OrderCard 子组件（内联） -->
<script lang="ts">
import { defineComponent, type PropType } from 'vue'

const OrderCard = defineComponent({
  name: 'OrderCard',
  props: {
    order: { type: Object as PropType<any>, required: true }
  },
  emits: ['accept', 'item-done', 'item-undone', 'reset'],
  setup(props, { emit }) {
    const doneCount = computed(() => props.order.items.filter((i: any) => i.is_done).length)
    const totalCount = computed(() => props.order.items.length)
    const allDone = computed(() => doneCount.value === totalCount.value)

    const statusClass = computed(() => ({
      pending: props.order.kitchen_status === 'pending',
      preparing: props.order.kitchen_status === 'preparing' || allDone.value,
      completed: props.order.kitchen_status === 'completed'
    }))

    function formatTime(isoStr: string) {
      if (!isoStr) return ''
      const d = new Date(isoStr)
      return `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}:${d.getSeconds().toString().padStart(2,'0')}`
    }

    function onItemClick(item: any) {
      if (item.is_done) {
        emit('item-undone', props.order.id, item.id)
      } else {
        emit('item-done', props.order.id, item.id)
      }
    }

    function onAccept() { emit('accept', props.order.id) }
    function onReset() { emit('reset', props.order.id) }

    return { doneCount, totalCount, allDone, statusClass, formatTime, onItemClick, onAccept, onReset }
  },
  template: `
    <div :class="['order-card', statusClass]">
      <div class="card-header">
        <span class="table-number">{{ order.table_number }}</span>
        <span class="order-time">{{ formatTime(order.created_at) }}</span>
        <span v-if="order.kitchen_status === 'preparing'" class="progress-tag">
          {{ doneCount }}/{{ totalCount }} 完成
        </span>
      </div>
      <div class="card-items">
        <div
          v-for="item in order.items"
          :key="item.id"
          :class="['item-row', { done: item.is_done }]"
          @click="onItemClick(item)"
        >
          <span class="item-check">{{ item.is_done ? '✅' : '○' }}</span>
          <span class="item-name">{{ item.dish_name }}</span>
          <span class="item-qty">×{{ item.quantity }}</span>
          <span v-if="item.note" class="item-note">{{ item.note }}</span>
        </div>
      </div>
      <div v-if="order.remark" class="card-remark">
        <strong>备注：</strong>{{ order.remark }}
      </div>
      <div class="card-actions">
        <button v-if="order.kitchen_status === 'pending'" class="btn-accept" @click="onAccept">
          接 单 ✓
        </button>
        <button v-if="order.kitchen_status === 'preparing'" class="btn-reset" @click="onReset">
          重置
        </button>
      </div>
    </div>
  `
})

</script>

<style scoped>
/* ─── 整体布局 ─── */
.kitchen-view {
  min-height: 100vh;
  background: #f5f6fa;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ─── PIN 输入界面 ─── */
.pin-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.pin-card {
  background: white;
  border-radius: 20px;
  padding: 40px 36px 32px;
  width: 340px;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}

.pin-icon { font-size: 60px; margin-bottom: 8px; }
.pin-card h2 { margin: 0 0 6px; color: #333; font-size: 24px; }
.pin-hint { color: #888; margin: 0 0 20px; font-size: 14px; }

.pin-dots {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-bottom: 16px;
}
.pin-dots span {
  font-size: 28px;
  color: #ddd;
  transition: color 0.15s;
}
.pin-dots span.filled { color: #667eea; }

.pin-error {
  color: #f56c6c;
  font-size: 13px;
  margin: 0 0 10px;
  min-height: 18px;
}

.pin-keypad {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  max-width: 260px;
  margin: 0 auto;
}

.key-btn {
  height: 56px;
  font-size: 24px;
  border: none;
  border-radius: 12px;
  background: #f0f2f5;
  color: #333;
  cursor: pointer;
  transition: background 0.15s;
}
.key-btn:hover { background: #e0e4eb; }
.key-btn:active { background: #d0d4db; }
.key-btn.clear, .key-btn.backspace { background: #fef0f0; color: #f56c6c; font-size: 22px; }

/* ─── 主界面 ─── */
.kitchen-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 16px 32px;
}

/* ─── 顶栏 ─── */
.kitchen-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 0;
  border-bottom: 1px solid #eee;
  background: white;
  margin-bottom: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}
.header-icon { font-size: 28px; }
.header-title { font-size: 20px; font-weight: 600; color: #333; }

.header-stats { display: flex; gap: 10px; }
.header-actions { display: flex; gap: 8px; }

/* ─── Tabs ─── */
.kitchen-tabs {
  background: white;
  border-radius: 12px 12px 0 0;
  padding: 0 16px;
}

/* ─── 订单网格 ─── */
.order-list { padding: 16px 0; }
.order-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

/* ─── 订单卡片 ─── */
.order-card {
  background: white;
  border-radius: 14px;
  padding: 16px;
  border: 2px solid #e4e7ed;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  transition: box-shadow 0.2s;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.order-card.pending { border-color: #f5a623; background: #fffbf0; }
.order-card.preparing { border-color: #409eff; background: #f0f7ff; }
.order-card.completed { border-color: #67c23a; background: #f0f9eb; opacity: 0.8; }

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #666;
  border-bottom: 1px solid #eee;
  padding-bottom: 8px;
}
.table-number {
  font-size: 22px;
  font-weight: 700;
  color: #333;
}
.order-time { margin-left: auto; font-size: 12px; color: #999; }
.progress-tag {
  font-size: 11px;
  background: #e6f0ff;
  color: #409eff;
  padding: 2px 6px;
  border-radius: 8px;
}

.card-items { display: flex; flex-direction: column; gap: 6px; }

.item-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 8px;
  transition: background 0.15s;
  font-size: 15px;
}
.item-row:hover { background: #f5f5f5; }
.item-row.done { text-decoration: line-through; color: #999; }

.item-check { font-size: 16px; flex-shrink: 0; }
.item-name { flex: 1; font-weight: 500; }
.item-qty { color: #f5a623; font-weight: 600; flex-shrink: 0; }
.item-note {
  width: 100%;
  font-size: 12px;
  color: #e6a23c;
  background: #fef9f0;
  border-radius: 4px;
  padding: 2px 6px;
  margin-top: 2px;
}

.card-remark {
  font-size: 13px;
  color: #f56c6c;
  background: #fef0f0;
  border-radius: 8px;
  padding: 6px 10px;
}

.card-actions { display: flex; gap: 8px; }

.btn-accept {
  flex: 1;
  padding: 10px;
  background: #f5a623;
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-accept:hover { background: #e09612; }

.btn-reset {
  padding: 6px 14px;
  background: #909399;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
}

/* ─── 空/加载状态 ─── */
.empty-state, .loading-state {
  text-align: center;
  padding: 80px 20px;
  color: #999;
}
.empty-icon { font-size: 80px; margin-bottom: 16px; }
.empty-state p, .loading-state p { font-size: 16px; margin: 0; }

/* ─── 分页 ─── */
.pagination-bar {
  display: flex;
  justify-content: center;
  padding: 16px 0;
}
</style>
