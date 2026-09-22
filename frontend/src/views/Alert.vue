<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="flex-between">
          <span>预警研判（七类风险 · 同地块同类型去重合并 · 三级分级 · 并发巡检）</span>
          <div>
            <el-button type="warning" :icon="Aim" :loading="scanning" @click="scanAll">全农场并发巡检</el-button>
            <el-button type="primary" :loading="running" @click="runOne">单地块研判</el-button>
          </div>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="研判地块">
          <el-select v-model="fieldId" placeholder="可选(默认全部第一块)" clearable style="width:200px">
            <el-option v-for="f in fields" :key="f.id" :label="f.name" :value="f.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="statusFilter" clearable placeholder="全部" style="width:120px" @change="load">
            <el-option label="未关闭" value="open" /><el-option label="已解除" value="closed" />
          </el-select>
        </el-form-item>
      </el-form>

      <el-table :data="filteredAlerts" size="small" border v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">{{ riskName(row.type) }}</template>
        </el-table-column>
        <el-table-column prop="level" label="级别" width="80">
          <template #default="{ row }"><el-tag size="small" :type="levelType(row.level)">{{ row.level }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="title" label="标题" />
        <el-table-column prop="detail" label="详情" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }"><el-tag size="small" :type="row.status === 'open' ? 'danger' : 'info'">{{ row.status === 'open' ? '未关闭' : '已解除' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="150" type="time" />
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'open'" link type="success" size="small" @click="resolve(row)">解除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="mt-16" layout="total, prev, pager, next" :total="total"
        :page-size="size" :current-page="page" @current-change="onPage" background small />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Aim } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { alert, fieldApi } from '../api'

const fields = ref([]); const fieldId = ref(null)
const alerts = ref([]); const total = ref(0); const page = ref(1); const size = ref(20)
const loading = ref(false); const running = ref(false); const scanning = ref(false)
const statusFilter = ref('open')

const riskMap = { drought: '干旱', waterlog: '渍涝', heat: '高温热害', frost: '低温冻害', rain: '强降雨', device: '设备故障', pest: '病虫害爆发' }
function riskName(t) { return riskMap[t] || t }
function levelType(l) { return l === '紧急' ? 'danger' : (l === '重要' ? 'warning' : 'info') }
const filteredAlerts = computed(() => statusFilter.value ? alerts.value.filter(a => a.status === statusFilter.value) : alerts.value)

async function runOne() {
  running.value = true
  try {
    const res = await alert.run({ field_id: fieldId.value })
    ElMessage.success(`研判完成，新增/更新 ${res.alert?.risks?.length || 0} 条风险`)
    load()
  } finally { running.value = false }
}
async function scanAll() {
  scanning.value = true
  try {
    const res = await alert.scan()
    ElMessage.success(res?.fields ? `巡检 ${res.fields} 块地，共 ${res.risks} 条风险` : '巡检完成')
    load()
  } finally { scanning.value = false }
}
async function load() {
  loading.value = true
  try {
    const data = await alert.page(page.value, size.value)
    alerts.value = data.items; total.value = data.total
  } finally { loading.value = false }
}
function onPage(p) { page.value = p; load() }
async function resolve(row) { await alert.resolve(row.id); ElMessage.success('已解除，形成闭环'); load() }

onMounted(async () => { fields.value = await fieldApi.list(); load() })
</script>
