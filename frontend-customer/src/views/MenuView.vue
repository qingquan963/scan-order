<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DishCard from '../components/DishCard.vue'
import CartBar from '../components/CartBar.vue'

const API_BASE = 'http://localhost:8003/api/v1'

const route = useRoute()
const router = useRouter()

const tableId = computed(() => Number(route.query.table_id) || 0)

// 桌台信息
const tableInfo = ref<{ id: number; name: string } | null>(null)

// 分类列表
const categories = ref<{ id: number; name: string }[]>([])

// 菜品列表
const dishes = ref<any[]>([])

// 购物车状态
interface CartItem {
  dish_id: number
  name: string
  price: number
  quantity: number
}

interface Cart {
  table_id: number
  items: CartItem[]
  total: number
}

const cart = ref<Cart>({ table_id: 0, items: [], total: 0 })

// 加载购物车
function loadCart(): Cart {
  const key = `cart_${tableId.value}`
  const saved = localStorage.getItem(key)
  if (saved) {
    try {
      return JSON.parse(saved)
    } catch {
      return { table_id: tableId.value, items: [], total: 0 }
    }
  }
  return { table_id: tableId.value, items: [], total: 0 }
}

// 保存购物车
function saveCart() {
  const key = `cart_${tableId.value}`
  localStorage.setItem(key, JSON.stringify(cart.value))
}

// 购物车中某菜品的数量
function getQty(dishId: number): number {
  return cart.value.items.find(i => i.dish_id === dishId)?.quantity || 0
}

// 加菜
function addDish(dish: any) {
  if (dish.is_available === 0) return
  const existing = cart.value.items.find(i => i.dish_id === dish.id)
  if (existing) {
    existing.quantity++
  } else {
    cart.value.items.push({ dish_id: dish.id, name: dish.name, price: dish.price, quantity: 1 })
  }
  recalcTotal()
  saveCart()
}

// 减菜
function removeDish(dishId: number) {
  const item = cart.value.items.find(i => i.dish_id === dishId)
  if (!item) return
  item.quantity--
  if (item.quantity <= 0) {
    cart.value.items = cart.value.items.filter(i => i.dish_id !== dishId)
  }
  recalcTotal()
  saveCart()
}

function recalcTotal() {
  cart.value.total = cart.value.items.reduce((sum, i) => sum + i.price * i.quantity, 0)
}

// 去购物车页
function goCart() {
  router.push(`/customer/cart?table_id=${tableId.value}`)
}

// 按分类过滤菜品
const dishesByCategory = computed(() => {
  const map = new Map<number, any[]>()
  for (const cat of categories.value) {
    map.set(cat.id, dishes.value.filter(d => d.category_id === cat.id))
  }
  return map
})

// 当前选中分类
const activeCategoryId = ref<number>(0)

// 分类滚动到对应位置
const categoryRefs = ref<Record<number, HTMLElement>>({})
const dishListRef = ref<HTMLElement>()

function scrollToCategory(catId: number) {
  activeCategoryId.value = catId
  const el = categoryRefs.value[catId]
  if (el && dishListRef.value) {
    const container = dishListRef.value
    const offsetTop = el.offsetTop - container.offsetTop
    container.scrollTo({ top: offsetTop, behavior: 'smooth' })
  }
}

// 监听滚动更新 active 分类
function onDishScroll() {
  if (!dishListRef.value) return
  const container = dishListRef.value
  const scrollTop = container.scrollTop + 60 // 偏移量

  for (const cat of categories.value) {
    const el = categoryRefs.value[cat.id]
    if (el && el.offsetTop <= scrollTop) {
      activeCategoryId.value = cat.id
    }
  }
}

// 获取菜品列表（仅 is_available=1）
async function fetchDishes() {
  try {
    const res = await fetch(`${API_BASE}/customer/dishes`)
    if (res.ok) {
      const data = await res.json()
      dishes.value = (Array.isArray(data) ? data : data.data || []).filter((d: any) => d.is_available === 1)
    }
  } catch (e) {
    console.error('fetch dishes error', e)
  }
}

async function fetchCategories() {
  try {
    const res = await fetch(`${API_BASE}/customer/categories`)
    if (res.ok) {
      const data = await res.json()
      categories.value = Array.isArray(data) ? data : data.data || []
      if (categories.value.length > 0) {
        activeCategoryId.value = categories.value[0].id
      }
    }
  } catch (e) {
    console.error('fetch categories error', e)
  }
}

async function fetchTable() {
  try {
    const res = await fetch(`${API_BASE}/customer/tables/${tableId.value}`)
    if (res.ok) {
      const data = await res.json()
      tableInfo.value = data
    }
  } catch (e) {
    console.error('fetch table error', e)
  }
}

onMounted(async () => {
  cart.value = loadCart()
  await Promise.all([fetchTable(), fetchCategories(), fetchDishes()])
})
</script>

<template>
  <div class="menu-page">
    <!-- 顶部标题 -->
    <div class="header">
      <div class="header-title">{{ tableInfo?.name || '扫码点餐' }}</div>
    </div>

    <div class="body">
      <!-- 左侧分类导航 -->
      <div class="sidebar">
        <div
          v-for="cat in categories"
          :key="cat.id"
          class="sidebar-item"
          :class="{ active: activeCategoryId === cat.id }"
          @click="scrollToCategory(cat.id)"
        >
          {{ cat.name }}
        </div>
      </div>

      <!-- 右侧菜品列表 -->
      <div class="dish-list" ref="dishListRef" @scroll="onDishScroll">
        <div
          v-for="cat in categories"
          :key="cat.id"
          :ref="(el) => { if (el) categoryRefs[cat.id] = el as HTMLElement }"
          class="category-section"
        >
          <div class="category-title">{{ cat.name }}</div>
          <DishCard
            v-for="dish in dishesByCategory.get(cat.id)"
            :key="dish.id"
            :dish="dish"
            :quantity="getQty(dish.id)"
            @add="addDish"
            @remove="removeDish"
          />
          <div
            v-if="!dishesByCategory.get(cat.id)?.length"
            class="empty-tip"
          >
            该分类暂无菜品
          </div>
        </div>
      </div>
    </div>

    <!-- 底部购物车栏 -->
    <CartBar
      :total-count="cart.items.reduce((s, i) => s + i.quantity, 0)"
      :total-price="cart.total"
      :on-jump="goCart"
    />
  </div>
</template>

<style scoped>
.menu-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}
.header {
  height: 48px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}
.header-title {
  font-size: 17px;
  font-weight: 600;
  color: #222;
}
.body {
  flex: 1;
  display: flex;
  overflow: hidden;
}
.sidebar {
  width: 78px;
  flex-shrink: 0;
  background: #f5f5f5;
  overflow-y: auto;
  border-right: 1px solid #eee;
}
.sidebar-item {
  padding: 14px 8px;
  font-size: 13px;
  color: #666;
  text-align: center;
  border-left: 3px solid transparent;
  cursor: pointer;
  transition: all 0.15s;
  line-height: 1.3;
}
.sidebar-item.active {
  background: #fff;
  color: #ff4d4f;
  font-weight: 600;
  border-left-color: #ff4d4f;
}
.dish-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px 10px 70px 10px;
}
.category-section {
  margin-bottom: 10px;
}
.category-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
  padding-left: 2px;
}
.empty-tip {
  text-align: center;
  color: #bbb;
  font-size: 13px;
  padding: 16px 0;
}
</style>
