<template>
  <div class="page">
    <el-row :gutter="16">
      <el-col :span="24">
        <el-card>
          <div class="welcome">
            <div>
              <h2 style="margin:0">👋 欢迎回来，{{ user.real_name || user.username }}</h2>
              <p class="text-muted" style="margin:8px 0 0">
                一套能跑通"感知 → 诊断 → 人工确认 → 规划 → 控制 → 预警"完整闭环的多 Agent 智慧农场系统。
              </p>
            </div>
            <div class="modes">
              <el-tag :type="engineType">编排引擎：{{ engine.engine || '-' }}</el-tag>
              <el-tag :type="llmType" style="margin-left:8px">LLM：{{ engine.llm || '-' }}</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <div class="card-grid mt-16">
      <el-card v-for="s in stats" :key="s.label" class="stat-card" shadow="hover">
        <div class="stat-value">{{ s.value }}</div>
        <div class="stat-label">{{ s.label }}</div>
      </el-card>
    </div>

    <el-row :gutter="16" class="mt-16">
      <el-col :span="14">
        <el-card header="快捷入口">
          <div class="quick">
            <el-button v-for="q in quickLinks" :key="q.path" :icon="q.icon" @click="$router.push(q.path)">
              {{ q.title }}
            </el-button>
          </div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card header="未关闭预警">
          <el-empty v-if="!alerts.length" description="暂无预警" :image-size="60" />
          <el-timeline v-else>
            <el-timeline-item v-for="a in alerts.slice(0,5)" :key="a.id"
              :type="a.level === '紧急' ? 'danger' : (a.level === '重要' ? 'warning' : 'info')"
              :timestamp="a.created_at?.slice(0,16).replace('T',' ')">
              [{{ a.level }}] {{ a.title }}
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { dashboard, agent } from '../api'

const user = ref(JSON.parse(localStorage.getItem('user') || '{}'))
const stats = ref([])
const alerts = ref([])
const engine = ref({})

const engineType = computed(() => (engine.value.engine || '').includes('langgraph') && !(engine.value.engine||'').includes('降级') ? 'success' : 'info')
const llmType = computed(() => engine.value.llm === 'langchain' ? 'success' : 'warning')

const quickLinks = [
  { path: '/chat', title: 'AI 问答', icon: 'ChatDotRound' },
  { path: '/diagnosis', title: '病虫害诊断', icon: 'FirstAidKit' },
  { path: '/agent-ops', title: 'Agent 编排', icon: 'Share' },
  { path: '/dashboard', title: '总览大屏', icon: 'DataBoard' },
  { path: '/alert', title: '预警研判', icon: 'WarnTriangleFilled' },
  { path: '/report', title: 'AI 报表', icon: 'Document' },
]

onMounted(async () => {
  try {
    const [ov, eng] = await Promise.all([dashboard.overview(), agent.engine()])
    engine.value = eng
    const c = ov.core
    stats.value = [
      { label: '地块数量', value: c.field_count },
      { label: '总面积(亩)', value: c.total_area },
      { label: '设备在线', value: `${c.device_online}/${c.device_count}` },
      { label: '未关闭预警', value: c.alert_open },
      { label: '紧急预警', value: c.alert_urgent },
      { label: '诊断记录', value: c.diagnosis_count },
    ]
    alerts.value = ov.alerts || []
  } catch (e) { /* ignore */ }
})
</script>

<style scoped>
.welcome { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
.quick { display: flex; flex-wrap: wrap; gap: 12px; }
</style>
