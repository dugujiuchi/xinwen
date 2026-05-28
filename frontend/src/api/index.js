import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// 响应拦截器：提取 data 字段，403 时通知管理端重登
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 403) {
      localStorage.removeItem('admin_password')
      window.dispatchEvent(new Event('admin-auth-expired'))
    }
    console.error('API 请求失败:', error)
    return Promise.reject(error)
  }
)

// 管理端 API 辅助 —— 从 localStorage 取密码
function getAdminHeaders() {
  const pwd = localStorage.getItem('admin_password') || ''
  return { 'X-Admin-Key': pwd }
}

// 栏目中文映射（唯一数据源，供全前端使用）
export const categoryLabelMap = {
  ai: '科技前沿资讯',
  industry: '资规行业资讯',
  tech: '大模型学习资料',
  media: '媒体新闻',
}
export function categoryLabel(cat) {
  return categoryLabelMap[cat] || cat
}

// 公开 API
export function fetchNews(params = {}) {
  return api.get('/news', { params })
}

export function fetchHealth() {
  return api.get('/health')
}

export function fetchCategories() {
  return api.get('/categories')
}

export function fetchTags(category) {
  return api.get('/tags', { params: category ? { category } : {} })
}

// 管理端 API
export function fetchSources(params = {}) {
  return api.get('/admin/sources', { params, headers: getAdminHeaders() })
}

export function fetchSource(id) {
  return api.get(`/admin/sources/${id}`, { headers: getAdminHeaders() })
}

export function createSource(data) {
  return api.post('/admin/sources', data, { headers: getAdminHeaders() })
}

export function updateSource(id, data) {
  return api.put(`/admin/sources/${id}`, data, { headers: getAdminHeaders() })
}

export function deleteSource(id) {
  return api.delete(`/admin/sources/${id}`, { headers: getAdminHeaders() })
}

export function testCrawlSource(id) {
  return api.post(`/admin/sources/${id}/test`, {}, { headers: getAdminHeaders() })
}

export function crawlSingleSource(id) {
  return api.post(`/admin/sources/${id}/crawl`, {}, { headers: getAdminHeaders() })
}

export function testConfigCrawl(crawlType, config) {
  return api.post('/admin/sources/test-config', { crawl_type: crawlType, config }, { headers: getAdminHeaders() })
}

export function analyzeSource(url) {
  return api.post('/admin/sources/analyze', { url }, { headers: getAdminHeaders() })
}

export function triggerCrawl() {
  return api.post('/admin/crawl/trigger', {}, { headers: getAdminHeaders() })
}

export function fetchCrawlLogs(params = {}) {
  return api.get('/admin/crawl/logs', { params, headers: getAdminHeaders() })
}

export function fetchStats() {
  return api.get('/admin/stats', { headers: getAdminHeaders() })
}

// 验证管理密码
export function verifyAdminPassword(password) {
  return api.get('/admin/sources', { params: { size: 1 }, headers: { 'X-Admin-Key': password } })
}

// 访客记录
export function recordVisit() {
  return api.post('/visitor/record')
}

export function fetchVisitorStats(period = 'week') {
  return api.get('/visitor/admin/stats', { params: { period }, headers: getAdminHeaders() })
}

export function fetchVisitorLogs(params = {}) {
  return api.get('/visitor/admin/logs', { params, headers: getAdminHeaders() })
}

export default api
