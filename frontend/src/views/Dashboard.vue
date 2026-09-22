<template>
  <div class="page dashboard">
    <div class="card-grid">
      <el-card v-for="s in coreStats" :key="s.label" class="stat-card" shadow="hover">
        <div class="stat-value" :style="{ color: s.color }">{{ s.value }}</div>
        <div class="stat-label">{{ s.label }}</div>
      </el-card>
    </div>

    <el-row :gutter="16" class="mt-16">
      <el-col :span="16">
        <el-card header="传感器实时曲线">
          <div ref="curveEl" style="height:300px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card header="预警看板" class="fixed-h">
          <el-empty v-if="!data.alerts?.length" description="暂无未关闭预警" :image-size="50" />
          <div v-for="a in (data.alerts || []).slice(0,8)" :key="a.id" class="alert-row">
            <el-tag size="small" :type="a.level === '紧急' ? 'danger' : (a.level === '重要' ? 'warning' : 'info')">{{ a.level }}</el-tag>
            <span class="alert-title">{{ a.title }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="mt-16">
      <el-col :span="8">
        <el-card header="Agent 指令流" class="fixed-h">
          <el-table :data="(data.commands || []).slice(0,8)" size="small">
            <el-table-column prop="action" label="动作" width="80" />
            <el-table-column prop="source" label="来源" width="70" />
            <el-table-column label="结果" width="70">
              <template #default="{ row }"><el-tag size="small" :type="row.passed ? 'success' : 'danger'">{{ row.passed ? '执行' : '拦截' }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="blocked_reason" label="说明" show-overflow-tooltip />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card header="病虫害分布" class="fixed-h">
          <div v-for="p in (data.pest_map || [])" :key="p.field_id" class="pest-row">
            <span>地块 #{{ p.field_id }}</span>
            <el-tag size="small" type="danger">{{ p.count }} 例</el-tag>
          </div>
          <el-empty v-if="!data.pest_map?.length" description="暂无诊断记录" :image-size="50" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card header="引擎 / LLM 健康" class="fixed-h">
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="编排引擎">
              <el-tag size="small" :type="engineType">{{ data.engine?.engine }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="LLM 模式">
              <el-tag size="small" :type="data.engine?.llm === 'langchain' ? 'success' : 'warning'">{{ data.engine?.llm }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="路由数">{{ Object.keys(data.engine?.routes || {}).length }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <el-card header="影像墙" class="mt-16">
      <div class="media-wall">
        <el-image v-for="m in (data.media_wall || [])" :key="m.id" :src="m.path" fit="cover" class="wall-thumb" />
        <el-empty v-if="!data.media_wall?.length" description="暂无影像" :image-size="50" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { dashboard } from '../api'

const data = ref({})
const curveEl = ref(null)
let chart = null, timer = null

const engineType = computed(() => (data.value.engine?.engine || '').includes('langgraph') && !(data.value.engine?.engine||'').includes('降级') ? 'success' : 'info')
const coreStats = computed(() => {
  const c = data.value.core || {}
  return [
    { label: '地块', value: c.field_count ?? '-', color: '#409eff' },
    { label: '总面积(亩)', value: c.total_area ?? '-', color: '#67c23a' },
    { label: '设备在线', value: `${c.device_online ?? 0}/${c.device_count ?? 0}`, color: '#409eff' },
    { label: '未关闭预警', value: c.alert_open ?? '-', color: '#e6a23c' },
    { label: '紧急预警', value: c.alert_urgent ?? '-', color: '#f56c6c' },
    { label: '诊断记录', value: c.diagnosis_count ?? '-', color: '#909399' },
  ]
})

function drawCurves(curves = []) {
  nextTick(() => {
    if (!curveEl.value) return
    if (!chart) chart = echarts.init(curveEl.value)
    const picked = curves.filter(c => c.points?.length).slice(0, 4)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: picked.map(p => p.sensor) },
      xAxis: { type: 'category', data: (picked[0]?.points || []).map(p => (p.ts || '').slice(11,19)) },
      yAxis: { type: 'value' },
      series: picked.map(p => ({ name: p.sensor, type: 'line', smooth: true, data: p.points.map(x => x.value) })),
    }, true)
  })
}

async function load() {
  data.value = await dashboard.overview()
  drawCurves(data.value.curves)
}

onMounted(() => { load(); timer = setInterval(load, 20000); window.addEventListener('resize', () => chart && chart.resize()) })
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.fixed-h { height: 300px; overflow-y: auto; }
.alert-row { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px dashed #eee; }
.alert-title { font-size: 13px; }
.pest-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px dashed #eee; }
.media-wall { display: flex; gap: 10px; flex-wrap: wrap; }
.wall-thumb { width: 140px; height: 90px; border-radius: 6px; }
</style>
