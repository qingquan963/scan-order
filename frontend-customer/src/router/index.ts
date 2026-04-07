import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import MenuView from '../views/MenuView.vue'
import CartView from '../views/CartView.vue'
import OrderStatusView from '../views/OrderStatusView.vue'
import PayView from '../views/PayView.vue'

// 路由守卫：检查是否有 cart 数据（防止直接访问订单页）
// table_id 查询参数可用于绕过检查（提交订单后跳转）
function checkCart(to: any): string | null {
  if (to.path.startsWith('/customer/order/')) {
    // 有 table_id 参数说明是刚提交订单后跳转过来的，放行
    if (to.query.table_id) {
      return null
    }
    let hasCart = false
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && key.startsWith('cart_')) {
        try {
          const val = localStorage.getItem(key)
          if (val && JSON.parse(val).items?.length > 0) {
            hasCart = true
            break
          }
        } catch {}
      }
    }
    if (!hasCart) {
      ElMessage.warning('请先扫码点餐')
      return '/customer/h5'
    }
  }
  return null
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/customer/h5',
    },
    {
      path: '/customer/h5',
      name: 'menu',
      component: MenuView,
    },
    {
      path: '/customer/cart',
      component: CartView,
    },
    {
      path: '/customer/order/:id',
      name: 'order-status',
      component: OrderStatusView,
    },
    {
      // Phase 2: 支付页面（counter_pay 模式）
      path: '/customer/pay/:id',
      name: 'pay',
      component: PayView,
    },
  ],
})

router.beforeEach((to, _from) => {
  const redirect = checkCart(to)
  if (redirect) return redirect
})

export default router
