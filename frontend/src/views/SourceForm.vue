<template>
  <div class="source-form-page">
    <h2 class="page-title">{{ isEdit ? '编辑数据源' : '新增数据源' }}</h2>

    <!-- 模式切换 -->
    <div class="mode-switch">
      <button
        :class="['mode-btn', { active: mode === 'simple' }]"
        @click="switchMode('simple')"
      >简单模式</button>
      <button
        :class="['mode-btn', { active: mode === 'advanced' }]"
        @click="switchMode('advanced')"
      >高级模式</button>
    </div>

    <!-- 基础信息 -->
    <div class="form-section">
      <div class="form-group">
        <label class="form-label">标识 <span class="required">*</span></label>
        <input v-model="form.name" type="text" class="form-input" placeholder="英文标识，如 geekpark" />
      </div>

      <div class="form-group">
        <label class="form-label">显示名称 <span class="required">*</span></label>
        <input v-model="form.display_name" type="text" class="form-input" placeholder="中文显示名，如 极客公园" />
      </div>

      <div class="form-row">
        <div class="form-group">
          <label class="form-label">栏目</label>
          <select v-model="form.category" class="form-select">
            <option value="ai">{{ categoryLabelMap.ai }}</option>
            <option value="industry">{{ categoryLabelMap.industry }}</option>
            <option value="tech">{{ categoryLabelMap.tech }}</option>
            <option value="media">{{ categoryLabelMap.media }}</option>
          </select>
        </div>

        <div class="form-group" v-if="mode === 'advanced'">
          <label class="form-label">抓取方式</label>
          <select v-model="form.crawl_type" class="form-select">
            <option value="api">API</option>
            <option value="selector">选择器</option>
            <option value="browser">浏览器</option>
          </select>
        </div>

        <div class="form-group">
          <label class="form-label">排序</label>
          <input v-model.number="form.sort_order" type="number" class="form-input" min="0" />
        </div>
      </div>

      <div class="form-group">
        <label class="toggle-switch">
          <input v-model="form.is_active" type="checkbox" />
          <span class="toggle-slider"></span>
          <span class="toggle-label">启用</span>
        </label>
      </div>
    </div>

    <!-- 简单模式：URL 分析 -->
    <div v-if="mode === 'simple'" class="form-section">
      <div class="form-group">
        <label class="form-label">网站地址 <span class="required">*</span></label>
        <div class="url-row">
          <input
            v-model="analyzeUrl"
            type="url"
            class="form-input"
            placeholder="https://example.com/news"
            @keyup.enter="doAnalyze"
          />
          <button
            class="btn btn-primary"
            :disabled="analyzing || !analyzeUrl.trim()"
            @click="doAnalyze"
          >
            <span v-if="analyzing" class="spinner-sm"></span>
            {{ analyzing ? '分析中...' : '分析' }}
          </button>
        </div>
      </div>

      <!-- 分析结果 -->
      <div v-if="analyzeError" class="alert alert-error">{{ analyzeError }}</div>

      <div v-if="analyzeResult" class="analyze-result">
        <div class="result-header">
          <span class="result-badge">{{ crawlTypeLabel(analyzeResult.crawl_type) }}</span>
          <span>检测到 <strong>{{ analyzeResult.preview?.length || 0 }}</strong> 条数据</span>
        </div>

        <!-- 预览表格 -->
        <table v-if="analyzeResult.preview?.length > 0" class="admin-table compact">
          <thead>
            <tr>
              <th style="width:40%">标题</th>
              <th style="width:30%">链接</th>
              <th style="width:20%">时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, i) in analyzeResult.preview" :key="i">
              <td class="ellipsis" :title="item.title">{{ item.title }}</td>
              <td class="ellipsis">
                <a :href="item.link" target="_blank" rel="noopener noreferrer" class="link">{{ item.link }}</a>
              </td>
              <td class="nowrap">{{ item.time_display || '-' }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="empty-text">未检测到可用数据，请尝试高级模式手动配置</p>
      </div>
    </div>

    <!-- 高级模式：JSON 编辑 -->
    <div v-if="mode === 'advanced'" class="form-section">
      <div class="form-section-header">
        <h3>抓取配置</h3>
        <div class="header-actions">
          <button class="btn btn-sm btn-outline" @click="formatJson">格式化 JSON</button>
          <button class="btn btn-sm btn-primary" :disabled="testing" @click="testCurConfig">
            <span v-if="testing" class="spinner-sm"></span>
            {{ testing ? '测试中...' : '测试抓取' }}
          </button>
        </div>
      </div>

      <details class="template-ref">
        <summary>查看 {{ crawlTypeLabel(form.crawl_type) }} 类型配置模板参考</summary>
        <pre class="template-code">{{ configTemplates[form.crawl_type] || '暂无模板' }}</pre>
      </details>

      <textarea
        v-model="form.config_json"
        class="json-editor"
        rows="20"
        placeholder="请输入 JSON 配置..."
      ></textarea>

      <p v-if="jsonError" class="error-text">{{ jsonError }}</p>
    </div>

    <!-- 操作 -->
    <div class="form-actions">
      <button class="btn btn-primary" :disabled="submitting" @click="submitForm">
        {{ submitting ? '提交中...' : (isEdit ? '保存修改' : '创建数据源') }}
      </button>
      <button class="btn btn-default" @click="goBack">取消</button>
    </div>
    <!-- 测试抓取模态框 -->
    <div v-if="showTestModal" class="modal-overlay" @click.self="showTestModal = false">
      <div class="modal test-modal">
        <div class="modal-header">
          <h3>测试抓取结果</h3>
          <button class="btn btn-sm btn-text" @click="showTestModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <div v-if="testing" class="loading">
            <div class="spinner"></div>
            <p>正在抓取...</p>
          </div>
          <div v-else-if="testError" class="error-text">{{ testError }}</div>
          <div v-else>
            <p class="test-count">抓取数量：{{ testResultCount }}</p>
            <table v-if="testPreview.length > 0" class="admin-table compact">
              <thead>
                <tr>
                  <th style="width:40%">标题</th>
                  <th style="width:30%">链接</th>
                  <th style="width:20%">时间</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, i) in testPreview" :key="i">
                  <td class="ellipsis" :title="item.title">{{ item.title }}</td>
                  <td class="ellipsis">
                    <a :href="item.link" target="_blank" rel="noopener noreferrer" class="link">{{ item.link }}</a>
                  </td>
                  <td class="nowrap">{{ fmtTime(item.time) }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="empty-text">未抓取到数据</p>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-default" @click="showTestModal = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchSource, createSource, updateSource, analyzeSource, testConfigCrawl, crawlSingleSource, categoryLabelMap } from '../api/index.js'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)

