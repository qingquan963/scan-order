/**
 * Phase Kitchen - 后厨屏 API 服务
 */
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8002'

const kitchenApi = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器：添加后厨令牌
kitchenApi.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('kitchen_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：处理错误
kitchenApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // 网络错误（如断网、超时）
    if (!error.response) {
      return Promise.reject({ networkError: true, error })
    }

    // 409 Conflict：并发冲突（乐观锁失败）
    if (error.response.status === 409) {
      return Promise.reject({ conflict: true, data: error.response.data })
    }

    // 401 Unauthorized：厨房令牌失效
    if (error.response.status === 401) {
      localStorage.removeItem('kitchen_token')
      return Promise.reject({ unauthorized: true })
    }

    return Promise.reject(error)
  }
)

// ─── API 方法 ────────────────────────────────────────────────

export const kitchenAuthApi = {
  /** 验证 PIN 码，获取后厨访问令牌 */
  login: (pin: string) =>
    kitchenApi.post('/api/v1/admin/kitchen/auth', { pin })
}

export const kitchenOrderApi = {
  /**
   * 获取后厨订单列表
   * @param status - pending(待接单) / preparing(制作中) / all
   * @param page - 页码
   * @param pageSize - 每页条数
   */
  getOrders: (params: {
    status?: string
    page?: number
    page_size?: number
  }) => kitchenApi.get('/api/v1/admin/kitchen/orders', { params }),

  /**
   * 厨房接单
   */
  acceptOrder: (orderId: number) =>
    kitchenApi.put(`/api/v1/admin/kitchen/orders/${orderId}/accept`),

  /**
   * 标记菜品完成
   */
  markItemDone: (orderId: number, itemId: number) =>
    kitchenApi.put(`/api/v1/admin/kitchen/orders/${orderId}/items/${itemId}/done`),

  /**
   * 撤销菜品完成
   */
  markItemUndone: (itemId: number) =>
    kitchenApi.put(`/api/v1/admin/kitchen/items/${itemId}/undone`),

  /**
   * 重置订单到待接单
   */
  resetOrder: (orderId: number) =>
    kitchenApi.put(`/api/v1/admin/kitchen/orders/${orderId}/reset`)
}

export default kitchenApi
