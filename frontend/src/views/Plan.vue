<template>
  <div class="page">
    <el-row :gutter="16">
      <el-col :span="8">
        <el-card header="发起农事规划（感知→规划→控制）">
          <el-form label-width="60px">
            <el-form-item label="地块">
              <el-select v-model="fieldId" placeholder="可选" clearable style="width:100%">
                <el-option v-for="f in fields" :key="f.id" :label="f.name" :value="f.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="诉求">
              <el-input v-model="userInput" type="textarea" :rows="2" placeholder="例如：以节水为目标安排本周农事" />
            </el-form-item>
            <el-button type="primary" :loading="running" @click="run">生成规划</el-button>
          </el-form>
          <el-card v-if="reasoning" shadow="never" class="mt-16">
            <div class="markdown-body" v-html="render(reasoning)"></div>
          </el-card>
          <div v-if="commands.length" class="mt-16">
            <div class="text-muted">🔧 设备指令（安全护栏）</div>
            <el-table :data="commands" size="small">
              <el-table-column prop="device" label="设备" />
              <el-table-column prop="action" label="动作" width="80" />
              <el-table-column label="结果" width="80">
                <template #default="{ row }"><el-tag size="small" :type="row.ok ? 'success' : 'danger'">{{ row.ok ? '执行' : '拦截' }}</el-tag></template>
              </el-table-column>
              <el-table-column prop="reason" label="说明" show-overflow-tooltip />
            </el-table>
          </div>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card header="农事计划列表">
          <el-table :data="tasks" size="small" border>
            <el-table-column prop="id" label="ID" width="55" />
            <el-table-column prop="title" label="任务" />
            <el-table-column prop="type" label="类型" width="90" />
            <el-table-column prop="objective" label="目标" width="80" />
            <el-table-column prop="priority" label="优先级" width="80">
              <template #default="{ row }"><el-tag size="small" :type="prioType(row.priority)">{{ row.priority }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }">
                <el-select :model-value="row.status" size="small" @change="(v) => setStatus(row, v)">
                  <el-option label="待办" value="pending" /><el-option label="进行" value="running" />
                  <el-option label="完成" value="done" /><el-option label="取消" value="cancelled" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column prop="plan_start" label="计划时间" width="150" type="time" />
          </el-table>
          <el-pagination class="mt-16" layout="total, prev, pager, next" :total="total"
            :page-size="size" :current-page="page" @current-change="onPage" background small />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { marked } from 'marked'
import { ElMessage } from 'element-plus'
import { task, fieldApi } from '../api'

const fields = ref([]); const fieldId = ref(null); const userInput = ref('')
const tasks = ref([]); const total = ref(0); const page = ref(1); const size = ref(20)
const running = ref(false); const reasoning = ref(''); const commands = ref([])

function render(t) { return marked.parse(t || '') }
function prioType(p) { return p === 'high' ? 'danger' : (p === 'low' ? 'info' : 'warning') }

async function run() {
  running.value = true
  try {
    const res = await task.run({ field_id: fieldId.value, user_input: userInput.value })
    reasoning.value = res.plan?.reasoning || ''
    commands.value = res.control?.commands || []
    ElMessage.success(`已生成 ${res.plan?.tasks?.length || 0} 条农事计划`)
    load()
  } finally { running.value = false }
}

async function load() {
  const data = await task.page(page.value, size.value)
  tasks.value = data.items; total.value = data.total
}
function onPage(p) { page.value = p; load() }
async function setStatus(row, status) {
  await task.setStatus(row.id, status); row.status = status; ElMessage.success('状态已更新')
}

onMounted(async () => { fields.value = await fieldApi.list(); load() })
</script>
