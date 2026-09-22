<template>
  <CrudTable :api="crop" title="作物管理" :columns="columns" :form-fields="formFields" />
</template>

<script setup>
import CrudTable from '../components/CrudTable.vue'
import { crop } from '../api'

const columns = [
  { prop: 'id', label: 'ID', width: 60 },
  { prop: 'field_id', label: '地块ID', width: 80 },
  { prop: 'name', label: '作物' },
  { prop: 'variety', label: '品种' },
  { prop: 'stage', label: '生育期', width: 100 },
  { prop: 'target_yield', label: '目标产量', width: 100 },
  { prop: 'created_at', label: '创建时间', width: 150, type: 'time' },
]
const formFields = [
  { prop: 'field_id', label: '地块ID', type: 'number' },
  { prop: 'name', label: '作物名称' },
  { prop: 'variety', label: '品种' },
  { prop: 'stage', label: '生育期', options: ['苗期','分蘖期','拔节期','抽穗期','灌浆期','成熟期','生长期'].map(v => ({ value: v, label: v })) },
  { prop: 'target_yield', label: '目标产量', type: 'number' },
]
</script>
