<template>
  <el-container class="layout">
    <el-aside :width="collapsed ? '64px' : '220px'" class="aside">
      <div class="logo">
        <span v-if="!collapsed">🌾 智慧农场</span>
        <span v-else>🌾</span>
      </div>
      <el-menu :default-active="$route.path" :collapse="collapsed" router background-color="#001529"
        text-color="#b7c0cd" active-text-color="#fff" class="menu">
        <el-menu-item v-for="m in menuRoutes" :key="m.path" :index="'/' + m.path">
          <el-icon><component :is="m.meta.icon" /></el-icon>
          <template #title>{{ m.meta.title }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="left">
          <el-icon class="collapse-btn" @click="collapsed = !collapsed">
            <Fold v-if="!collapsed" /><Expand v-else />
          </el-icon>
          <span class="title">{{ $route.meta.title || 'AI Agent 智慧农场系统' }}</span>
        </div>
        <div class="right">
          <el-tag :type="engineType" class="mode-tag" size="small">
            引擎: {{ engine.engine || '...' }}
          </el-tag>
          <el-tag :type="llmType" size="small" style="margin-left:8px">
            LLM: {{ engine.llm || '...' }}
          </el-tag>
          <el-dropdown @command="onCommand" style="margin-left:12px">
            <span class="user">
              <el-icon><UserFilled /></el-icon> {{ user.real_name || user.username || 'admin' }}
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main">
        <router-view v-slot="{ Component }">
          <keep-alive :max="6"><component :is="Component" /></keep-alive>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { menuRoutes } from '../router'
import { agent } from '../api'

const router = useRouter()
const collapsed = ref(false)
const engine = ref({})
const user = ref(JSON.parse(localStorage.getItem('user') || '{}'))
let timer = null

const engineType = computed(() =>
  (engine.value.engine || '').includes('langgraph') && !(engine.value.engine || '').includes('降级')
    ? 'success' : 'info')
const llmType = computed(() => engine.value.llm === 'langchain' ? 'success' : 'warning')

async function loadEngine() {
  try { engine.value = await agent.engine() } catch (e) { /* ignore */ }
}
function onCommand(c) {
  if (c === 'logout') {
    localStorage.removeItem('token'); localStorage.removeItem('user')
    router.push('/login')
  }
}
onMounted(() => { loadEngine(); timer = setInterval(loadEngine, 15000) })
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.layout { height: 100vh; }
.aside { background: #001529; transition: width .2s; overflow-x: hidden; }
.logo { height: 60px; line-height: 60px; text-align: center; color: #fff; font-weight: 700; font-size: 16px; white-space: nowrap; }
.menu { border-right: none; }
.header { background: #fff; border-bottom: 1px solid #eee; display: flex; align-items: center; justify-content: space-between; }
.header .left { display: flex; align-items: center; gap: 12px; }
.header .title { font-size: 16px; font-weight: 600; }
.collapse-btn { cursor: pointer; font-size: 20px; }
.header .right { display: flex; align-items: center; }
.user { cursor: pointer; display: flex; align-items: center; gap: 4px; }
.main { background: #f0f2f5; padding: 0; overflow-y: auto; }
</style>