const form = ref({
  name: '',
  display_name: '',
  category: 'ai',
  crawl_type: 'api',
  is_active: true,
  sort_order: 0,
  config_json: '',
})

const mode = ref('simple')
const submitting = ref(false)
const jsonError = ref('')

// 简单模式分析
const analyzeUrl = ref('')
const analyzing = ref(false)
const analyzeError = ref('')
const analyzeResult = ref(null)

// 高级模式测试
const testing = ref(false)
const showTestModal = ref(false)
const testError = ref('')
const testResultCount = ref(0)
const testPreview = ref([])

function crawlTypeLabel(type) {
  const map = { api: 'API 接口', selector: '选择器', browser: '浏览器' }
  return map[type] || type
}

function fmtTime(val) {
  if (!val) return '-'
  try {
    const d = new Date(val)
    if (isNaN(d.getTime())) return val
    return d.toLocaleString('zh-CN', { hour12: false })
  } catch (e) {
    return val
  }
}

const configTemplates = {
  api: JSON.stringify({
    url: 'https://api.example.com/articles',
    method: 'GET',
    headers: {},
    params: { pageSize: 20 },
    response_type: 'json',
    item_path: 'data.list',
    fetch_content: true,
    mapping: { title: 'title', link: 'url', time: 'publishTime', summary: 'abstract', tags: 'tagList' },
  }, null, 2),
  selector: JSON.stringify({
    url: 'https://example.com/news',
    encoding: 'utf-8',
    list_selector: '.news-list li',
    fetch_content: false,
    content_selector: '.article-body',
    mapping: {
      title: { selector: 'h3 a', attr: 'text' },
      link: { selector: 'h3 a', attr: 'href' },
      time: { selector: 'span.date', attr: 'text' },
    },
  }, null, 2),
  browser: JSON.stringify({
    url: 'https://example.com/news',
    scroll_times: 3,
    wait_selector: '.article-list',
    extract_mode: 'dom',
    fetch_content: false,
    mapping: {
      title: { selector: '.item .title', attr: 'text' },
      link: { selector: '.item a', attr: 'href' },
      time: { selector: '.item .time', attr: 'text' },
    },
  }, null, 2),
}

