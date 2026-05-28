<template>
  <div class="visitor-logs">
    <h3 class="section-title">访客记录</h3>

    <!-- 周期切换 -->
    <div class="period-tabs">
      <button :class="['btn', period === 'week' ? 'btn-primary' : 'btn-outline']" @click="period = 'week'; loadStats()">
        近 7 天
      </button>
      <button :class="['btn', period === 'month' ? 'btn-primary' : 'btn-outline']" @click="period = 'month'; loadStats()">
        近 30 天
      </button>
    </div>

    <!-- 统计概览卡片 -->
    <div class="stats-overview">
      <div class="stat-card">
        <div class="stat-value">{{ stats.period_visits }}</div>
        <div class="stat-label">{{ period === 'week' ? '近7天访问' : '近30天访问' }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_visits }}</div>
        <div class="stat-label">历史总访问</div>
      </div>
    </div>

    <!-- 每日趋势表格 -->
    <div class="stats-section">
      <h4>每日趋势</h4>
      <table class="admin-table" v-if="stats.daily && stats.daily.length > 0">
        <thead>
          <tr>
            <th>日期</th>
            <th>访问量</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in stats.daily" :key="d.day">
            <td>{{ d.day }}</td>
            <td>{{ d.count }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-cell">暂无数据</div>
    </div>

    <!-- 省份分布 -->
    <div class="stats-section">
      <h4>省份分布</h4>
      <table class="admin-table" v-if="stats.by_region && stats.by_region.length > 0">
        <thead>
          <tr>
            <th>省份</th>
            <th>访问量</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in stats.by_region" :key="r.region">
            <td>{{ r.region }}</td>
            <td>{{ r.count }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-cell">暂无数据</div>
    </div>

    <!-- 城市分布 Top 20 -->
    <div class="stats-section">
      <h4>城市分布（Top 20）</h4>
      <table class="admin-table" v-if="stats.by_city && stats.by_city.length > 0">
        <thead>
          <tr>
            <th>城市</th>
            <th>省份</th>
            <th>访问量</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in stats.by_city" :key="c.city + c.region">
            <td>{{ c.city }}</td>
            <td>{{ c.region }}</td>
            <td>{{ c.count }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-cell">暂无数据</div>
    </div>

    <!-- 访问明细 -->
    <div class="stats-section">
      <h4>最近访问明细</h4>
      <table class="admin-table" v-if="logs.length > 0">
        <thead>
          <tr>
            <th>IP</th>
            <th>国家</th>
            <th>省份</th>
            <th>城市</th>
            <th>运营商</th>
            <th>访问时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id">
            <td>{{ log.ip }}</td>
            <td>{{ log.country }}</td>
            <td>{{ log.region }}</td>
            <td>{{ log.city }}</td>
            <td>{{ log.isp }}</td>
            <td>{{ formatTime(log.visit_time) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else-if="!loading" class="empty-cell">暂无数据</div>

      <div class="pagination-bar" v-if="total > pageSize">
        <button class="btn btn-outline" :disabled="page <= 1" @click="page--; loadLogs()">上一页</button>
        <span>{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
        <button class="btn btn-outline" :disabled="page >= Math.ceil(total / pageSize)" @click="page++; loadLogs()">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchVisitorStats, fetchVisitorLogs } from '../api/index.js'

const period = ref('week')
const stats = ref({})
const logs = ref([])
const page = ref(1)
const pageSize = 20
const total = ref(0)
const loading = ref(false)

onMounted(() => {
  loadStats()
  loadLogs()
})

async function loadStats() {
  try {
    const resp = await fetchVisitorStats(period.value)
    stats.value = resp.data
  } catch (e) {
    stats.value = {}
  }
}

async function loadLogs() {
  loading.value = true
  try {
    const resp = await fetchVisitorLogs({ page: page.value, size: pageSize })
    logs.value = resp.data.items
    total.value = resp.data.total
  } catch (e) {
    logs.value = []
  } finally {
    loading.value = false
  }
}

function formatTime(t) {
  if (!t) return ''
  return t.replace('T', ' ').substring(0, 19)
}
</script>

<style scoped>
.period-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.stats-overview {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}
.stat-card {
  flex: 1;
  background: #f0f7ff;
  border: 1px solid #d0e3f7;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1a73e8;
}
.stat-label {
  font-size: 13px;
  color: #666;
  margin-top: 4px;
}
.stats-section {
  margin-bottom: 24px;
}
.stats-section h4 {
  font-size: 15px;
  margin-bottom: 10px;
  color: #333;
}
</style>
