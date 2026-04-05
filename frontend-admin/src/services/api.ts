import axios from 'axios'
import router from '@/router'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8002'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器：添加 JWT Token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：处理 401 Token 过期
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

// 分类管理API
export const categoryApi = {
  // 获取分类列表
  getCategories: () => api.get('/api/v1/admin/categories'),
  
  // 创建分类
  createCategory: (data: { name: string; sort_order?: number }) => 
    api.post('/api/v1/admin/categories', data),
  
  // 更新分类
  updateCategory: (id: number, data: { name: string; sort_order?: number }) => 
    api.put(`/api/v1/admin/categories/${id}`, data),
  
  // 删除分类
  deleteCategory: (id: number) => 
    api.delete(`/api/v1/admin/categories/${id}`)
}

// 菜品管理API
export const dishApi = {
  // 获取菜品列表
  getDishes: (params?: {
    category_id?: number;
    is_available?: boolean;
    search?: string;
    page?: number;
    limit?: number;
  }) => api.get('/api/v1/admin/dishes', { params }),
  
  // 创建菜品
  createDish: (data: {
    name: string;
    price: number;
    description?: string;
    image_url?: string;
    category_id: number;
    is_available: boolean;
  }) => api.post('/api/v1/admin/dishes', data),
  
  // 获取菜品详情
  getDish: (id: number) => 
    api.get(`/api/v1/admin/dishes/${id}`),
  
  // 更新菜品
  updateDish: (id: number, data: {
    name?: string;
    price?: number;
    description?: string;
    image_url?: string;
    category_id?: number;
    is_available?: boolean;
  }) => api.put(`/api/v1/admin/dishes/${id}`, data),
  
  // 切换上下架
  toggleAvailable: (id: number) => 
    api.patch(`/api/v1/admin/dishes/${id}/toggle-available`),
  
  // 删除菜品
  deleteDish: (id: number) => 
    api.delete(`/api/v1/admin/dishes/${id}`)
}

// 桌台管理API
export const tableApi = {
  // 获取桌台列表
  getTables: () => api.get('/api/v1/admin/tables'),
  
  // 创建桌台
  createTable: (data: { code: string; name: string; capacity?: number; status?: string }) => 
    api.post('/api/v1/admin/tables', data),
  
  // 获取桌台详情
  getTable: (id: number) => 
    api.get(`/api/v1/admin/tables/${id}`),
  
  // 更新桌台
  updateTable: (id: number, data: { code?: string; name?: string; capacity?: number; status?: string }) => 
    api.put(`/api/v1/admin/tables/${id}`, data),
  
  // 删除桌台
  deleteTable: (id: number) => 
    api.delete(`/api/v1/admin/tables/${id}`)
}

// 订单管理API
export const orderApi = {
  // 获取订单列表
  getOrders: (params?: { status?: string; page?: number; limit?: number }) => 
    api.get('/api/v1/admin/orders', { params }),
  
  // 获取订单详情
  getOrder: (id: number) => 
    api.get(`/api/v1/admin/orders/${id}`),
  
  // 更新订单状态
  updateOrderStatus: (id: number, status: string) => 
    api.put(`/api/v1/admin/orders/${id}/status`, { status }),
  
  // 获取小票内容
  getOrderTicket: (id: number) => 
    api.get(`/api/v1/admin/orders/${id}/ticket`)
}

// 统计API
export const statsApi = {
  // 获取今日统计
  getTodayStats: () => 
    api.get('/api/v1/admin/stats/today'),
  
  // 获取销售统计
  getSalesStats: (params?: { period?: 'day' | 'week' | 'month'; date_range?: string }) => 
    api.get('/api/v1/admin/stats/sales', { params })
}

// 商户设置API
export const merchantApi = {
  // 获取商户信息
  getProfile: () => 
    api.get('/api/v1/admin/merchant/profile'),
  
  // 更新商户信息
  updateProfile: (data: {
    name?: string;
    phone?: string;
    address?: string;
    business_hours?: string;
    announcement?: string;
  }) => api.put('/api/v1/admin/merchant/profile', data),
  
  // 修改密码
  changePassword: (data: { old_password: string; new_password: string }) => 
    api.post('/api/v1/admin/merchant/change-password', data),
  
  // 获取商户支付设置（Phase 2）
  getPaymentSettings: () =>
    api.get('/api/v1/admin/settings'),
  
  // 更新商户支付设置（Phase 2）
  updatePaymentSettings: (data: { mode: 'counter_pay' | 'credit_pay' }) =>
    api.put('/api/v1/admin/settings', data)
}

export default api