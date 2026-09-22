<template>
  <CrudTable :api="fieldApi" title="地块管理" :columns="columns" :form-fields="formFields">
    <template #row-actions="{ row }">
      <el-button link type="primary" size="small" @click="showDetail(row)">详情</el-button>
    </template>
  </CrudTable>

  <el-dialog v-model="detailVisible" title="地块聚合详情" width="640px">
    <el-descriptions :column="2" border size="small">
      <el-descriptions-item label="名称">{{ detail.name }}</el-descriptions-item>
      <el-descriptions-item label="编码">{{ detail.code }}</el-descriptions-item>
      <el-descriptions-item label="面积(亩)">{{ detail.area }}</el-descriptions-item>
      <el-descriptions-item label="土壤">{{ detail.soil_type }}</el-descriptions-item>
      <el-descriptions-item label="经纬度">{{ detail.lat }}, {{ detail.lon }}</el-descriptions-item>
      <el-descriptions-item label="状态">{{ detail.status }}</el-descriptions-item>
    </el-descriptions>
    <el-tabs class="mt-16">
      <el-tab-pane label="作物">
        <el-table :data="detail.crops" size="small"><el-table-column prop="name" label="作物" />
          <el-table-column prop="variety" label="品种" /><el-table-column prop="stage" label="生育期" /></el-table>
      </el-tab-pane>
      <el-tab-pane label="设备">
        <el-table :data="detail.devices" size="small"><el-table-column prop="name" label="设备" />
          <el-table-column prop="type" label="类型" /><el-table-column prop="online" label="在线" /></el-table>
      </el-tab-pane>
      <el-tab-pane label="传感器">
        <el-table :data="detail.sensors" size="small"><el-table-column prop="name" label="传感器" />
          <el-table-column prop="metric" label="指标" /><el-table-column prop="unit" label="单位" /></el-table>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import CrudTable from '../components/CrudTable.vue'
import { fieldApi } from '../api'

const columns = [
  { prop: 'id', label: 'ID', width: 60 },
  { prop: 'code', label: '编码', width: 90 },
  { prop: 'name', label: '名称' },
  { prop: 'area', label: '面积(亩)', width: 90 },
  { prop: 'soil_type', label: '土壤', width: 90 },
  { prop: 'status', label: '状态', width: 90, tag: (v) => v === 'normal' ? 'success' : 'info' },
]
const formFields = [
  { prop: 'code', label: '编码' },
  { prop: 'name', label: '名称' },
  { prop: 'area', label: '面积(亩)', type: 'number' },
  { prop: 'soil_type', label: '土壤类型' },
  { prop: 'lat', label: '纬度', type: 'number' },
  { prop: 'lon', label: '经度', type: 'number' },
  { prop: 'status', label: '状态', options: [{ value: 'normal', label: '正常' }, { value: 'rest', label: '休耕' }] },
]

const detailVisible = ref(false)
const detail = ref({})
async function showDetail(row) {
  detail.value = await fieldApi.detail(row.id)
  detailVisible.value = true
}
</script>
