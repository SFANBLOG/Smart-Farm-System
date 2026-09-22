<template>
  <div class="page">
    <el-row :gutter="16">
      <el-col :span="8">
        <el-card header="发起长势诊断（感知→长势→规划）">
          <el-form label-width="60px">
            <el-form-item label="地块">
              <el-select v-model="fieldId" placeholder="可选" clearable style="width:100%" @change="loadHistory">
                <el-option v-for="f in fields" :key="f.id" :label="f.name" :value="f.id" />
              </el-select>
            </el-form-item>
            <el-button type="primary" :loading="running" @click="run">开始诊断</el-button>
          </el-form>

          <div v-if="growth.score !== undefined" class="mt-16">
            <el-progress type="dashboard" :percentage="growth.score" :color="scoreColor" />
            <el-descriptions :column="1" border size="small" class="mt-16">
              <el-descriptions-item label="生育期">{{ growth.stage }}</el-descriptions-item>
              <el-descriptions-item label="绿度指数">{{ growth.green_index }}</el-descriptions-item>
              <el-descriptions-item label="缺素判断">{{ growth.nutrient_issue || '无明显缺素' }}</el-descriptions-item>
              <el-descriptions-item label="距采收(天)">{{ growth.days_to_harvest }}</el-descriptions-item>
              <el-descriptions-item label="预估产量">{{ growth.estimated_yield }}</el-descriptions-item>
            </el-descriptions>
            <el-card shadow="never" class="mt-16">
              <div class="markdown-body" v-html="render(growth.analysis)"></div>
            </el-card>
          </div>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card header="历史长势曲线">
          <div ref="chartEl" style="height:320px"></div>
        </el-card>
        <el-card header="诊断记录" class="mt-16">
          <el-table :data="history" size="small" max-height="260">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="score" label="长势评分" width="90" />
            <el-table-column prop="green_index" label="绿度" width="80" />
            <el-table-column prop="stage" label="生育期" width="90" />
            <el-table-column prop="nutrient_issue" label="缺素" show-overflow-tooltip />
            <el-table-column prop="created_at" label="时间" width="150" type="time" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { marked } from 'marked'
import { growth as growthApi, fieldApi } from '../api'

const fields = ref([])
const fieldId = ref(null)
const growth = ref({})
const history = ref([])
const running = ref(false)
const chartEl = ref(null)
let chart = null

const scoreColor = [
  { color: '#f56c6c', percentage: 50 },
  { color: '#e6a23c', percentage: 70 },
  { color: '#67c23a', percentage: 100 },
]
function render(t) { return marked.parse(t || '') }

async function run() {
  running.value = true
  try {
    const res = await growthApi.run({ field_id: fieldId.value })
    growth.value = res.growth
    loadHistory()
  } finally { running.value = false }
}

async function loadHistory() {
  if (!fieldId.value) { history.value = []; drawChart(); return }
  const curve = await growthApi.history(fieldId.value)
  const page = await growthApi.page(1, 20)
  history.value = page.items
  drawChart(curve)
}

function drawChart(curve = []) {
  nextTick(() => {
    if (!chartEl.value) return
    if (!chart) chart = echarts.init(chartEl.value)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['长势评分', '绿度指数'] },
      xAxis: { type: 'category', data: curve.map(c => (c.created_at || '').slice(5,16).replace('T',' ')) },
      yAxis: [{ type: 'value', name: '评分', max: 100 }, { type: 'value', name: '绿度', max: 1 }],
      series: [
        { name: '长势评分', type: 'line', smooth: true, data: curve.map(c => c.score), areaStyle: { opacity: 0.1 } },
        { name: '绿度指数', type: 'line', smooth: true, yAxisIndex: 1, data: curve.map(c => c.green_index) },
      ],
    })
  })
}

onMounted(async () => {
  fields.value = await fieldApi.list()
  if (fields.value.length) { fieldId.value = fields.value[0].id; loadHistory() }
  else drawChart()
  window.addEventListener('resize', () => chart && chart.resize())
})
</script>
