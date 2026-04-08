<template>
  <div class="kds">
    <div class="header">
      <h1>🍳 后厨看板 - {{ tenant }}</h1>
      <button @click="fetchOrders">🔄 刷新</button>
    </div>
    <div class="orders">
      <div v-for="order in orders" :key="order.id" class="order-card" :class="order.kitchen_status || order.status">
        <div class="table-no">桌台 {{ order.table_id }}</div>
        <div class="items">
          <div v-for="item in order.items" :key="item.id" class="item">
            <span>{{ item.dish_name }}</span>
            <span>× {{ item.quantity }}</span>
          </div>
        </div>
        <button v-if="order.kitchen_status !== 'preparing'" @click="startOrder(order.id)">开始制作</button>
        <button @click="markDone(order.id)">完成</button>
      </div>
    </div>
    <div v-if="orders.length === 0" class="empty">暂无待制作订单</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import axios from 'axios';

const orders = ref<any[]>([]);
const tenant = ref(localStorage.getItem('tenant_name') || '未知商户');
const API_BASE = localStorage.getItem('API_BASE') || 'http://localhost:8000';

async function fetchOrders() {
  const token = localStorage.getItem('token');
  const res = await axios.get(`${API_BASE}/api/v1/kitchen/orders`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  orders.value = res.data.orders || [];
}

async function startOrder(orderId: number) {
  const token = localStorage.getItem('token');
  await axios.post(`${API_BASE}/api/v1/kitchen/orders/${orderId}/start`, {}, {
    headers: { Authorization: `Bearer ${token}` }
  });
  fetchOrders();
}

async function markDone(orderId: number) {
  const token = localStorage.getItem('token');
  await axios.post(`${API_BASE}/api/v1/kitchen/orders/${orderId}/done`, {}, {
    headers: { Authorization: `Bearer ${token}` }
  });
  fetchOrders();
}

onMounted(() => {
  fetchOrders();
  setInterval(fetchOrders, 10000);
});
</script>

<style scoped>
.kds { padding: 20px; }
.header { display: flex; justify-content: space-between; margin-bottom: 20px; }
.orders { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.order-card { background: #16213e; padding: 16px; border-radius: 8px; border-left: 4px solid #e94560; }
.order-card.preparing { border-left-color: #f39c12; }
.table-no { font-weight: bold; font-size: 18px; color: #e94560; margin-bottom: 8px; }
.items { margin-bottom: 12px; }
.item { display: flex; justify-content: space-between; padding: 4px 0; }
button { margin-right: 8px; padding: 6px 12px; cursor: pointer; }
.empty { text-align: center; color: #666; margin-top: 40px; }
</style>
