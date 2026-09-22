<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="flex-between">
          <span>{{ title }}</span>
          <div>
            <slot name="toolbar" />
            <el-button type="primary" :icon="Plus" @click="openCreate" v-if="!readonly">新增</el-button>
            <el-button :icon="Refresh" @click="load">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table :data="rows" v-loading="loading" size="small" border>
        <el-table-column v-for="col in columns" :key="col.prop" :prop="col.prop" :label="col.label"
          :width="col.width" show-overflow-tooltip>
          <template #default="{ row }" v-if="col.tag || col.type">
            <el-tag v-if="col.tag" size="small" :type="col.tag(row[col.prop])">{{ row[col.prop] }}</el-tag>
            <span v-else-if="col.type === 'time'">{{ (row[col.prop] || '').slice(0,16).replace('T',' ') }}</span>
            <span v-else>{{ row[col.prop] }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" :width="readonly ? 90 : 150" fixed="right" v-if="!hideActions">
          <template #default="{ row }">
            <slot name="row-actions" :row="row" />
            <el-button v-if="!readonly" link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination class="mt-16" layout="total, prev, pager, next" :total="total"
        :page-size="size" :current-page="page" @current-change="onPage" background small />
    </el-card>

    <el-dialog v-model="dialog" :title="editing.id ? '编辑' : '新增'" width="520px">
      <el-form :model="editing" label-width="110px">
        <el-form-item v-for="f in formFields" :key="f.prop" :label="f.label">
          <el-select v-if="f.options" v-model="editing[f.prop]" style="width:100%" clearable>
            <el-option v-for="o in f.options" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
          <el-input-number v-else-if="f.type === 'number'" v-model="editing[f.prop]" style="width:100%" />
          <el-switch v-else-if="f.type === 'bool'" v-model="editing[f.prop]" />
          <el-input v-else v-model="editing[f.prop]" type="textarea" v-if="f.textarea" :rows="3" />
          <el-input v-else v-model="editing[f.prop]" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="save" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const props = defineProps({
  api: { type: Object, required: true },
  title: { type: String, default: '' },
  columns: { type: Array, default: () => [] },
  formFields: { type: Array, default: () => [] },
  readonly: { type: Boolean, default: false },
  hideActions: { type: Boolean, default: false },
})
const emit = defineEmits(['loaded'])

const rows = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const loading = ref(false)
const dialog = ref(false)
const saving = ref(false)
const editing = ref({})

async function load() {
  loading.value = true
  try {
    const data = await props.api.page(page.value, size.value)
    rows.value = data.items
    total.value = data.total
    emit('loaded', rows.value)
  } finally { loading.value = false }
}
function onPage(p) { page.value = p; load() }
function openCreate() { editing.value = {}; dialog.value = true }
function openEdit(row) { editing.value = { ...row }; dialog.value = true }
async function save() {
  saving.value = true
  try {
    if (editing.value.id) await props.api.update(editing.value.id, editing.value)
    else await props.api.create(editing.value)
    ElMessage.success('保存成功'); dialog.value = false; load()
  } finally { saving.value = false }
}
async function remove(row) {
  await ElMessageBox.confirm('确认删除该记录？', '提示', { type: 'warning' })
  await props.api.remove(row.id)
  ElMessage.success('已删除'); load()
}
watch(() => props.api, load)
onMounted(load)
defineExpose({ load })
</script>
