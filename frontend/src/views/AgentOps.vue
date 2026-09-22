<template>
  <div class="page">
    <el-row :gutter="16">
      <el-col :span="10">
        <el-card header="动态路由表（按任务类型编排）">
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="编排引擎">
              <el-tag :type="engineType">{{ engine.engine }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="LLM 模式">
              <el-tag :type="engine.llm === 'langchain' ? 'success' : 'warning'">{{ engine.llm }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
          <el-table :data="routeRows" size="small" class="mt-16">
            <el-table-column prop="type" label="任务" width="90" />
            <el-table-column label="节点链路">
              <template #default="{ row }">
                <el-tag v-for="(n, i) in row.nodes" :key="i" size="small"
                  :type="n === 'human' ? 'danger' : 'info'" style="margin:2px">
                  {{ n }}<span v-if="i < row.nodes.length - 1"> →</span>
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card header="发起任务链" class="mt-16">
          <el-form label-width="80px">
            <el-form-item label="任务类型">
              <el-select v-model="form.task_type" style="width:100%">
                <el-option v-for="t in taskTypes" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
            <el-form-item label="地块">
              <el-select v-model="form.field_id" placeholder="可选" clearable style="width:100%">
                <el-option v-for="f in fields" :key="f.id" :label="f.name" :value="f.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="补充说明">
              <el-input v-model="form.user_input" type="textarea" :rows="2" placeholder="例如：叶片有褐斑" />
            </el-form-item>
            <el-button type="primary" :loading="running" @click="run">执行</el-button>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="14">
        <el-card header="执行结果 / 节点复盘">
          <el-empty v-if="!result.request_id" description="选择任务类型后点击执行" />
          <div v-else>
            <el-alert :title="`request_id: ${result.request_id} 状态: ${result.status}`"
              :type="result.need_confirm ? 'warning' : 'success'" :closable="false" show-icon />
            <el-tabs class="mt-16">
              <el-tab-pane label="节点轨迹">
                <el-steps direction="vertical" :active="result.trace?.length || 0" finish-status="success">
                  <el-step v-for="(t, i) in result.trace" :key="i" :title="t.node"
                    :description="JSON.stringify(t)" />
                </el-steps>
              </el-tab-pane>
              <el-tab-pane label="感知">
                <pre class="json">{{ fmt(result.perception) }}</pre>
              </el-tab-pane>
              <el-tab-pane label="诊断/长势">
                <pre class="json">{{ fmt({ diagnosis: result.diagnosis, growth: result.growth }) }}</pre>
              </el-tab-pane>
              <el-tab-pane label="规划/控制">
                <pre class="json">{{ fmt({ plan: result.plan, control: result.control }) }}</pre>
              </el-tab-pane>
              <el-tab-pane label="预警/问答">
                <pre class="json">{{ fmt({ alert: result.alert, answer: result.answer }) }}</pre>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-card>

        <el-card header="节点级审计日志" class="mt-16">
          <el-input v-model="logFilter" placeholder="按 request_id 过滤" clearable size="small"
            style="width:280px;margin-bottom:8px" @change="loadLogs" />
          <el-table :data="logs" size="small" max-height="300">
            <el-table-column prop="request_id" label="request_id" width="140" show-overflow-tooltip />
            <el-table-column prop="node" label="节点" width="110" />
            <el-table-column prop="phase" label="阶段" width="70" />
            <el-table-column prop="cost_ms" label="耗时(ms)" width="90" />
            <el-table-column prop="status" label="状态" width="70" />
            <el-table-column label="时间">
              <template #default="{ row }">{{ row.ts?.slice(11,19) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { agent, fieldApi } from '../api'

const engine = ref({})
const fields = ref([])
const logs = ref([])
const logFilter = ref('')
const result = ref({})
const running = ref(false)
const taskTypes = ['diagnose', 'growth', 'plan', 'control', 'alert', 'chat', 'full']
const form = ref({ task_type: 'full', field_id: null, user_input: '' })

const engineType = computed(() => (engine.value.engine || '').includes('langgraph') && !(engine.value.engine||'').includes('降级') ? 'success' : 'info')
const routeRows = computed(() => Object.entries(engine.value.routes || {}).map(([type, nodes]) => ({ type, nodes })))

function fmt(o) { return JSON.stringify(o || {}, null, 2) }

async function run() {
  running.value = true
  try {
    result.value = await agent.run(form.value)
    if (result.value.need_confirm) ElMessage.warning('检测到高风险，已挂起等待人工确认（前往病虫害诊断页处理）')
    else ElMessage.success('执行完成')
    loadLogs()
  } finally { running.value = false }
}

async function loadLogs() {
  const params = { page: 1, size: 30 }
  if (logFilter.value) params.request_id = logFilter.value
  const data = await agent.logs(params)
  logs.value = data.items
}

onMounted(async () => {
  engine.value = await agent.engine()
  fields.value = await fieldApi.list()
  loadLogs()
})
</script>

<style scoped>
.json { background: #f6f8fa; padding: 12px; border-radius: 6px; overflow: auto; max-height: 400px; font-size: 12px; }
</style>
