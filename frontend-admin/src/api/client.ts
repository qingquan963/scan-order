const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

interface TokenData {
  access_token: string
  refresh_token: string
  expires_in: number
}

export const apiClient = {
  getToken(): string | null {
    return localStorage.getItem('access_token')
  },

  setToken(data: TokenData) {
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    localStorage.setItem('token_expires', String(Date.now() + data.expires_in * 1000))
  },

  clearToken() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('token_expires')
  },

  async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken()
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    }
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    })

    if (res.status === 401) {
      this.clearToken()
      window.location.href = '/login'
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
