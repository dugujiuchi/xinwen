<template>
  <div>
    <div class="top-bar">
      <SearchBar v-model="searchKeyword" />
      <router-link to="/admin" class="admin-link">管理</router-link>
    </div>

    <TabNav :tabs="tabs" v-model="currentTab" />

    <TagFilter v-if="currentTags.length > 0" :tags="currentTags" v-model="currentTag" />

    <NewsGrid :items="newsItems" :keyword="searchKeyword" :loading="loading" />

    <Pagination v-model="currentPage" :total="total" :size="pageSize" />
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, onUnmounted } from 'vue'
import { fetchNews, fetchCategories, fetchTags, categoryLabelMap } from '../api/index.js'
import SearchBar from '../components/SearchBar.vue'
import TabNav from '../components/TabNav.vue'
import TagFilter from '../components/TagFilter.vue'
import NewsGrid from '../components/NewsGrid.vue'
import Pagination from '../components/Pagination.vue'

const tabs = ref([])
const allTags = ref([])
const currentTab = ref('')
const currentTag = ref('')
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = 20
const total = ref(0)
const newsItems = ref([])
const loading = ref(false)

// 获取当前 tab 对应的标签列表
const currentTags = computed(() => {
  const tags = allTags.value || []
  return [{ key: '', label: '全部' }, ...tags.map(t => ({ key: t, label: t }))]
})

// 初始化：获取分类
onMounted(async () => {
  try {
    const catResp = await fetchCategories()
    const categories = catResp.data || {}
    tabs.value = Object.keys(categories).map(key => ({
      key,
      label: categoryLabelMap[key] || key,
    }))
    if (tabs.value.length > 0) {
      currentTab.value = 'industry'
    }
  } catch (e) {
    tabs.value = Object.entries(categoryLabelMap).map(([key, label]) => ({ key, label }))
    currentTab.value = 'industry'
  }
})

async function loadTags() {
  try {
    const cat = currentTab.value || undefined
    const resp = await fetchTags(cat)
    allTags.value = resp.data || []
    // 切栏目时清除已选标签
    currentTag.value = ''
  } catch (e) {
    allTags.value = []
  }
}

async function loadNews() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      size: pageSize,
      category: currentTab.value || undefined,
    }
    // 只有当前选中的标签不为空时传 tags 参数
    if (currentTag.value) {
      params.tags = currentTag.value
    }
    // 搜索关键词
    if (searchKeyword.value) {
      params.search = searchKeyword.value
    }
    const resp = await fetchNews(params)
    newsItems.value = resp.data.items
    total.value = resp.data.total
  } catch (e) {
    newsItems.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

// 切换栏目：先加载标签，再加载新闻（避免 loadTags 清空 currentTag 触发二次请求）
async function onTabChange() {
  await loadTags()          // 会清空 currentTag，但不会触发 watch（已在同一调用链）
  currentPage.value = 1
  loadNews()
}
watch(currentTab, onTabChange)

// 仅翻页
watch(currentPage, () => loadNews())

// 搜索防抖
let timer = null
watch(searchKeyword, () => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    currentPage.value = 1
    loadNews()
  }, 400)
})

// 标签筛选
watch(currentTag, () => {
  currentPage.value = 1
  loadNews()
})

onUnmounted(() => {
  clearTimeout(timer)
})
</script>

<style scoped>
.top-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.top-bar> :first-child {
  flex: 1;
}

.admin-link {
  flex-shrink: 0;
  padding: 6px 16px;
  font-size: 14px;
  color: #666;
  text-decoration: none;
  border: 1px solid #ddd;
  border-radius: 6px;
  transition: all 0.2s;
}

.admin-link:hover {
  color: #333;
  border-color: #999;
  background: #f5f5f5;
}

@media (max-width: 480px) {
  .top-bar {
    gap: 8px;
  }
  .admin-link {
    padding: 4px 10px;
    font-size: 12px;
  }
}
</style>
