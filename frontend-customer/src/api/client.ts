const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

interface TokenData {
  access_token: string
  refresh_token: string
  expires_in: number
}

// 从 URL 获取 tenant 和 table_id
function getUrlParams() {
  const params = new URLSearchParams(window.location.search)
  return {
    tenant: params.get('tenant') || '',
    table_id: params.get('table_id') || ''
  }
}

export const apiClient = {
  getToken(): string | null {
    return localStorage.getItem('customer_access_token')
  },

  setToken(data: TokenData) {
    localStorage.setItem('customer_access_token', data.access_token)
    localStorage.setItem('customer_refresh_token', data.refresh_token)
    localStorage.setItem('customer_token_expires', String(Date.now() + data.expires_in * 1000))
  },

  clearToken() {
    localStorage.removeItem('customer_access_token')
    localStorage.removeItem('customer_refresh_token')
    localStorage.removeItem('customer_token_expires')
  },

  getTenant(): string {
    return localStorage.getItem('customer_tenant') || ''
  },

  setTenant(tenant: string) {
    localStorage.setItem('customer_tenant', tenant)
  },

  getTableId(): string {
    return localStorage.getItem('customer_table_id') || ''
  },

  setTableId(tableId: string) {
    localStorage.setItem('customer_table_id', tableId)
  },

  async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken()
    const tenant = this.getTenant()
    const tableId = this.getTableId()
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    }
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    
    // 添加 tenant 和 table_id 到查询参数
    const url = new URL(`${API_BASE}${path}`, window.location.origin)
    if (tenant) url.searchParams.set('tenant', tenant)
    if (tableId) url.searchParams.set('table_id', tableId)
    
    const res = await fetch(url.toString(), {
      ...options,
      headers,
    })

    if (res.status === 401) {
      this.clearToken()
      throw new Error('Unauthorized')
    }

    if (res.status === 403) {
      const body = await res.json().catch(() => ({}))
      window.dispatchEvent(new CustomEvent('show-upgrade-modal', { detail: body }))
      throw new Error('Upgrade required')
    }

    if (!res.ok) {
      throw new Error(`API Error: ${res.status}`)
    }

    return res.json()
  },

  get<T>(path: string) { return this.request<T>(path) },
  post<T>(path: string, body: unknown) { return this.request<T>(path, { method: 'POST', body: JSON.stringify(body) }) },
}

// 从 URL 初始化 tenant 和 table_id
const urlParams = getUrlParams()
if (urlParams.tenant) apiClient.setTenant(urlParams.tenant)
if (urlParams.table_id) apiClient.setTableId(urlParams.table_id)
