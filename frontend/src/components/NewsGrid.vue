<template>
  <div v-if="loading" class="loading">
    <div class="spinner"></div>
    <p>加载中...</p>
  </div>
  <div v-else-if="items.length === 0" class="empty-state">
    <p>暂无相关资讯</p>
  </div>
  <div v-else class="news-grid">
    <NewsCard v-for="item in items" :key="item.id" :news="item" :keyword="keyword" />
  </div>
</template>

<script setup>
import NewsCard from './NewsCard.vue'

defineProps({
  items: { type: Array, default: () => [] },
  keyword: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})
</script>
