<template>
  <div>
    <SearchBar v-model="searchKeyword" />

    <TabNav :tabs="tabs" v-model="currentTab" />

    <TagFilter
      v-if="currentTags.length > 0"
      :tags="currentTags"
      v-model="currentTag"
    />

    <NewsGrid :items="newsItems" :keyword="searchKeyword" :loading="loading" />

    <Pagination
      v-model="currentPage"
      :total="total"
      :size="pageSize"
    />
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { fetchNews } from '../api/index.js'
import SearchBar from '../components/SearchBar.vue'
import TabNav from '../components/TabNav.vue'
import TagFilter from '../components/TagFilter.vue'
import NewsGrid from '../components/NewsGrid.vue'
import Pagination from '../components/Pagination.vue'

const tabs = [
  { key: 'ai', label: '科技前沿资讯' },
  { key: 'industry', label: '资规行业资讯' },
  { key: 'tech', label: '大模型学习资料' },
  { key: 'media', label: '媒体新闻' },
]

const tagMap = {
  ai: [
    { key: '', label: '全部' },
    { key: '智能体', label: '智能体' },
    { key: '大模型', label: '大模型' },
    { key: '图像', label: '图像' },
    { key: '无人机', label: '无人机' },
  ],
  industry: [
    { key: '', label: '全部' },
  ],
  tech: [
    { key: '', label: '全部' },
    { key: 'Clip', label: 'Clip' },
    { key: '图像', label: '图像检测' },
  ],
  media: [
    { key: '', label: '全部' },
    { key: '麻辣GIS', label: '麻辣GIS' },
    { key: 'DoNews', label: 'DoNews' },
    { key: '资源中国', label: '资源中国' },
  ],
}

const currentTab = ref('ai')
const currentTag = ref('')
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = 20
const total = ref(0)
const newsItems = ref([])
const loading = ref(false)

const currentTags = computed(() => tagMap[currentTab.value] || [])

async function loadNews() {
  loading.value = true
  try {
    const search = currentTag.value || searchKeyword.value
    const resp = await fetchNews({
      page: currentPage.value,
      size: pageSize,
      search: search || undefined,
    })
    newsItems.value = resp.data.items
    total.value = resp.data.total
  } catch (e) {
    newsItems.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

watch([currentTab, currentPage], loadNews)

let timer = null
watch(searchKeyword, () => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    currentPage.value = 1
    loadNews()
  }, 400)
})

watch(currentTag, () => {
  currentPage.value = 1
  loadNews()
})

loadNews()
</script>
