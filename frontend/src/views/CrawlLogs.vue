<template>
  <div class="crawl-logs-page">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <h2 class="page-title">爬取日志</h2>
      <button class="btn btn-primary" :disabled="triggering" @click="triggerFullCrawl">
        {{ triggering ? '触发中...' : '触发全量爬取' }}
      </button>
    </div>

    <!-- 日志表格 -->
    <table class="admin-table">
      <thead>
        <tr>
          <th>时间</th>
          <th>数据源名称</th>
          <th>状态</th>
          <th>抓取数量</th>
          <th>错误信息</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading">
          <td colspan="5" class="empty-cell">
            <div class="spinner"></div>
            <p>加载中...</p>
          </td>
        </tr>
        <tr v-else-if="errorMsg">
          <td colspan="5" class="empty-cell error-text">{{ errorMsg }}</td>
        </tr>
        <tr v-else-if="logs.length === 0">
          <td colspan="5" class="empty-cell">暂无爬取日志</td>
        </tr>
        <tr v-for="log in logs" :key="log.id">
          <td>{{ formatTime(log.started_at) }}</td>
          <td>{{ log.source_name || log.source_id }}</td>
          <td>
            <span v-if="log.status === 'running'" class="status-badge status-running">
              <span class="spin-icon">&#8635;</span> 运行中
            </span>
            <span v-else-if="log.status === 'success'" class="status-badge status-success">
              成功
            </span>
            <span v-else-if="log.status === 'failed'" class="status-badge status-failed">
              失败
            </span>
            <span v-else class="status-badge">{{ log.status }}</span>
          </td>
          <td>{{ log.items_count ?? '-' }}</td>
          <td class="error-cell">{{ log.error_message || '-' }}</td>
        </tr>
      </tbody>
    </table>

    <!-- 分页 -->
    <Pagination v-model="currentPage" :total="total" :size="pageSize" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { triggerCrawl, fetchCrawlLogs } from '../api/index.js'
import Pagination from '../components/Pagination.vue'

const logs = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const triggering = ref(false)
const loading = ref(false)
const errorMsg = ref('')

let autoRefreshTimer = null

function formatTime(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function loadLogs() {
  loading.value = true
  errorMsg.value = ''
  try {
    const resp = await fetchCrawlLogs({ page: currentPage.value, size: pageSize })
    logs.value = resp.data.items || []
    total.value = resp.data.total || 0
  } catch (e) {
    logs.value = []
    total.value = 0
    errorMsg.value = '加载爬取日志失败，请检查网络连接'
  } finally {
    loading.value = false
  }
}

async function triggerFullCrawl() {
  triggering.value = true
  try {
    await triggerCrawl()
    // 触发后立即刷新日志
    currentPage.value = 1
    await loadLogs()
  } catch (e) {
    alert(e.response?.data?.message || '触发爬取失败，请重试')
  } finally {
    triggering.value = false
  }
}

function startAutoRefresh() {
  stopAutoRefresh()
  autoRefreshTimer = setInterval(loadLogs, 10000)
}

function stopAutoRefresh() {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
}

watch(currentPage, loadLogs)

onMounted(() => {
  loadLogs()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>
