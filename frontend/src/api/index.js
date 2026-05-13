import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// 响应拦截器：提取 data 字段
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API 请求失败:', error)
    return Promise.reject(error)
  }
)

export function fetchNews(params = {}) {
  return api.get('/news', { params })
}

export function fetchHealth() {
  return api.get('/health')
}

export default api
