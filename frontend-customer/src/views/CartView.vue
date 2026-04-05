<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const API_BASE = 'http://127.0.0.1:8002/api/v1'

const route = useRoute()
const router = useRouter()

const tableId = computed(() => Number(route.query.table_id) || 0)

interface CartItem {
  dish_id: number
  name: string
  price: number
  quantity: number
}

const cartItems = ref<CartItem[]>([])
const remark = ref('')
const submitting = ref(false)
let submitTimer: ReturnType<typeof setTimeout> | null = null

const totalPrice = computed(() =>
  cartItems.value.reduce((sum, i) => sum + i.price * i.quantity, 0)
)

const totalCount = computed(() =>
  cartItems.value.reduce((sum, i) => sum + i.quantity, 0)
)

function loadCart() {
  const key = `cart_${tableId.value}`
  const saved = localStorage.getItem(key)
  if (saved) {
    try {
      const data = JSON.parse(saved)
      cartItems.value = data.items || []
    } catch {
      cartItems.value = []
    }
  }
}

function saveCart() {
  const key = `cart_${tableId.value}`
  localStorage.setItem(key, JSON.stringify({
    table_id: tableId.value,
    items: cartItems.value,
    total: totalPrice.value
  }))
}

function increaseQty(item: CartItem) {
  item.quantity++
  saveCart()
}

function decreaseQty(item: CartItem) {
  item.quantity--
  if (item.quantity <= 0) {
    cartItems.value = cartItems.value.filter(i => i.dish_id !== item.dish_id)
  }
  saveCart()
}

