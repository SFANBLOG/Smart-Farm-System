<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="flex-between">
          <span>影像管理（图片像素分析 · 视频自动抽帧）</span>
          <el-upload :action="media.uploadUrl" :show-file-list="false" :on-success="onUploaded"
            accept="image/*,video/*" :data="{ field_id: fieldId }">
            <el-button type="primary" :icon="Upload">上传图片/视频</el-button>
          </el-upload>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="关联地块">
          <el-select v-model="fieldId" placeholder="可选" clearable style="width:180px">
            <el-option v-for="f in fields" :key="f.id" :label="f.name" :value="f.id" />
          </el-select>
        </el-form-item>
      </el-form>

      <div class="wall">
        <el-card v-for="m in list" :key="m.id" class="wall-item" shadow="hover" body-style="padding:0">
          <el-image v-if="m.kind === 'image'" :src="m.path" fit="cover" class="wall-img" :preview-src-list="[m.path]" />
          <div v-else class="wall-video">🎬 视频</div>
          <div class="wall-info">
            <div class="name">{{ m.filename || m.path }}</div>
            <div v-if="m.meta?.pixel" class="pixel">
              <el-tag size="small" type="success">健康 {{ m.meta.pixel.health_score }}</el-tag>
              <el-tag size="small">绿 {{ (m.meta.pixel.green_ratio*100).toFixed(0) }}%</el-tag>
              <el-tag size="small" type="warning">黄 {{ (m.meta.pixel.yellow_ratio*100).toFixed(0) }}%</el-tag>
              <el-tag size="small" type="danger">褐 {{ (m.meta.pixel.brown_ratio*100).toFixed(0) }}%</el-tag>
              <div class="hint">{{ m.meta.pixel.hint }}</div>
              <div class="text-muted" style="font-size:11px">通道: {{ m.meta.pixel.channel }}</div>
            </div>
            <div v-if="m.meta?.frames" class="text-muted" style="font-size:12px">抽帧 {{ m.meta.frames }} 张</div>
          </div>
        </el-card>
      </div>
      <el-empty v-if="!list.length" description="暂无影像" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Upload } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { media, fieldApi } from '../api'

const list = ref([]); const fields = ref([]); const fieldId = ref(null)

async function load() { const d = await media.page(1, 60); list.value = d.items }
function onUploaded(resp) {
  if (resp.code === 200) { ElMessage.success('上传并分析完成'); load() }
  else ElMessage.error(resp.msg)
}
onMounted(async () => { fields.value = await fieldApi.list(); load() })
</script>

<style scoped>
.wall { display: grid; gap: 16px; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); }
.wall-img { width: 100%; height: 150px; }
.wall-video { width: 100%; height: 150px; display: flex; align-items: center; justify-content: center; background: #f0f2f5; font-size: 24px; }
.wall-info { padding: 10px; }
.wall-info .name { font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pixel { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
.pixel .hint { width: 100%; font-size: 12px; color: #606266; margin-top: 4px; }
</style>
