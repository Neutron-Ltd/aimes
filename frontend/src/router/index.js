import { createRouter, createWebHistory } from 'vue-router'
import IndexPage from '../views/Index.vue'

const assistantRoutes = [
  {
    path: '/assistant/production',
    name: 'assistant-production',
    component: () => import('../views/assistants/production/index.vue'),
    meta: { title: 'AI生产助手' }
  },
  {
    path: '/assistant/warehouse',
    name: 'assistant-warehouse',
    component: () => import('../views/assistants/warehouse/index.vue'),
    meta: { title: 'AI仓库助手' }
  },
  {
    path: '/assistant/quality',
    name: 'assistant-quality',
    component: () => import('../views/assistants/quality/index.vue'),
    meta: { title: 'AI质量助手' }
  },
  {
    path: '/assistant/equipment',
    name: 'assistant-equipment',
    component: () => import('../views/assistants/equipment/index.vue'),
    meta: { title: 'AI设备助手' }
  },
  {
    path: '/assistant/procurement',
    name: 'assistant-procurement',
    component: () => import('../views/assistants/procurement/index.vue'),
    meta: { title: 'AI采购助手' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: IndexPage,
      meta: { title: '首页' }
    },
    ...assistantRoutes,
    {
      path: '/assistant/:type',
      redirect: (to) => {
        const legacyMap = {
          production: '/assistant/production',
          warehouse: '/assistant/warehouse',
          quality: '/assistant/quality',
          equipment: '/assistant/equipment',
          procurement: '/assistant/procurement'
        }
        return legacyMap[to.params.type] || '/'
      }
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ],
  scrollBehavior() {
    return { top: 0 }
  }
})

export default router
