import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import AdminLayout from '../views/AdminLayout.vue'
import SourceList from '../views/SourceList.vue'
import SourceForm from '../views/SourceForm.vue'
import CrawlLogs from '../views/CrawlLogs.vue'

const routes = [
  { path: '/', name: 'home', component: Home },
  {
    path: '/admin',
    component: AdminLayout,
    children: [
      { path: '', redirect: '/admin/sources' },
      { path: 'sources', name: 'source-list', component: SourceList },
      { path: 'sources/new', name: 'source-create', component: SourceForm },
      { path: 'sources/:id/edit', name: 'source-edit', component: SourceForm },
      { path: 'crawl-logs', name: 'crawl-logs', component: CrawlLogs },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
