<template>
  <div class="order-status-page">
    <!-- 错误提示 -->
    <div v-if="error" class="error-box">
      <el-icon class="error-icon"><WarningFilled /></el-icon>
      <span>{{ error }}</span>
      <el-button size="small" @click="goHome">返回首页</el-button>
    </div>

    <!-- 订单内容 -->
    <div v-else-if="order" class="order-content">
      <!-- 头部信息 -->
      <div class="order-header">
        <div class="order-title">订单状态</div>
        <div class="order-number">订单号: {{ order.order_number }}</div>
        <div class="table-info">桌号: {{ order.table_id }}号桌</div>
        <div class="order-time">下单时间: {{ formatTime(order.created_at) }}</div>
      </div>

      <!-- 状态标签 -->
      <div class="status-section">
        <el-tag :type="statusTagType" size="large" effect="dark" round>
          {{ statusText }}
        </el-tag>
        <div v-if="!isFinal" class="polling-hint">正在实时更新...</div>
      </div>

      <!-- 订单菜品列表 -->
      <div class="dishes-section">
        <div class="section-title">菜品明细</div>
        <div class="dish-list">
          <div v-for="item in order.items" :key="item.id" class="dish-item">
            <div class="dish-info">
              <span class="dish-name">{{ item.dish_name }}</span>
              <span v-if="item.note" class="dish-note">{{ item.note }}</span>
            </div>
            <div class="dish-meta">
              <span class="dish-qty">x{{ item.quantity }}</span>
              <span class="dish-price">¥{{ item.subtotal.toFixed(2) }}</span>
            </div>
          </div>
        </div>
        <div class="order-total">
          <span>合计</span>
          <span class="total-amount">¥{{ order.total_amount.toFixed(2) }}</span>
        </div>
      </div>

      <!-- 备注 -->
      <div v-if="order.remark" class="remark-section">
        <div class="section-title">备注</div>
        <div class="remark-text">{{ order.remark }}</div>
      </div>

      <!-- Phase 2: 待付款状态显示去支付按钮 -->
      <div v-if="order.status === 'pending_payment'" class="pending-payment-tip">
        <div class="tip-text">请凭支付码到柜台付款</div>
      </div>

      <!-- 返回菜单按钮 -->
      <div class="bottom-action">
        <button
          v-if="order.status === 'pending_payment'"
          class="pay-btn"
          @click="goToPay"
        >
          查看支付码
        </button>
        <button class="back-menu-btn" @click="goMenu">
          返回菜单
        </button>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-else class="loading-box">
      <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { WarningFilled, Loading } from '@element-plus/icons-vue'

const API_BASE = 'http://localhost:8002/api/v1'

const route = useRoute()
const router = useRouter()

const orderId = computed(() => route.params.id as string)
const order = ref<any>(null)
const error = ref('')
let pollingTimer: ReturnType<typeof setInterval> | null = null

// 状态 → Tag type
const statusTagType = computed(() => {
  const map: Record<string, string> = {
    pending: 'warning',       // 待接单
    pending_payment: 'warning', // Phase 2: 待付款
    confirmed: 'primary',     // 已接单
    paid: 'success',          // 已结账
    cancelled: 'info',        // 已取消
  }
  return map[order.value?.status] || 'info'
})

// 状态 → 文字
const statusText = computed(() => {
  const map: Record<string, string> = {
    pending: '待接单',
    pending_payment: '待付款',  // Phase 2
    confirmed: '已接单',
    paid: '已结账',
    cancelled: '已取消',
  }
  return map[order.value?.status] || order.value?.status || ''
})

// 订单是否已完结（停止轮询）
const isFinal = computed(() => {
  return order.value?.status === 'paid' || order.value?.status === 'cancelled'
})

// 格式化时间
function formatTime(dt: string | Date) {
  if (!dt) return ''
  const d = new Date(dt)
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

// 获取订单数据
async function fetchOrder() {
  try {
    const res = await axios.get(`${API_BASE}/customer/orders/${orderId.value}`)
    order.value = res.data
    error.value = ''

    // 订单已完成，停止轮询
    if (isFinal.value) {
      stopPolling()
    }
  } catch (e: any) {
    stopPolling()
    if (e.response?.status === 404) {
      error.value = '订单不存在'
    } else {
      error.value = '网络异常'
    }
  }
}

// 轮询
function startPolling() {
  stopPolling()
  pollingTimer = setInterval(fetchOrder, 5000)
}

function stopPolling() {
  if (pollingTimer !== null) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

// 返回首页
function goHome() {
  router.push('/customer/h5')
}

// 返回菜单
function goMenu() {
  router.push(`/customer/h5?table_id=${route.query.table_id}`)
}

// Phase 2: 跳转支付页面
function goToPay() {
  router.push(`/customer/pay/${orderId.value}?table_id=${route.query.table_id}`)
}

// 路由守卫在 router/index.ts 中处理 cart 检查
// 此处组件仅负责订单数据获取和轮询
onMounted(async () => {
  await fetchOrder()
  if (!isFinal.value) {
    startPolling()
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.order-status-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: 20px;
}

.error-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 12px;
  color: #666;
}

.error-icon {
  font-size: 48px;
  color: #f56c6c;
}

.loading-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 12px;
  color: #999;
}

.loading-icon {
  animation: spin 1s linear infinite;
  color: #409eff;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.order-content {
  max-width: 480px;
  margin: 0 auto;
  padding: 0 12px;
}

.order-header {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.order-title {
  font-size: 18px;
  font-weight: 600;
  color: #222;
  margin-bottom: 6px;
}

.order-number,
.table-info,
.order-time {
  font-size: 13px;
  color: #888;
}

.status-section {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.polling-hint {
  font-size: 12px;
  color: #bbb;
}

.dishes-section {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  margin-top: 10px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
}

.dish-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.dish-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.dish-item:last-child {
  border-bottom: none;
}

.dish-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.dish-name {
  font-size: 14px;
  color: #333;
}

.dish-note {
  font-size: 12px;
  color: #999;
}

.dish-meta {
  display: flex;
  gap: 8px;
  align-items: center;
}

.dish-qty {
  font-size: 13px;
  color: #999;
}

.dish-price {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.order-total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #eee;
  font-size: 15px;
  font-weight: 600;
  color: #333;
}

.total-amount {
  color: #ff4d4f;
  font-size: 18px;
}

.remark-section {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  margin-top: 10px;
}

.remark-text {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
}

.bottom-action {
  margin-top: 20px;
  padding: 0 12px;
  max-width: 480px;
  margin-left: auto;
  margin-right: auto;
}

.back-menu-btn {
  width: 100%;
  background: #fff;
  color: #ff4d4f;
  border: 1.5px solid #ff4d4f;
  border-radius: 24px;
  padding: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.back-menu-btn:hover {
  background: #fff0f0;
}

/* Phase 2: pending_payment styles */
.pending-payment-tip {
  background: #fff;
  border-radius: 8px;
  padding: 12px 16px;
  margin: 10px 0;
  text-align: center;
}

.tip-text {
  font-size: 14px;
  color: #ff4d4f;
  font-weight: 500;
}

.bottom-action {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 20px;
  padding: 0 12px;
  max-width: 480px;
  margin-left: auto;
  margin-right: auto;
}

.pay-btn {
  width: 100%;
  background: #ff4d4f;
  color: #fff;
  border: none;
  border-radius: 24px;
  padding: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.pay-btn:hover {
  background: #e63636;
}
</style>
