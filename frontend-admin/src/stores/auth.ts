import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import router from '@/router'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8003'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || '')
  const merchantId = ref(localStorage.getItem('merchant_id') || '')
  const merchantName = ref(localStorage.getItem('merchant_name') || '')

  // 登录
  const login = async (username: string, password: string) => {
    try {
      const response = await axios.post(`${API_BASE}/api/v1/admin/auth/login`, {
        username,
        password
      })
      
      const { access_token, merchant_id } = response.data
      
      // 保存token和商户信息
      token.value = access_token
      merchantId.value = merchant_id.toString()
      
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('merchant_id', merchant_id.toString())
      
      // 设置axios默认请求头
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      
      return { success: true }
    } catch (error: any) {
      console.error('登录失败:', error)
      return { 
        success: false, 
        message: error.response?.data?.detail || '登录失败，请检查用户名和密码' 
      }
    }
  }

  // 注册
  const register = async (name: string, username: string, password: string) => {
    try {
      const response = await axios.post(`${API_BASE}/api/v1/admin/auth/register`, {
        name,
        username,
        password
      })
      
      const { access_token, merchant_id } = response.data
      
      // 保存token和商户信息
      token.value = access_token
      merchantId.value = merchant_id.toString()
      merchantName.value = name
      
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('merchant_id', merchant_id.toString())
      localStorage.setItem('merchant_name', name)
      
      // 设置axios默认请求头
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      
      return { success: true }
    } catch (error: any) {
      console.error('注册失败:', error)
      return { 
        success: false, 
        message: error.response?.data?.detail || '注册失败，请稍后重试' 
      }
    }
  }

  // 登出
  const logout = () => {
    token.value = ''
    merchantId.value = ''
    merchantName.value = ''
    
    localStorage.removeItem('access_token')
    localStorage.removeItem('merchant_id')
    localStorage.removeItem('merchant_name')
    
    delete axios.defaults.headers.common['Authorization']
    
    router.push('/login')
  }

  // 初始化axios配置
  const initAxios = () => {
    const storedToken = localStorage.getItem('access_token')
    if (storedToken) {
      token.value = storedToken
      axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`
    }
    
    // 配置响应拦截器
    axios.interceptors.response.use(
      response => response,
      error => {
        if (error.response?.status === 401) {
          // token过期或无效，清除登录状态
          logout()
        }
        return Promise.reject(error)
      }
    )
  }

  return {
    token,
    merchantId,
    merchantName,
    login,
    register,
    logout,
    initAxios
  }
})