onMounted(async () => {
  if (isEdit.value) {
    mode.value = 'advanced'
    try {
      const resp = await fetchSource(route.params.id)
      const source = resp.data
      if (source) {
        const configObj = typeof source.config === 'object' ? source.config : {}
        form.value = {
          name: source.name || '',
          display_name: source.display_name || '',
          category: source.category || 'ai',
          crawl_type: source.crawl_type || 'api',
          is_active: source.is_active !== false,
          sort_order: source.sort_order ?? 0,
          config_json: JSON.stringify(configObj, null, 2),
        }
        // 提取 URL 供简单模式使用
        analyzeUrl.value = configObj.url || ''
      }
    } catch (e) { /* 加载失败 */ }
  }
})

function switchMode(target) {
  mode.value = target
  // 切到简单模式时，从 config_json 提取 URL
  if (target === 'simple' && !analyzeUrl.value) {
    try {
      const cfg = JSON.parse(form.value.config_json || '{}')
      analyzeUrl.value = cfg.url || ''
    } catch (e) { /* ignore */ }
  }
}

async function doAnalyze() {
  if (!analyzeUrl.value.trim()) return
  analyzing.value = true
  analyzeError.value = ''
  analyzeResult.value = null

  try {
    const resp = await analyzeSource(analyzeUrl.value.trim())
    const data = resp.data
    analyzeResult.value = data

    if (data.error) {
      analyzeError.value = data.error
    }

    // 自动填充表单
    if (data.crawl_type) {
      form.value.crawl_type = data.crawl_type
    }
    if (data.config) {
      form.value.config_json = JSON.stringify(data.config, null, 2)
    }
  } catch (e) {
    analyzeError.value = e.response?.data?.detail || '分析失败，请检查网络或 URL 是否正确'
  } finally {
    analyzing.value = false
  }
}

function formatJson() {
  try {
    const parsed = JSON.parse(form.value.config_json)
    form.value.config_json = JSON.stringify(parsed, null, 2)
    jsonError.value = ''
  } catch (e) {
    jsonError.value = 'JSON 格式错误：' + e.message
  }
}

async function testCurConfig() {
  // 解析当前 JSON 配置
  let configObj = {}
  try {
    configObj = JSON.parse(form.value.config_json || '{}')
  } catch (e) {
    jsonError.value = 'JSON 格式错误，无法测试'
    return
  }
  jsonError.value = ''

  showTestModal.value = true
  testing.value = true
  testError.value = ''
  testPreview.value = []
  testResultCount.value = 0

  try {
    const resp = await testConfigCrawl(form.value.crawl_type, configObj)
    const result = resp.data || {}
    testResultCount.value = result.count || 0
    testPreview.value = (result.items || []).slice(0, 10)
  } catch (e) {
    testError.value = e.response?.data?.detail || '测试抓取失败'
  } finally {
    testing.value = false
  }
}

async function submitForm() {
  // 简单模式：用分析结果覆盖 config_json
  if (mode.value === 'simple' && analyzeResult.value?.config) {
    form.value.config_json = JSON.stringify(analyzeResult.value.config, null, 2)
    form.value.crawl_type = analyzeResult.value.crawl_type || form.value.crawl_type
  }

  let configObj = {}
  if (form.value.config_json.trim()) {
    try {
      configObj = JSON.parse(form.value.config_json)
      jsonError.value = ''
    } catch (e) {
      jsonError.value = 'JSON 格式错误，请修正后重新提交'
      return
    }
  }

  submitting.value = true
  try {
    const payload = {
      display_name: form.value.display_name,
      category: form.value.category,
      crawl_type: form.value.crawl_type,
      is_active: form.value.is_active,
      sort_order: form.value.sort_order,
      config: configObj,
    }

    if (isEdit.value) {
      await updateSource(route.params.id, payload)
      router.push('/admin/sources')
    } else {
      const resp = await createSource({ ...payload, name: form.value.name })
      const newId = resp.data?.id
      router.push('/admin/sources')
      // 新增后自动触发一次抓取
      if (newId) {
        crawlSingleSource(newId).catch(() => {})
      }
    }
  } catch (e) {
    jsonError.value = e.response?.data?.message || '提交失败，请重试'
  } finally {
    submitting.value = false
  }
}

function goBack() {
  router.push('/admin/sources')
}
</script>

<style scoped>
.source-form-page {
  max-width: 900px;
  margin: 0 auto;
}
.page-title {
  margin: 0 0 20px;
  font-size: 20px;
  font-weight: 600;
}

