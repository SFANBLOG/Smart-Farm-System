<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="flex-between">
          <span>气象预报（Open-Meteo 实时，失败退化为季节性本地推演 · 10 分钟缓存）</span>
          <el-select v-model="fieldId" placeholder="选择地块" clearable style="width:200px" @change="load">
            <el-option v-for="f in fields" :key="f.id" :label="f.name" :value="f.id" />
          </el-select>
        </div>
      </template>

      <div class="card-grid">
        <el-card v-for="(d, i) in forecast" :key="i" class="weather-card" shadow="hover">
          <div class="date">{{ d.date }}<el-tag size="small" :type="d.source === 'open-meteo' ? 'success' : 'info'" style="margin-left:6px">{{ d.source === 'open-meteo' ? '实时' : '本地推演' }}</el-tag></div>
          <div class="icon">{{ weatherIcon(d) }}</div>
          <div class="temp">{{ d.temp_min }}℃ ~ {{ d.temp_max }}℃</div>
          <div class="detail">
            <span>🌧 降雨 {{ d.rain }}mm</span>
            <span v-if="d.wind !== undefined">💨 风 {{ d.wind }}m/s</span>
            <span v-if="d.humidity !== undefined">💧 湿 {{ d.humidity }}%</span>
          </div>
          <el-tag v-if="d.rain >= 15" type="warning" size="small">强降雨提示</el-tag>
          <el-tag v-if="d.temp_max >= 35" type="danger" size="small" style="margin-left:4px">高温提示</el-tag>
        </el-card>
      </div>
      <el-empty v-if="!forecast.length" description="选择地块查看预报" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { weather, fieldApi } from '../api'

const fields = ref([]); const fieldId = ref(null); const forecast = ref([])

function weatherIcon(d) {
  if ((d.rain || 0) >= 15) return '⛈'
  if ((d.rain || 0) > 1) return '🌧'
  if ((d.temp_max || 0) >= 33) return '🔥'
  if ((d.temp_min || 99) <= 3) return '❄️'
  return '☀️'
}
async function load() { forecast.value = await weather.forecast(fieldId.value, 3) }
onMounted(async () => {
  fields.value = await fieldApi.list()
  if (fields.value.length) { fieldId.value = fields.value[0].id }
  load()
})
</script>

<style scoped>
.weather-card { text-align: center; }
.date { font-weight: 600; }
.icon { font-size: 42px; margin: 10px 0; }
.temp { font-size: 18px; font-weight: 600; color: #409eff; }
.detail { display: flex; flex-direction: column; gap: 4px; margin-top: 10px; font-size: 13px; color: #606266; }
</style>
