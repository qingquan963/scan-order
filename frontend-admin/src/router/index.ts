import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import CategoryManager from '../views/CategoryManager.vue'
import DishManager from '../views/DishManager.vue'
import TableManager from '../views/TableManager.vue'
import OrderManager from '../views/OrderManager.vue'
import SettingsView from '../views/SettingsView.vue'
import KitchenView from '../views/KitchenView.vue'
import AppLayout from '../layouts/AppLayout.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/login'
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
        {
          path: 'dashboard',
          name: 'dashboard',
          component: DashboardView
        },
        {
          path: 'categories',
          name: 'categories',
          component: CategoryManager
        },
        {
          path: 'dishes',
          name: 'dishes',
          component: DishManager
        },
        {
          path: 'tables',
          name: 'tables',
          component: TableManager
        },
        {
          path: 'orders',
          name: 'orders',
          component: OrderManager
        },
        {
          path: 'settings',
          name: 'settings',
          component: SettingsView
        }
      ]
    },
    {
      path: '/kitchen',
      name: 'kitchen',
      component: KitchenView,
      meta: { requiresAuth: false }
    }
  ]
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')

  if (to.meta.requiresAuth !== false && !token) {
    // 需要认证但未登录，跳转到登录页
    next('/login')
  } else if (to.path === '/login' && token) {
    // 已登录但访问登录页，跳转到首页
    next('/dashboard')
  } else {
    next()
  }
})

export default router
