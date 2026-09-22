<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="flex-between">
          <span>AI 运营分析报告</span>
          <div>
            <el-button type="primary" :icon="Document" :loading="loading" @click="generate">一键生成报告</el-button>
            <el-button :icon="Download" :disabled="!report.markdown" @click="exportMd">导出 Markdown</el-button>
          </div>
        </div>
      </template>

      <el-empty v-if="!report.markdown" description="点击「一键生成报告」，由 LLM（或离线兜底）汇总生成" />
      <div v-else>
        <el-alert :type="report.llm_mode === 'langchain' ? 'success' : 'info'" :closable="false" show-icon
          :title="`生成模式：${report.llm_mode === 'langchain' ? '真实大模型' : '本地离线兜底'}`" />
        <div v-if="report.summary" class="summary mt-16">
          <el-tag v-for="(v, k) in report.summary" :key="k" class="sum-tag" type="info">
            {{ k }}：{{ Array.isArray(v) ? v.join('、') : (typeof v === 'object' ? JSON.stringify(v) : v) }}
          </el-tag>
        </div>
        <el-divider />
        <div class="markdown-body report-body" v-html="render(report.markdown)"></div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Document, Download } from '@element-plus/icons-vue'
import { marked } from 'marked'
import { ElMessage } from 'element-plus'
import { report as reportApi } from '../api'

const report = ref({}); const loading = ref(false)
function render(t) { return marked.parse(t || '') }

async function generate() {
  loading.value = true
  try { report.value = await reportApi.operations(); ElMessage.success('报告已生成') }
  finally { loading.value = false }
}
function exportMd() {
  const blob = new Blob([report.value.markdown], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `农场运营报告_${Date.now()}.md`; a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.summary { display: flex; flex-wrap: wrap; gap: 8px; }
.sum-tag { font-size: 12px; }
.report-body { background: #fff; padding: 8px; }
</style>
