<template>
  <div class="pay-page">
    <!-- 顶部 -->
    <div class="header">
      <span class="back-btn" @click="router.back()">←</span>
      <span class="header-title">订单支付</span>
      <span class="placeholder"></span>
    </div>

    <!-- 错误状态 -->
    <div v-if="error" class="error-box">
      <div class="error-icon">!</div>
      <div class="error-text">{{ error }}</div>
      <button class="action-btn secondary" @click="router.push(`/customer/h5?table_id=${tableId}`)">
        返回菜单
      </button>
    </div>

    <!-- 支付内容 -->
    <div v-else-if="order" class="pay-content">
      <!-- 订单摘要 -->
      <div class="order-summary">
        <div class="summary-title">订单已提交</div>
        <div class="summary-order-no">订单号: {{ order.order_number }}</div>
        <div class="summary-amount">
          <span class="amount-label">应付金额</span>
          <span class="amount-value">¥{{ order.total_amount?.toFixed(2) }}</span>
        </div>
      </div>

      <!-- 状态提示 -->
      <div class="status-notice" v-if="order.status === 'pending_payment'">
        <div class="notice-icon">📋</div>
        <div class="notice-title">请凭此码到柜台付款</div>
        <div class="notice-sub">付款完成后工作人员会确认您的订单</div>
      </div>

      <!-- 支付码展示（counter_pay 模式） -->
      <div v-if="order.status === 'pending_payment'" class="payment-code-section">
        <div class="payment-code-label">扫码支付</div>
        <div class="payment-code-box">
          <img v-if="qrCodeUrl" :src="qrCodeUrl" alt="支付二维码" class="qr-code-image" />
          <div v-else class="payment-code">{{ paymentCode }}</div>
        </div>
        <div class="countdown-box">
          <div class="countdown-label">剩余时间</div>
          <div class="countdown-value" :class="{ urgent: countdown < 120 }">
            {{ formatCountdown(countdown) }}
          </div>
        </div>
      </div>

      <!-- 已支付提示 -->
      <div v-if="order.status === 'pending' || order.status === 'confirmed'" class="paid-notice">
        <div class="paid-icon">✓</div>
        <div class="paid-title">已付款，请等待接单</div>
        <div class="paid-sub">商户接单后会开始准备您的菜品</div>
      </div>

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <button
          v-if="order.status === 'pending_payment'"
          class="action-btn primary"
          :class="{ loading: confirming }"
          @click="confirmPayment"
          :disabled="confirming"
        >
          {{ confirming ? '确认中...' : '我已付款（模拟）' }}
        </button>
        <button
          class="action-btn secondary"
          @click="router.push(`/customer/h5?table_id=${tableId}`)"
        >
          返回菜单
        </button>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-else class="loading-box">
      <div class="loading-spinner"></div>
      <span>加载中...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const API_BASE = 'http://localhost:8002/api/v1'

const route = useRoute()
const router = useRouter()

const orderId = computed(() => route.params.id as string)
const tableId = computed(() => Number(route.query.table_id) || 0)

interface Order {
  id: number
  order_number: string
  status: string
  total_amount: number
  payment_code?: string
  payment_token?: string
}

const order = ref<Order | null>(null)
const error = ref('')
const confirming = ref(false)
const countdown = ref(0)
const qrCodeUrl = ref('')
let countdownTimer: ReturnType<typeof setInterval> | null = null
const ORDER_EXPIRE_MINUTES = 10

async function generateQRCode(orderData: Order) {
  qrCodeUrl.value = ''
  const content = `${orderData.id}:${orderData.total_amount}:${Date.now()}`
  try {
    const QRCode = (await import('qrcode')).default
    qrCodeUrl.value = await QRCode.toDataURL(content, {
      width: 200,
      margin: 2,
      color: { dark: '#000000', light: '#ffffff' }
    })
  } catch (e) {
    console.error('QR code generation failed:', e)
  }
}
const paymentCode = computed(() => {
  if (order.value?.payment_code) return order.value.payment_code
  if (order.value?.payment_token) {
    return `ORDER-${order.value.id}-${order.value.payment_token.substring(0, 8).toUpperCase()}`
  }
  return ''
})

function formatCountdown(seconds: number) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function startCountdown() {
  stopCountdown()
  countdownTimer = setInterval(() => {
    if (countdown.value > 0) {
      countdown.value--
    } else {
      stopCountdown()
      // 超时自动刷新订单状态
      fetchOrder()
    }
  }, 1000)
}

function stopCountdown() {
  if (countdownTimer !== null) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
}

