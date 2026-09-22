<template>
  <div class="page">
    <el-row :gutter="16">
      <el-col :span="10">
        <el-card header="知识导入">
          <el-upload :action="knowledge.uploadUrl" :show-file-list="false" :on-success="onUploaded"
            accept=".pdf,.txt" drag>
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽 PDF / TXT 到此处，或<em>点击上传</em></div>
            <template #tip><div class="el-upload__tip text-muted">自动切片 → 哈希向量化 → 入库索引</div></template>
          </el-upload>
          <el-divider>或直接录入文本</el-divider>
          <el-input v-model="textForm.title" placeholder="标题" class="mb-8" />
          <el-input v-model="textForm.content" type="textarea" :rows="4" placeholder="正文内容" />
          <div class="mt-8">
            <el-button type="primary" @click="addText">录入</el-button>
            <el-button @click="reindex" :loading="reindexing">重建索引(reindex)</el-button>
          </div>
        </el-card>

        <el-card header="文档库" class="mt-16">
          <el-table :data="docs" size="small" max-height="320">
            <el-table-column prop="id" label="ID" width="55" />
            <el-table-column prop="title" label="标题" show-overflow-tooltip />
            <el-table-column prop="chunk_count" label="切片" width="70" />
            <el-table-column label="操作" width="70">
              <template #default="{ row }"><el-button link type="danger" size="small" @click="removeDoc(row)">删除</el-button></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="14">
        <el-card header="语义检索（余弦 + 关键词混合打分 · 可溯源）">
          <div class="search-bar">
            <el-input v-model="query" placeholder="输入问题，例如：稻瘟病如何防治" @keyup.enter="search">
              <template #append><el-button :icon="Search" @click="search" :loading="searching">检索</el-button></template>
            </el-input>
          </div>
          <el-empty v-if="!hits.length && searched" description="无命中：以实地判断为准" />
          <div v-for="h in hits" :key="h.chunk_id" class="hit">
            <div class="hit-head">
              <el-tag size="small">《{{ h.title }}》</el-tag>
              <el-tag size="small" type="success">相关度 {{ (h.score * 100).toFixed(1) }}%</el-tag>
            </div>
            <div class="hit-body">{{ h.content }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { UploadFilled, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { knowledge } from '../api'

const docs = ref([]); const query = ref(''); const hits = ref([])
const searched = ref(false); const searching = ref(false); const reindexing = ref(false)
const textForm = ref({ title: '', content: '' })

async function loadDocs() { const d = await knowledge.docs(1, 200); docs.value = d.items }
async function search() {
  if (!query.value.trim()) return
  searching.value = true
  try { hits.value = await knowledge.search(query.value, 6); searched.value = true }
  finally { searching.value = false }
}
function onUploaded(resp) {
  if (resp.code === 200) { ElMessage.success(resp.msg); loadDocs() }
  else ElMessage.error(resp.msg)
}
async function addText() {
  if (!textForm.value.title || !textForm.value.content) return ElMessage.warning('请填写标题与内容')
  await knowledge.addText(textForm.value)
  ElMessage.success('录入成功'); textForm.value = { title: '', content: '' }; loadDocs()
}
async function reindex() {
  reindexing.value = true
  try { const r = await knowledge.reindex(); ElMessage.success(`已重建 ${r.reindexed} 个切片`) }
  finally { reindexing.value = false }
}
async function removeDoc(row) {
  await ElMessageBox.confirm('确认删除该文档及其切片？', '提示', { type: 'warning' })
  await knowledge.remove(row.id); ElMessage.success('已删除'); loadDocs()
}
onMounted(loadDocs)
</script>

<style scoped>
.search-bar { margin-bottom: 16px; }
.hit { border: 1px solid #ebeef5; border-radius: 6px; padding: 10px 12px; margin-bottom: 10px; }
.hit-head { display: flex; gap: 8px; margin-bottom: 6px; }
.hit-body { font-size: 13px; color: #606266; line-height: 1.6; }
.mb-8 { margin-bottom: 8px; }
</style>
