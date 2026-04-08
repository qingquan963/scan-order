import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import DashboardView from '../views/DashboardView.vue'
import CategoryManager from '../views/CategoryManager.vue'
import DishManager from '../views/DishManager.vue'
import TableManager from '../views/TableManager.vue'
import OrderManager from '../views/OrderManager.vue'
import SettingsView from '../views/SettingsView.vue'
import TenantSettingsView from '../views/TenantSettingsView.vue'
import PricingView from '../views/PricingView.vue'
import KitchenView from '../views/KitchenView.vue'
import AppLayout from '../layouts/AppLayout.vue'
import { apiClient } from '../api/client'

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
      path: '/register',
      name: 'register',
      component: RegisterView,
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
        {
          path: 'admin/panel',
          name: 'admin-panel',
          component: DashboardView
        },
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
        },
        {
          path: 'tenant-settings',
          name: 'tenant-settings',
          component: TenantSettingsView
        },
        {
          path: 'pricing',
          name: 'pricing',
          component: PricingView
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
  const publicPages = ['/login', '/register']
  if (publicPages.includes(to.path)) {
    return next()
  }
  if (!apiClient.getToken()) {
    return next('/login')
  }
  next()
})

export default router