async function fetchOrder() {
  try {
    const res = await fetch(`${API_BASE}/customer/orders/${orderId.value}`)
    if (!res.ok) {
      const err = await res.json()
      error.value = err.detail || '获取订单失败'
      return
    }
    const data = await res.json()
    order.value = data

    // 生成支付二维码
    if (data.status === 'pending_payment') {
      generateQRCode(data)
    }

    // 根据状态处理倒计时
    if (data.status === 'pending_payment') {
      // 计算剩余时间（10分钟超时）
      const createdAt = new Date(data.created_at)
      const elapsed = Math.floor((Date.now() - createdAt.getTime()) / 1000)
      countdown.value = Math.max(0, ORDER_EXPIRE_MINUTES * 60 - elapsed)
      startCountdown()
    } else {
      stopCountdown()
      countdown.value = 0
    }

    error.value = ''
  } catch (e: any) {
    error.value = '网络异常，请刷新重试'
  }
}

async function confirmPayment() {
  if (confirming.value || !order.value?.payment_token) return
  confirming.value = true
  try {
    const res = await fetch(`${API_BASE}/customer/orders/${orderId.value}/pay`, {
      method: 'POST'
    })
    const data = await res.json()
    if (!res.ok) {
      alert(data.detail || '确认失败')
      return
    }
    // 重新获取订单状态
    await fetchOrder()
  } catch (e) {
    alert('网络异常，请重试')
  } finally {
    confirming.value = false
  }
}

onMounted(async () => {
  await fetchOrder()
})

onUnmounted(() => {
  stopCountdown()
})
</script>

<style scoped>
.pay-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: 30px;
}

.header {
  position: sticky;
  top: 0;
  background: #fff;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  border-bottom: 1px solid #eee;
  z-index: 10;
}

.back-btn {
  font-size: 20px;
  color: #333;
  cursor: pointer;
  width: 32px;
}

.header-title {
  font-size: 17px;
  font-weight: 600;
  color: #222;
}

.placeholder {
  width: 32px;
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

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #eee;
  border-top-color: #409eff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 12px;
  color: #666;
  padding: 20px;
  text-align: center;
}

.error-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: #fff0f0;
  color: #f56c6c;
  font-size: 32px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
}

.error-text {
  font-size: 14px;
  color: #999;
}

.pay-content {
  max-width: 480px;
  margin: 0 auto;
  padding: 0 12px;
}

.order-summary {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  margin-top: 12px;
  text-align: center;
}

.summary-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.summary-order-no {
  font-size: 12px;
  color: #999;
  margin-bottom: 12px;
}

.summary-amount {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.amount-label {
  font-size: 12px;
  color: #888;
}

.amount-value {
  font-size: 32px;
  font-weight: 700;
  color: #ff4d4f;
}

.status-notice {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  margin-top: 12px;
  text-align: center;
}

.notice-icon {
  font-size: 48px;
  margin-bottom: 8px;
}

.notice-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.notice-sub {
  font-size: 13px;
  color: #999;
}

.payment-code-section {
  background: #fff;
  border-radius: 12px;
  padding: 24px 20px;
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.payment-code-label {
  font-size: 14px;
  color: #888;
}

.payment-code-box {
  width: 100%;
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.qr-code-image {
  width: 200px;
  height: 200px;
  display: block;
  margin: 0 auto;
}

.payment-code {
  font-size: 22px;
  font-weight: 700;
  font-family: 'Courier New', monospace;
  color: #333;
  letter-spacing: 2px;
  word-break: break-all;
}

.countdown-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.countdown-label {
  font-size: 12px;
  color: #999;
}

.countdown-value {
  font-size: 28px;
  font-weight: 700;
  color: #333;
  font-family: 'Courier New', monospace;
}

.countdown-value.urgent {
  color: #f56c6c;
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.paid-notice {
  background: #fff;
  border-radius: 12px;
  padding: 32px 20px;
  margin-top: 12px;
  text-align: center;
}

.paid-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: #f0f9eb;
  color: #67c23a;
  font-size: 28px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12px;
}

.paid-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.paid-sub {
  font-size: 13px;
  color: #999;
}

.action-buttons {
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action-btn {
  width: 100%;
  border: none;
  border-radius: 24px;
  padding: 14px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.action-btn.primary {
  background: #ff4d4f;
  color: #fff;
}

.action-btn.primary:hover:not(:disabled) {
  background: #e63636;
}

.action-btn.primary.loading {
  background: #ccc;
  cursor: not-allowed;
}

.action-btn.secondary {
  background: #fff;
  color: #ff4d4f;
  border: 1.5px solid #ff4d4f;
}

.action-btn.secondary:hover {
  background: #fff0f0;
}
</style>
