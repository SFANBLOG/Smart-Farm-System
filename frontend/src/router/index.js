import { createRouter, createWebHashHistory } from 'vue-router'
import AdminLayout from '../layout/AdminLayout.vue'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: AdminLayout,
    redirect: '/home',
    children: [
      { path: 'home', name: 'home', component: () => import('../views/Home.vue'), meta: { title: '首页', icon: 'HomeFilled' } },
      { path: 'dashboard', name: 'dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '总览大屏', icon: 'DataBoard' } },
      { path: 'chat', name: 'chat', component: () => import('../views/Chat.vue'), meta: { title: 'AI 问答助手', icon: 'ChatDotRound' } },
      { path: 'agent-ops', name: 'agent-ops', component: () => import('../views/AgentOps.vue'), meta: { title: 'Agent 编排', icon: 'Share' } },
      { path: 'diagnosis', name: 'diagnosis', component: () => import('../views/Diagnosis.vue'), meta: { title: '病虫害诊断', icon: 'FirstAidKit' } },
      { path: 'growth', name: 'growth', component: () => import('../views/Growth.vue'), meta: { title: '作物长势', icon: 'Sunny' } },
      { path: 'plan', name: 'plan', component: () => import('../views/Plan.vue'), meta: { title: '农事规划', icon: 'Calendar' } },
      { path: 'alert', name: 'alert', component: () => import('../views/Alert.vue'), meta: { title: '预警研判', icon: 'WarnTriangleFilled' } },
      { path: 'knowledge', name: 'knowledge', component: () => import('../views/Knowledge.vue'), meta: { title: '农业知识库', icon: 'Reading' } },
      { path: 'media', name: 'media', component: () => import('../views/Media.vue'), meta: { title: '影像管理', icon: 'Picture' } },
      { path: 'sensor-data', name: 'sensor-data', component: () => import('../views/SensorData.vue'), meta: { title: '传感器数据', icon: 'Odometer' } },
      { path: 'device', name: 'device', component: () => import('../views/Device.vue'), meta: { title: '设备管理', icon: 'Cpu' } },
      { path: 'field', name: 'field', component: () => import('../views/Field.vue'), meta: { title: '地块管理', icon: 'MapLocation' } },
      { path: 'crop', name: 'crop', component: () => import('../views/Crop.vue'), meta: { title: '作物管理', icon: 'Cherry' } },
      { path: 'weather', name: 'weather', component: () => import('../views/Weather.vue'), meta: { title: '气象预报', icon: 'Cloudy' } },
      { path: 'report', name: 'report', component: () => import('../views/Report.vue'), meta: { title: 'AI 分析报表', icon: 'Document' } },
      { path: 'llm-config', name: 'llm-config', component: () => import('../views/LLMConfig.vue'), meta: { title: '大模型配置', icon: 'Setting' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/home' },
]

const router = createRouter({ history: createWebHashHistory(), routes })

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (!to.meta.public && !token) return { path: '/login' }
  if (to.path === '/login' && token) return { path: '/home' }
  return true
})

export const menuRoutes = routes[1].children
export default router
