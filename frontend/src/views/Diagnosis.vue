<template>
  <div class="page">
    <el-row :gutter="16">
      <el-col :span="9">
        <el-card header="多模态诊断工作台">
          <el-form label-width="70px">
            <el-form-item label="地块">
              <el-select v-model="form.field_id" placeholder="可选" clearable style="width:100%">
                <el-option v-for="f in fields" :key="f.id" :label="f.name" :value="f.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="叶片图">
              <el-upload :action="media.uploadUrl" :show-file-list="false" :on-success="onUploaded"
                accept="image/*" :data="{ field_id: form.field_id }">
                <el-button :icon="Upload">上传图片</el-button>
              </el-upload>
            </el-form-item>
            <el-form-item label="文字描述">
              <el-input v-model="form.user_input" type="textarea" :rows="3"
                placeholder="例如：叶片出现褐斑并有蔓延趋势" />
            </el-form-item>
            <el-button type="primary" :loading="running" @click="run" :icon="FirstAidKit">开始诊断</el-button>
          </el-form>

          <div v-if="thumbs.length" class="thumbs mt-16">
            <el-image v-for="(t, i) in thumbs" :key="i" :src="t" fit="cover" class="thumb" />
          </div>
        </el-card>
      </el-col>

      <el-col :span="15">
        <el-card header="诊断结果">
          <el-empty v-if="!result.diagnosis" description="上传图片或填写描述后开始诊断" />
          <div v-else>
            <el-alert v-if="result.need_confirm" type="warning" show-icon :closable="false"
              title="检测到重度病害/高危：自动化节点已挂起，需人工确认后才会执行灌溉/打药/设备联动" />
            <el-descriptions :column="2" border class="mt-16">
              <el-descriptions-item label="疑似病害">
                <b>{{ result.diagnosis.disease }}</b>
              </el-descriptions-item>
              <el-descriptions-item label="严重度">
                <el-tag :type="sevType(result.diagnosis.severity)">{{ result.diagnosis.severity }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="置信度">{{ result.diagnosis.confidence }}</el-descriptions-item>
              <el-descriptions-item label="健康评分">{{ result.diagnosis.health_score ?? '-' }}</el-descriptions-item>
              <el-descriptions-item label="推荐药剂">{{ result.diagnosis.pesticide }}</el-descriptions-item>
              <el-descriptions-item label="用量">{{ result.diagnosis.dosage }}</el-descriptions-item>
              <el-descriptions-item label="安全间隔期">{{ result.diagnosis.safety_interval }}</el-descriptions-item>
              <el-descriptions-item label="休药期">{{ result.diagnosis.withdrawal_period }}</el-descriptions-item>
            </el-descriptions>

            <el-card v-if="result.diagnosis.text" shadow="never" class="mt-16">
              <div class="markdown-body" v-html="render(result.diagnosis.text)"></div>
            </el-card>

            <div v-if="result.diagnosis.refs?.length" class="mt-16">
              <div class="text-muted">📚 知识依据：</div>
              <el-tag v-for="r in result.diagnosis.refs" :key="r.chunk_id" size="small" type="info" class="ref-tag">
                《{{ r.title }}》 {{ (r.score * 100).toFixed(0) }}%
              </el-tag>
            </div>

            <div v-if="result.control?.commands?.length" class="mt-16">
              <div class="text-muted">🔧 设备指令（安全护栏）：</div>
              <el-table :data="result.control.commands" size="small">
                <el-table-column prop="device" label="设备" />
                <el-table-column prop="action" label="动作" width="90" />
                <el-table-column label="结果" width="90">
                  <template #default="{ row }">
                    <el-tag :type="row.ok ? 'success' : 'danger'" size="small">{{ row.ok ? '已执行' : '已拦截' }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="reason" label="说明" show-overflow-tooltip />
              </el-table>
            </div>

            <div v-if="result.need_confirm && pendingId" class="mt-16">
              <el-button type="success" @click="resume('approve')">✓ 确认执行</el-button>
              <el-button type="danger" @click="resume('reject')">✗ 驳回</el-button>
            </div>
          </div>
        </el-card>

        <el-card header="历史诊断" class="mt-16">
          <el-table :data="history" size="small" max-height="260">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="disease" label="病害" />
            <el-table-column prop="severity" label="严重度" width="80" />
            <el-table-column prop="pesticide" label="药剂" width="120" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 'done' || row.status === 'confirmed' ? 'success' : (row.status === 'rejected' ? 'danger' : 'warning')">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="时间" width="150">
              <template #default="{ row }">{{ row.created_at?.slice(0,16).replace('T',' ') }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Upload, FirstAidKit } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { diagnosis, fieldApi, media } from '../api'

const fields = ref([])
const history = ref([])
const result = ref({})
const form = ref({ field_id: null, user_input: '', media_paths: [] })
const thumbs = ref([])
const running = ref(false)
const pendingId = ref(null)

function render(t) { return marked.parse(t || '') }
function sevType(s) { return s === '重度' ? 'danger' : (s === '中度' ? 'warning' : 'success') }

function onUploaded(resp) {
  if (resp.code === 200) {
    form.value.media_paths.push(resp.data.media_path)
    thumbs.value.push(resp.data.path)
    ElMessage.success('上传并分析完成')
  }
}

async function run() {
  running.value = true
  try {
    result.value = await diagnosis.run(form.value)
    pendingId.value = result.value.need_confirm ? await findPending() : null
    loadHistory()
  } finally { running.value = false }
}

async function findPending() {
  const list = await diagnosis.list()
  const p = list.find(d => d.request_id === result.value.request_id && d.need_confirm)
  return p?.id || null
}

async function resume(decision) {
  const res = await diagnosis.resume(pendingId.value, decision)
  ElMessage.success(decision === 'approve' ? '已确认并执行后续节点' : '已驳回，终止自动化')
  if (res.commands) result.value.control = { commands: res.commands }
  pendingId.value = null
  loadHistory()
}

async function loadHistory() {
  const data = await diagnosis.page(1, 20)
  history.value = data.items
}

onMounted(async () => {
  fields.value = await fieldApi.list()
  loadHistory()
})
</script>

<style scoped>
.thumbs { display: flex; gap: 8px; flex-wrap: wrap; }
.thumb { width: 80px; height: 80px; border-radius: 6px; }
.ref-tag { margin: 2px 4px 2px 0; }
</style>
