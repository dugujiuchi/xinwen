<template>
  <div class="source-list">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-filters">
        <input
          v-model="searchQuery"
          type="text"
          class="form-input"
          placeholder="搜索数据源名称..."
          @input="onSearchInput"
        />
        <select v-model="categoryFilter" class="form-select" @change="onFilterChange">
          <option value="">全部栏目</option>
          <option v-for="(label, key) in categoryLabelMap" :key="key" :value="key">{{ label }}</option>
        </select>
      </div>
      <router-link to="/admin/sources/new" class="btn btn-primary">
        + 新增数据源
      </router-link>
    </div>

    <!-- 数据表格 -->
    <table class="admin-table">
      <thead>
        <tr>
          <th style="width: 60px">序号</th>
          <th>名称</th>
          <th>标识</th>
          <th>栏目</th>
          <th>抓取方式</th>
          <th style="width: 80px">状态</th>
          <th style="width: 220px">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading">
          <td colspan="7" class="empty-cell">
            <div class="spinner"></div>
            <p>加载中...</p>
          </td>
        </tr>
        <tr v-else-if="errorMsg">
          <td colspan="7" class="empty-cell error-text">{{ errorMsg }}</td>
        </tr>
        <tr v-else-if="sources.length === 0">
          <td colspan="7" class="empty-cell">暂无数据</td>
        </tr>
        <tr v-for="(source, index) in sources" :key="source.id">
          <td>{{ (currentPage - 1) * pageSize + index + 1 }}</td>
          <td>{{ source.display_name }}</td>
          <td><code>{{ source.name }}</code></td>
          <td>{{ categoryLabel(source.category) }}</td>
          <td>{{ source.crawl_type }}</td>
          <td>
            <label class="toggle-switch">
              <input
                type="checkbox"
                :checked="source.is_active"
                @change="toggleActive(source)"
              />
              <span class="toggle-slider"></span>
            </label>
          </td>
          <td class="action-cell">
            <router-link
              :to="`/admin/sources/${source.id}/edit`"
              class="btn btn-sm btn-outline"
            >
              编辑
            </router-link>
            <button class="btn btn-sm btn-outline" :disabled="crawlingId === source.id" @click="doCrawl(source)">
              {{ crawlingId === source.id ? '抓取中...' : '抓取' }}
            </button>
            <button class="btn btn-sm btn-danger" @click="confirmDelete(source)">
              删除
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- 分页 -->
    <Pagination v-model="currentPage" :total="total" :size="pageSize" />

    <!-- 删除确认框 -->
    <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
      <div class="modal confirm-modal">
        <div class="modal-header">
          <h3>确认删除</h3>
        </div>
        <div class="modal-body">
          <p>确定要删除数据源 <strong>{{ deleteTarget?.display_name }}</strong> 吗？</p>
          <p class="warning-text">此操作不可撤销</p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-default" @click="showDeleteConfirm = false">取消</button>
          <button class="btn btn-danger" :disabled="deleting" @click="doDelete">
            {{ deleting ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { fetchSources, updateSource, deleteSource, crawlSingleSource, categoryLabel, categoryLabelMap } from '../api/index.js'
import Pagination from '../components/Pagination.vue'

// 列表数据
const sources = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const searchQuery = ref('')
const categoryFilter = ref('')
const loading = ref(false)
const errorMsg = ref('')
let searchTimer = null

// 单源抓取
const crawlingId = ref(null)

// 删除
const showDeleteConfirm = ref(false)
const deleteTarget = ref(null)
const deleting = ref(false)

function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    loadSources()
  }, 400)
}

function onFilterChange() {
  currentPage.value = 1
  loadSources()
}

watch(currentPage, loadSources)

async function loadSources() {
  loading.value = true
  errorMsg.value = ''
  try {
    const params = {
      page: currentPage.value,
      size: pageSize,
    }
    if (searchQuery.value) params.search = searchQuery.value
    if (categoryFilter.value) params.category = categoryFilter.value

    const resp = await fetchSources(params)
    sources.value = resp.data.items || []
    total.value = resp.data.total || 0
  } catch (e) {
    sources.value = []
    total.value = 0
    errorMsg.value = '加载数据源列表失败，请检查网络连接'
  } finally {
    loading.value = false
  }
}

async function toggleActive(source) {
  try {
    await updateSource(source.id, { is_active: !source.is_active })
    source.is_active = !source.is_active
  } catch (e) {
    alert('切换状态失败，请重试')
  }
}

async function doCrawl(source) {
  crawlingId.value = source.id
  try {
    const resp = await crawlSingleSource(source.id)
    alert(resp.message || '抓取完成')
    loadSources()
  } catch (e) {
    alert(e.response?.data?.detail || '抓取失败，请重试')
  } finally {
    crawlingId.value = null
  }
}

function confirmDelete(source) {
  deleteTarget.value = source
  showDeleteConfirm.value = true
}

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await deleteSource(deleteTarget.value.id)
    showDeleteConfirm.value = false
    deleteTarget.value = null
    loadSources()
  } catch (e) {
    alert(e.response?.data?.message || '删除失败，请重试')
  } finally {
    deleting.value = false
  }
}

onMounted(loadSources)

onUnmounted(() => {
  clearTimeout(searchTimer)
})
</script>
