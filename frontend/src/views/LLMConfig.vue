<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="flex-between">
          <span>大模型配置（后台启用任意 OpenAI 兼容模型即可热切换；不配 Key 也能离线跑通全流程）</span>
          <el-button type="primary" :icon="Plus" @click="openCreate">新增配置</el-button>
        </div>
      </template>

      <el-alert type="info" :closable="false" show-icon class="mb-16"
        title="启用「本地规则内核」= 离线兜底模式（断网/无 Key 可用）；启用任一云端配置 = 真实大模型 + 向量检索。切换即时生效。" />

      <el-table :data="rows" v-loading="loading" size="small" border>
        <el-table-column prop="id" label="ID" width="55" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="provider" label="提供方" width="100" />
        <el-table-column prop="model" label="模型" width="160" />
        <el-table-column prop="base_url" label="Base URL" show-overflow-tooltip />
        <el-table-column label="API Key" width="110">
          <template #default="{ row }">{{ row.api_key ? '******' : '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }"><el-tag size="small" :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '使用中' : '未启用' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <el-button v-if="!row.is_active" link type="success" size="small" @click="activate(row)">启用</el-button>
            <el-button link type="primary" size="small" @click="test(row)" :loading="testingId === row.id">测试</el-button>
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialog" :title="editing.id ? '编辑配置' : '新增配置'" width="520px">
      <el-form :model="editing" label-width="110px">
        <el-form-item label="名称"><el-input v-model="editing.name" /></el-form-item>
        <el-form-item label="提供方">
          <el-select v-model="editing.provider" style="width:100%">
            <el-option v-for="p in providers" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="Base URL"><el-input v-model="editing.base_url" placeholder="https://api.openai.com/v1" /></el-form-item>
        <el-form-item label="API Key"><el-input v-model="editing.api_key" type="password" show-password /></el-form-item>
        <el-form-item label="对话模型"><el-input v-model="editing.model" placeholder="gpt-4o-mini" /></el-form-item>
        <el-form-item label="Embedding"><el-input v-model="editing.embedding_model" placeholder="text-embedding-3-small" /></el-form-item>
        <el-form-item label="Temperature"><el-input-number v-model="editing.temperature" :min="0" :max="2" :step="0.1" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="save" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { llmConfig } from '../api'

const rows = ref([]); const loading = ref(false); const dialog = ref(false)
const editing = ref({}); const saving = ref(false); const testingId = ref(null)
const providers = [
  { value: 'local', label: '本地规则内核(离线)' }, { value: 'openai', label: 'OpenAI' },
  { value: 'deepseek', label: 'DeepSeek' }, { value: 'dashscope', label: '通义千问' },
  { value: 'zhipu', label: '智谱 GLM' }, { value: 'moonshot', label: 'Moonshot' },
  { value: 'ollama', label: 'Ollama' },
]

async function load() { loading.value = true; try { rows.value = await llmConfig.list() } finally { loading.value = false } }
function openCreate() { editing.value = { provider: 'openai', temperature: 0.2 }; dialog.value = true }
function openEdit(row) { editing.value = { ...row }; dialog.value = true }
async function save() {
  saving.value = true
  try {
    if (editing.value.id) await llmConfig.update(editing.value.id, editing.value)
    else await llmConfig.create(editing.value)
    ElMessage.success('已保存'); dialog.value = false; load()
  } finally { saving.value = false }
}
async function activate(row) { await llmConfig.activate(row.id); ElMessage.success(`已切换到 ${row.name}（即时生效）`); load() }
async function test(row) {
  testingId.value = row.id
  try { const r = await llmConfig.test(row.id); r.ok ? ElMessage.success(r.msg || '连通正常') : ElMessage.warning('连通失败') }
  catch (e) { /* interceptor */ } finally { testingId.value = null }
}
async function remove(row) {
  await ElMessageBox.confirm('确认删除该配置？', '提示', { type: 'warning' })
  await llmConfig.remove(row.id); ElMessage.success('已删除'); load()
}
onMounted(load)
</script>

<style scoped>.mb-16 { margin-bottom: 16px; }</style>
