<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <div class="brand">
        <div class="logo">🌾</div>
        <h2>AI Agent 智慧农场系统</h2>
        <p class="text-muted">FastAPI + LangChain + LangGraph + 多模态多 Agent</p>
      </div>
      <el-form :model="form" @submit.prevent="onLogin" label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="admin" :prefix-icon="User" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="admin123" show-password
            :prefix-icon="Lock" @keyup.enter="onLogin" />
        </el-form-item>
        <el-button type="primary" style="width:100%" :loading="loading" @click="onLogin">登 录</el-button>
      </el-form>
      <p class="tip text-muted">默认账号 admin / admin123（无需任何 API Key 即可跑通全流程）</p>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { auth } from '../api'

const router = useRouter()
const loading = ref(false)
const form = reactive({ username: 'admin', password: 'admin123' })

async function onLogin() {
  loading.value = true
  try {
    const data = await auth.login(form)
    localStorage.setItem('token', data.token)
    localStorage.setItem('user', JSON.stringify(data.user))
    ElMessage.success('登录成功')
    router.push('/home')
  } catch (e) {
    /* interceptor 已提示 */
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap { height: 100vh; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #1d4b2c 0%, #3a7d44 50%, #6fbf73 100%); }
.login-card { width: 400px; border-radius: 12px; }
.brand { text-align: center; margin-bottom: 20px; }
.logo { font-size: 48px; }
.brand h2 { margin: 8px 0 4px; }
.tip { text-align: center; font-size: 12px; margin-top: 16px; }
</style>
