<template>
  <div class="news-card">
    <div class="news-card-header">
      <span class="source-tag">{{ news.source_name }}</span>
      <span v-if="isToday()" class="today-badge">今日</span>
      <span class="time-text">{{ formatTime(news.pub_time) }}</span>
    </div>
    <h3 class="news-card-title">
      <a :href="news.link" target="_blank" rel="noopener noreferrer"
         v-html="highlightTitle(news.title)"></a>
    </h3>
    <div class="news-card-footer">
      <a :href="news.link" target="_blank" rel="noopener noreferrer" class="read-link">
        阅读全文
      </a>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  news: { type: Object, required: true },
  keyword: { type: String, default: '' },
})

function formatTime(timeStr) {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${m}-${day} ${h}:${min}`
}

function isToday() {
  if (!props.news.pub_time) return false
  const d = new Date(props.news.pub_time)
  return d.toDateString() === new Date().toDateString()
}

// HTML 转义映射
const HTML_ENTITIES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }
function escapeHtml(str) { return String(str).replace(/[&<>"']/g, ch => HTML_ENTITIES[ch]) }

function highlightTitle(title) {
  const safe = escapeHtml(title)
  if (!props.keyword || !safe) return safe
  const regex = new RegExp(`(${escapeRegExp(props.keyword)})`, 'gi')
  return safe.replace(regex, '<span class="highlight">$1</span>')
}

function escapeRegExp(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
</script>
