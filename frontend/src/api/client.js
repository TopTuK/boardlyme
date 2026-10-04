import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('bm_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export async function tryRefresh() {
  const refreshToken = localStorage.getItem('bm_refresh')
  if (!refreshToken) return false
  try {
    const { data } = await axios.post('/api/auth/refresh', { refresh_token: refreshToken })
    localStorage.setItem('bm_token', data.access_token)
    localStorage.setItem('bm_refresh', data.refresh_token)
    return true
  } catch {
    return false
  }
}

api.interceptors.response.use(undefined, async (error) => {
  const original = error.config
  if (error.response && error.response.status === 401 && original && !original._retried) {
    original._retried = true
    if (await tryRefresh()) {
      original.headers = original.headers || {}
      original.headers.Authorization = `Bearer ${localStorage.getItem('bm_token')}`
      return api(original)
    }
    localStorage.removeItem('bm_token')
    localStorage.removeItem('bm_refresh')
    localStorage.removeItem('bm_user')
    if (!window.location.pathname.startsWith('/login')) window.location.href = '/login'
  }
  return Promise.reject(error)
})

export default api
