<template>
  <CrudTable :api="device" title="设备管理（指令带安全护栏）" :columns="columns" :form-fields="formFields">
    <template #row-actions="{ row }">
      <el-button link type="primary" size="small" @click="openCmd(row)">下发指令</el-button>
      <el-button link size="small" @click="openLog(row)">指令流水</el-button>
    </template>
  </CrudTable>

  <el-dialog v-model="cmdVisible" title="手动下发指令（同样过安全校验）" width="460px">
    <el-form label-width="80px">
      <el-form-item label="设备">{{ cmdForm.deviceName }}</el-form-item>
      <el-form-item label="动作">
        <el-select v-model="cmdForm.action" style="width:100%">
          <el-option label="灌溉 irrigate" value="irrigate" />
          <el-option label="施药 spray" value="spray" />
          <el-option label="通风 ventilate" value="ventilate" />
          <el-option label="开启 open" value="open" />
          <el-option label="关闭 close" value="close" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="cmdVisible = false">取消</el-button>
      <el-button type="primary" @click="sendCmd" :loading="sending">下发</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="logVisible" title="设备指令流水" width="720px">
    <el-table :data="logs" size="small" max-height="400">
      <el-table-column prop="action" label="动作" width="90" />
      <el-table-column prop="source" label="来源" width="80" />
      <el-table-column label="校验" width="80">
        <template #default="{ row }"><el-tag size="small" :type="row.passed ? 'success' : 'danger'">{{ row.passed ? '通过' : '拦截' }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="blocked_reason" label="拦截原因" show-overflow-tooltip />
      <el-table-column prop="created_at" label="时间" width="150" type="time" />
    </el-table>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import CrudTable from '../components/CrudTable.vue'
import { device } from '../api'

const columns = [
  { prop: 'id', label: 'ID', width: 60 },
  { prop: 'code', label: '编码', width: 90 },
  { prop: 'name', label: '名称' },
  { prop: 'type', label: '类型', width: 90 },
  { prop: 'online', label: '在线', width: 80, tag: (v) => v ? 'success' : 'danger' },
  { prop: 'status', label: '状态', width: 90 },
]
const formFields = [
  { prop: 'code', label: '编码' },
  { prop: 'name', label: '名称' },
  { prop: 'type', label: '类型', options: ['pump','valve','sprayer','fan','light'].map(v => ({ value: v, label: v })) },
  { prop: 'field_id', label: '地块ID', type: 'number' },
  { prop: 'online', label: '在线', type: 'bool' },
  { prop: 'status', label: '状态' },
]

const cmdVisible = ref(false); const sending = ref(false)
const cmdForm = ref({ device_id: null, action: 'irrigate', deviceName: '' })
function openCmd(row) { cmdForm.value = { device_id: row.id, action: 'irrigate', deviceName: row.name }; cmdVisible.value = true }
async function sendCmd() {
  sending.value = true
  try {
    const res = await device.sendCommand({ device_id: cmdForm.value.device_id, action: cmdForm.value.action })
    if (res.ok) ElMessage.success('指令已执行')
    else ElMessage.warning('指令被安全护栏拦截：' + res.reason)
    cmdVisible.value = false
  } finally { sending.value = false }
}

const logVisible = ref(false); const logs = ref([])
async function openLog(row) {
  const data = await device.commands(row.id, 1, 50)
  logs.value = data.items; logVisible.value = true
}
</script>