async function submitOrder() {
  // 防抖：1秒内禁止重复点击
  if (submitting.value) return
  if (cartItems.value.length === 0) return

  submitting.value = true
  submitTimer = setTimeout(() => {
    submitting.value = false
  }, 1000)

  try {
    const res = await fetch(`${API_BASE}/customer/orders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        table_id: tableId.value,
        items: cartItems.value.map(i => ({ dish_id: i.dish_id, quantity: i.quantity })),
        remark: remark.value
      })
    })

    if (!res.ok) {
      const err = await res.json()
      alert(err.detail || '下单失败')
      submitting.value = false
      if (submitTimer) clearTimeout(submitTimer)
      return
    }

    const data = await res.json()
    // 清空购物车
    localStorage.removeItem(`cart_${tableId.value}`)

    // Phase 2: 根据支付模式决定跳转
    // counter_pay 模式 -> 跳转支付页
    // credit_pay 模式 -> 跳转订单状态页
    if (data.payment_mode === 'counter_pay' && data.status === 'pending_payment') {
      router.push(`/customer/pay/${data.id}?table_id=${tableId.value}`)
    } else {
      router.push(`/customer/order/${data.id}?table_id=${tableId.value}`)
    }
  } catch (e) {
    alert('网络异常，请重试')
    submitting.value = false
    if (submitTimer) clearTimeout(submitTimer)
  }
}

onMounted(() => {
  loadCart()
})
</script>

<template>
  <div class="cart-page">
    <!-- 顶部 -->
    <div class="header">
      <span class="back-btn" @click="router.back()">←</span>
      <span class="header-title">购物车</span>
      <span class="clear-btn" v-if="cartItems.length > 0" @click="cartItems = []; saveCart()">清空</span>
      <span v-else class="clear-btn placeholder"></span>
    </div>

    <!-- 空购物车 -->
    <div v-if="cartItems.length === 0" class="empty-cart">
      <div class="empty-icon">🛒</div>
      <div class="empty-text">购物车是空的</div>
      <div class="empty-sub">快去选择喜欢的菜品吧</div>
      <button class="go-menu-btn" @click="router.push(`/customer/h5?table_id=${tableId}`)">去点餐</button>
    </div>

    <!-- 购物车内容 -->
    <div v-else class="cart-content">
      <!-- 头部桌台信息 -->
      <div class="table-badge">桌台：{{ tableId }}号桌</div>

      <!-- 菜品列表 -->
      <div class="item-list">
        <div v-for="item in cartItems" :key="item.dish_id" class="cart-item">
          <div class="item-info">
            <div class="item-name">{{ item.name }}</div>
            <div class="item-price">¥{{ item.price.toFixed(2) }}</div>
          </div>
          <div class="item-actions">
            <button class="qty-btn minus" @click="decreaseQty(item)">−</button>
            <span class="qty-num">{{ item.quantity }}</span>
            <button class="qty-btn plus" @click="increaseQty(item)">+</button>
          </div>
        </div>
      </div>

      <!-- 备注 -->
      <div class="remark-section">
        <div class="remark-label">备注</div>
        <textarea
          v-model="remark"
          class="remark-input"
          placeholder="口味、偏好等要求（选填）"
          rows="2"
        ></textarea>
      </div>
    </div>

    <!-- 底部结算栏 -->
    <div class="bottom-bar" v-if="cartItems.length > 0">
      <div class="total-info">
        <span class="total-count">共 {{ totalCount }} 件</span>
        <span class="total-price">¥{{ totalPrice.toFixed(2) }}</span>
      </div>
      <button
        class="submit-btn"
        :class="{ disabled: submitting }"
        @click="submitOrder"
      >
        {{ submitting ? '提交中...' : '提交订单' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.cart-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: 70px;
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

.clear-btn {
  font-size: 13px;
  color: #ff4d4f;
  cursor: pointer;
  width: 32px;
  text-align: right;
}

.clear-btn.placeholder {
  cursor: default;
}

.empty-cart {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-top: 80px;
  gap: 8px;
}

.empty-icon {
  font-size: 56px;
  opacity: 0.5;
}

.empty-text {
  font-size: 16px;
  color: #666;
  font-weight: 500;
}

.empty-sub {
  font-size: 13px;
  color: #999;
  margin-bottom: 16px;
}

.go-menu-btn {
  background: #ff4d4f;
  color: #fff;
  border: none;
  border-radius: 20px;
  padding: 10px 28px;
  font-size: 14px;
  cursor: pointer;
}

.cart-content {
  max-width: 480px;
  margin: 0 auto;
  padding: 10px 12px;
}

.table-badge {
  display: inline-block;
  background: #fff0f0;
  color: #ff4d4f;
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 12px;
  margin-bottom: 10px;
}

.item-list {
  background: #fff;
  border-radius: 10px;
  overflow: hidden;
}

.cart-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 14px;
  border-bottom: 1px solid #f0f0f0;
}

.cart-item:last-child {
  border-bottom: none;
}

.item-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: 15px;
  font-weight: 500;
  color: #222;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-price {
  font-size: 13px;
  color: #ff4d4f;
}

.item-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.qty-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}

.qty-btn.plus {
  background: #ff4d4f;
  color: #fff;
}

.qty-btn.plus:hover {
  background: #e63636;
}

.qty-btn.minus {
  background: #f5f5f5;
  color: #666;
  border: 1px solid #ddd;
}

.qty-btn.minus:hover {
  background: #eee;
}

.qty-num {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  min-width: 24px;
  text-align: center;
}

.remark-section {
  margin-top: 12px;
  background: #fff;
  border-radius: 10px;
  padding: 12px 14px;
}

.remark-label {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.remark-input {
  width: 100%;
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 14px;
  resize: none;
  outline: none;
  box-sizing: border-box;
  font-family: inherit;
  color: #333;
}

.remark-input:focus {
  border-color: #ff4d4f;
}

.remark-input::placeholder {
  color: #bbb;
}

.bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: #fff;
  box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  z-index: 100;
}

.total-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.total-count {
  font-size: 12px;
  color: #888;
}

.total-price {
  font-size: 20px;
  font-weight: 700;
  color: #ff4d4f;
}

.submit-btn {
  background: #ff4d4f;
  color: #fff;
  border: none;
  border-radius: 22px;
  padding: 10px 28px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.submit-btn:hover:not(.disabled) {
  background: #e63636;
}

.submit-btn.disabled {
  background: #ccc;
  cursor: not-allowed;
}
</style>
