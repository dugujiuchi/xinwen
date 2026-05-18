<template>
  <div class="admin-container">
    <!-- 密码验证弹窗 -->
    <div v-if="showPasswordModal" class="modal-overlay">
      <div class="password-modal">
        <h3>管理端验证</h3>
        <p class="password-hint">请输入管理密码以继续</p>
        <input
          ref="pwdInput"
          v-model="passwordInput"
          type="password"
          class="form-input"
          placeholder="请输入管理密码"
          @keyup.enter="verifyPassword"
        />
        <p v-if="passwordError" class="error-text">{{ passwordError }}</p>
        <button class="btn btn-primary" :disabled="verifying" @click="verifyPassword">
          {{ verifying ? '验证中...' : '确认' }}
        </button>
      </div>
    </div>

    <!-- 管理端主体 -->
    <div class="admin-layout">
      <!-- 顶部栏 -->
      <header class="admin-header">
        <router-link to="/" class="back-link">← 返回新闻页</router-link>
        <h2 class="admin-header-title">管理端</h2>
        <button class="btn btn-text" @click="logout">退出登录</button>
      </header>

      <div class="admin-body">
        <!-- 左侧导航 -->
        <aside class="admin-sidebar">
          <nav class="admin-nav">
            <router-link
              to="/admin/sources"
              class="admin-nav-item"
              active-class="admin-nav-item--active"
            >
              数据源管理
            </router-link>
            <router-link
              to="/admin/crawl-logs"
              class="admin-nav-item"
              active-class="admin-nav-item--active"
            >
              爬取日志
            </router-link>
          </nav>
        </aside>

        <!-- 右侧内容区 -->
        <main class="admin-content">
          <router-view />
        </main>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { verifyAdminPassword } from '../api/index.js'

const router = useRouter()

const showPasswordModal = ref(false)
const passwordInput = ref('')
const passwordError = ref('')
const verifying = ref(false)
const pwdInput = ref(null)

function showPwdModal() {
  showPasswordModal.value = true
  passwordInput.value = ''
  passwordError.value = ''
  nextTick(() => pwdInput.value?.focus())
}

onMounted(() => {
  const savedPwd = localStorage.getItem('admin_password')
  if (!savedPwd) {
    showPwdModal()
  }
  // 监听 403 响应触发的密码过期事件
  window.addEventListener('admin-auth-expired', showPwdModal)
})

onUnmounted(() => {
  window.removeEventListener('admin-auth-expired', showPwdModal)
})

async function verifyPassword() {
  const pwd = passwordInput.value.trim()
  if (!pwd) {
    passwordError.value = '请输入密码'
    return
  }

  verifying.value = true
  passwordError.value = ''
  try {
    await verifyAdminPassword(pwd)
    localStorage.setItem('admin_password', pwd)
    showPasswordModal.value = false
  } catch (e) {
    passwordError.value = '密码错误，请重新输入'
  } finally {
    verifying.value = false
  }
}

function logout() {
  localStorage.removeItem('admin_password')
  router.push('/')
}
</script>

<style scoped>
.admin-header {
  display: flex;
  align-items: center;
  gap: 16px;
}
.admin-header-title {
  flex: 1;
}
.back-link {
  color: #1a73e8;
  text-decoration: none;
  font-size: 14px;
}
.back-link:hover {
  text-decoration: underline;
}
</style>
