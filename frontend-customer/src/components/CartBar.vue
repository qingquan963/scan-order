<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  totalCount: number
  totalPrice: number
  onJump: () => void
}

const props = defineProps<Props>()

const hasItems = computed(() => props.totalCount > 0)
</script>

<template>
  <div class="cart-bar" :class="{ active: hasItems }">
    <div class="cart-info" @click="onJump">
      <span class="cart-icon">🛒</span>
      <span class="cart-badge" v-if="hasItems">{{ totalCount }}</span>
      <div class="cart-text">
        <span class="cart-label">已选 {{ totalCount }} 件</span>
        <span class="cart-price">¥{{ totalPrice.toFixed(2) }}</span>
      </div>
    </div>
    <button class="cart-btn" :disabled="!hasItems" @click="onJump">
      去结算
    </button>
  </div>
</template>

<style scoped>
.cart-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 56px;
  background: #d9d9d9;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  z-index: 100;
  transition: background 0.2s;
}
.cart-bar.active {
  background: #fff;
  box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
}
.cart-info {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.cart-icon {
  font-size: 26px;
}
.cart-badge {
  position: absolute;
  top: -6px;
  left: 18px;
  background: #ff4d4f;
  color: #fff;
  border-radius: 50%;
  width: 18px;
  height: 18px;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}
.cart-text {
  display: flex;
  flex-direction: column;
}
.cart-label {
  font-size: 12px;
  color: #888;
}
.cart-price {
  font-size: 17px;
  font-weight: 700;
  color: #ff4d4f;
}
.cart-btn {
  background: #ff4d4f;
  color: #fff;
  border: none;
  border-radius: 20px;
  padding: 8px 22px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.cart-btn:hover:not(:disabled) {
  background: #e63636;
}
.cart-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}
</style>
