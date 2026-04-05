<script setup lang="ts">
import { computed } from 'vue'

interface Dish {
  id: number
  name: string
  price: number
  description: string
  image: string
  is_available: number
}

interface Props {
  dish: Dish
  quantity: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  add: [dish: Dish]
  remove: [dishId: number]
}>()

const isSoldOut = computed(() => props.dish.is_available === 0)

function handleAdd() {
  if (!isSoldOut.value) {
    emit('add', props.dish)
  }
}

function handleRemove() {
  if (!isSoldOut.value && props.quantity > 0) {
    emit('remove', props.dish.id)
  }
}

function truncate(text: string, maxLen: number): string {
  if (!text || text.length <= maxLen) return text || ''
  return text.slice(0, maxLen) + '...'
}
</script>

<template>
  <div class="dish-card" :class="{ 'sold-out': isSoldOut }">
    <div class="dish-image">
      <img :src="dish.image || '/placeholder.png'" :alt="dish.name" />
      <span v-if="isSoldOut" class="sold-out-tag">已售罄</span>
    </div>
    <div class="dish-info">
      <div class="dish-name">{{ dish.name }}</div>
      <div class="dish-desc">{{ truncate(dish.description, 40) }}</div>
      <div class="dish-bottom">
        <span class="dish-price">¥{{ dish.price.toFixed(2) }}</span>
        <div class="dish-actions">
          <button
            class="btn-minus"
            :disabled="isSoldOut || quantity === 0"
            @click="handleRemove"
          >−</button>
          <span class="dish-qty">{{ quantity }}</span>
          <button
            class="btn-plus"
            :disabled="isSoldOut"
            @click="handleAdd"
          >+</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dish-card {
  display: flex;
  gap: 10px;
  background: #fff;
  border-radius: 10px;
  padding: 10px;
  margin-bottom: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
.dish-card.sold-out {
  opacity: 0.65;
}
.dish-image {
  position: relative;
  flex-shrink: 0;
  width: 80px;
  height: 80px;
  border-radius: 8px;
  overflow: hidden;
}
.dish-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.sold-out-tag {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0,0,0,0.45);
  color: #fff;
  font-size: 12px;
  font-weight: bold;
}
.dish-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-width: 0;
}
.dish-name {
  font-size: 15px;
  font-weight: 600;
  color: #222;
}
.dish-desc {
  font-size: 12px;
  color: #888;
  margin: 3px 0;
  line-height: 1.4;
}
.dish-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.dish-price {
  font-size: 16px;
  color: #ff4d4f;
  font-weight: 700;
}
.dish-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.btn-minus, .btn-plus {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: none;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}
.btn-plus {
  background: #ff4d4f;
  color: #fff;
}
.btn-plus:hover:not(:disabled) {
  background: #e63636;
}
.btn-minus {
  background: #f5f5f5;
  color: #666;
  border: 1px solid #ddd;
}
.btn-minus:hover:not(:disabled) {
  background: #eee;
}
.btn-minus:disabled, .btn-plus:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.dish-qty {
  min-width: 20px;
  text-align: center;
  font-size: 15px;
  font-weight: 600;
  color: #333;
}
</style>
