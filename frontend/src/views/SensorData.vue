<template>
  <div class="page">
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card header="传感器列表">
          <el-input v-model="filter" placeholder="搜索指标" size="small" clearable class="mb-8" />
          <div class="sensor-list">
            <div v-for="s in filteredSensors" :key="s.id"
              :class="['sensor-item', { active: s.id === current?.id }]" @click="select(s)">
              <div class="s-name">{{ s.name }}</div>
              <div class="text-muted" style="font-size:12px">{{ s.metric }} · {{ s.online ? '在线' : '离线' }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="18">
        <el-card v-if="current">
          <template #header>
            <div class="flex-between">
              <span>{{ current.name }} — 时序曲线</span>
              <div>
                <el-button size="small" @click="simulate" :loading="simulating">生成模拟数据</el-button>
                <el-tag size="small" type="info">均值 {{ stat.avg }}</el-tag>
                <el-tag size="small" type="warning" style="margin-left:6px">极值 {{ stat.min }}~{{ stat.max }}</el-tag>
                <el-tag size="small" :type="stat.trend === 'up' ? 'danger' : (stat.trend === 'down' ? 'success' : 'info')" style="margin-left:6px">
                  趋势 {{ trendName(stat.trend) }}
                </el-tag>
              </div>
            </div>
          </template>
          <div ref="chartEl" style="height:380px"></div>
        </el-card>
        <el-card v-else><el-empty description="请选择左侧传感器" /></el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { sensor } from '../api'

const sensors = ref([]); const current = ref(null); const filter = ref('')
const stat = ref({}); const simulating = ref(false)
const chartEl = ref(null); let chart = null

const filteredSensors = computed(() => sensors.value.filter(s => !filter.value || s.metric.includes(filter.value) || s.name.includes(filter.value)))
function trendName(t) { return t === 'up' ? '上升' : (t === 'down' ? '下降' : '平稳') }

async function select(s) {
  current.value = s
  const [data, st] = await Promise.all([sensor.data(s.id, 100), sensor.stat(s.id, 20)])
  stat.value = st
  drawChart(data, s)
}
function drawChart(data, s) {
  nextTick(() => {
    if (!chartEl.value) return
    if (!chart) chart = echarts.init(chartEl.value)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: data.map(d => (d.ts || '').slice(11,19)) },
      yAxis: { type: 'value', name: s.unit || s.metric },
      series: [{
        type: 'line', smooth: true, data: data.map(d => d.value), areaStyle: { opacity: 0.15 },
        markPoint: { data: [{ type: 'max', name: '最大' }, { type: 'min', name: '最小' }] },
      }],
    }, true)
  })
}
async function simulate() {
  simulating.value = true
  try { await sensor.simulate(current.value.id, 10); ElMessage.success('已生成模拟数据'); select(current.value) }
  finally { simulating.value = false }
}

onMounted(async () => {
  sensors.value = await sensor.list()
  if (sensors.value.length) select(sensors.value[0])
  window.addEventListener('resize', () => chart && chart.resize())
})
</script>

<style scoped>
.sensor-list { max-height: calc(100vh - 240px); overflow-y: auto; }
.sensor-item { padding: 8px 10px; border-radius: 6px; cursor: pointer; border: 1px solid transparent; }
.sensor-item:hover { background: #f5f7fa; }
.sensor-item.active { background: #ecf5ff; border-color: #b3d8ff; }
.s-name { font-size: 13px; }
.mb-8 { margin-bottom: 8px; }
</style>