/* 模式切换 */
.mode-switch {
  display: flex;
  gap: 0;
  margin-bottom: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
  width: fit-content;
}
.mode-btn {
  padding: 8px 24px;
  font-size: 14px;
  border: none;
  background: #fff;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}
.mode-btn:first-child {
  border-right: 1px solid #ddd;
}
.mode-btn.active {
  background: #1a73e8;
  color: #fff;
}

/* 表单 */
.form-section {
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 16px;
}
.form-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.form-section-header h3 {
  margin: 0;
  font-size: 15px;
}
.form-group {
  margin-bottom: 14px;
}
.form-row {
  display: flex;
  gap: 16px;
}
.form-row .form-group {
  flex: 1;
}
.form-label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #333;
}
.required {
  color: #e53e3e;
}
.form-input, .form-select {
  width: 100%;
  padding: 8px 12px;
  font-size: 14px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  background: #fff;
  box-sizing: border-box;
  transition: border-color 0.2s;
}
.form-input:focus, .form-select:focus {
  border-color: #1a73e8;
  outline: none;
}

/* URL 分析 */
.url-row {
  display: flex;
  gap: 10px;
}
.url-row .form-input {
  flex: 1;
}
.alert {
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 13px;
  margin-bottom: 12px;
}
.alert-error {
  background: #fff2f0;
  border: 1px solid #ffccc7;
  color: #cf1322;
}
.analyze-result {
  margin-top: 12px;
}
.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
  font-size: 14px;
}
.result-badge {
  display: inline-block;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 500;
  color: #1a73e8;
  background: #e8f0fe;
  border-radius: 4px;
}

/* 表格 */
.admin-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.admin-table.compact th,
.admin-table.compact td {
  padding: 8px 10px;
  border-bottom: 1px solid #f0f0f0;
  text-align: left;
}
.admin-table th {
  background: #fafafa;
  font-weight: 500;
  color: #666;
}
.ellipsis {
  max-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nowrap {
  white-space: nowrap;
  color: #999;
  font-size: 12px;
}

/* JSON 编辑器 */
.template-ref {
  margin-bottom: 10px;
}
.template-ref summary {
  cursor: pointer;
  font-size: 13px;
  color: #1a73e8;
  user-select: none;
}
.template-code {
  background: #f6f8fa;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  overflow-x: auto;
  margin-top: 6px;
  max-height: 200px;
}
.json-editor {
  width: 100%;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  padding: 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  resize: vertical;
  box-sizing: border-box;
}
.json-editor:focus {
  border-color: #1a73e8;
  outline: none;
}

/* Toggle */
.toggle-switch {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.toggle-switch input {
  display: none;
}
.toggle-slider {
  width: 40px;
  height: 22px;
  background: #ccc;
  border-radius: 11px;
  position: relative;
  transition: background 0.2s;
}
.toggle-slider::after {
  content: '';
  position: absolute;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  top: 2px;
  left: 2px;
  transition: transform 0.2s;
}
.toggle-switch input:checked + .toggle-slider {
  background: #1a73e8;
}
.toggle-switch input:checked + .toggle-slider::after {
  transform: translateX(18px);
}
.toggle-label {
  font-size: 13px;
  color: #333;
}

/* 按钮 */
.form-actions {
  display: flex;
  gap: 10px;
  padding: 20px 0;
}
.btn {
  padding: 8px 20px;
  font-size: 14px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn-primary {
  background: #1a73e8;
  color: #fff;
}
.btn-primary:hover:not(:disabled) {
  background: #1557b0;
}
.btn-default {
  background: #fff;
  color: #333;
  border: 1px solid #d9d9d9;
}
.btn-default:hover {
  border-color: #1a73e8;
  color: #1a73e8;
}
.btn-outline {
  background: #fff;
  color: #1a73e8;
  border: 1px solid #1a73e8;
}
.btn-outline:hover {
  background: #e8f0fe;
}
.btn-sm {
  padding: 4px 12px;
  font-size: 12px;
}
.error-text {
  color: #e53e3e;
  font-size: 13px;
  margin-top: 6px;
}
.empty-text {
  color: #999;
  font-size: 13px;
  padding: 12px;
}
.spinner-sm {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  margin-right: 4px;
  vertical-align: middle;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.link {
  color: #1a73e8;
  text-decoration: none;
}
.link:hover {
  text-decoration: underline;
}
</style>
