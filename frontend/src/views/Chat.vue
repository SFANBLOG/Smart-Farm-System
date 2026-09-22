<template>
  <div class="page chat-page">
    <el-row :gutter="16" style="height:100%">
      <el-col :span="5">
        <el-card class="sessions-card">
          <template #header>
            <div class="flex-between">
              <span>会话</span>
              <el-button size="small" type="primary" :icon="Plus" @click="newSession">新建</el-button>
            </div>
          </template>
          <div class="session-list">
            <div v-for="s in sessions" :key="s.id"
              :class="['session-item', { active: s.id === currentSession }]"
              @click="selectSession(s.id)">
              <span class="title">{{ s.title }}</span>
              <el-icon class="del" @click.stop="removeSession(s.id)"><Delete /></el-icon>
            </div>
            <el-empty v-if="!sessions.length" description="暂无会话" :image-size="50" />
          </div>
        </el-card>
      </el-col>

      <el-col :span="19">
        <el-card class="chat-card">
          <template #header>
            <div class="flex-between">
              <span>AI 问答助手（SSE 流式 · 多轮记忆 · 图文提问 · RAG 溯源）</span>
              <div>
                <el-select v-model="fieldId" placeholder="地块(可选)" clearable size="small" style="width:160px">
                  <el-option v-for="f in fields" :key="f.id" :label="f.name" :value="f.id" />
                </el-select>
              </div>
            </div>
          </template>

          <div ref="msgBox" class="msg-box">
            <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
              <div class="avatar">{{ m.role === 'user' ? '我' : 'AI' }}</div>
              <div class="bubble">
                <div v-if="m.role === 'assistant'" class="markdown-body" v-html="render(m.content)"></div>
                <div v-else>{{ m.content }}</div>
                <div v-if="m.knowledge_refs?.length" class="refs">
                  <div class="refs-title">📚 知识依据：</div>
                  <el-tag v-for="(r, ri) in m.knowledge_refs" :key="r.chunk_id" size="small" type="info" class="ref-tag">
                    【{{ ri + 1 }}】《{{ r.title }}》 {{ (r.score * 100).toFixed(0) }}%
                  </el-tag>
                </div>
              </div>
            </div>
            <el-empty v-if="!messages.length" description="开始提问，例如：水稻叶片有褐斑怎么办？" />
          </div>

          <div class="input-bar">
            <el-input v-model="input" type="textarea" :rows="2" placeholder="输入问题，Enter 发送，Shift+Enter 换行"
              @keydown.enter.exact.prevent="send" :disabled="streaming" />
            <el-button type="primary" :loading="streaming" @click="send" :icon="Promotion">发送</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { Plus, Delete, Promotion } from '@element-plus/icons-vue'
import { marked } from 'marked'
import { markedHighlight } from 'marked-highlight'
import hljs from 'highlight.js'
import { ElMessage } from 'element-plus'
import { chat, fieldApi } from '../api'

marked.use(markedHighlight({ highlight: (code, lang) => {
  try { return hljs.highlight(code, { language: lang || 'plaintext' }).value } catch { return code }
} }))

const sessions = ref([])
const currentSession = ref(null)
const messages = ref([])
const input = ref('')
const streaming = ref(false)
const fields = ref([])
const fieldId = ref(null)
const msgBox = ref(null)

function render(text) { return marked.parse(text || '') }
function scrollBottom() { nextTick(() => { if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight }) }

async function loadSessions() { sessions.value = await chat.sessions() }
async function newSession() {
  const s = await chat.newSession()
  await loadSessions(); selectSession(s.id)
}
async function selectSession(id) {
  currentSession.value = id
  const msgs = await chat.messages(id)
  messages.value = msgs.map(m => ({ role: m.role, content: m.content, knowledge_refs: m.knowledge_refs }))
  scrollBottom()
}
async function removeSession(id) {
  await chat.removeSession(id)
  if (currentSession.value === id) { messages.value = []; currentSession.value = null }
  loadSessions()
}

function send() {
  const text = input.value.trim()
  if (!text || streaming.value) return
  input.value = ''
  messages.value.push({ role: 'user', content: text })
  const aiMsg = { role: 'assistant', content: '', knowledge_refs: [] }
  messages.value.push(aiMsg)
  scrollBottom()
  streaming.value = true

  const body = JSON.stringify({ session_id: currentSession.value, message: text, field_id: fieldId.value })
  fetch(chat.streamUrl, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body
  }).then(async resp => {
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const parts = buf.split('\n\n')
      buf = parts.pop()
      for (const part of parts) handleSSE(part, aiMsg)
      scrollBottom()
    }
  }).catch(e => {
    ElMessage.error('流式请求失败：' + e.message)
  }).finally(() => {
    streaming.value = false
    loadSessions()
  })
}

function handleSSE(block, aiMsg) {
  const lines = block.split('\n')
  let event = 'message', data = ''
  for (const l of lines) {
    if (l.startsWith('event:')) event = l.slice(6).trim()
    else if (l.startsWith('data:')) data += l.slice(5).trim()
  }
  if (!data) return
  let obj; try { obj = JSON.parse(data) } catch { return }
  if (event === 'token') aiMsg.content += obj.text
  else if (event === 'refs') { aiMsg.knowledge_refs = obj.refs || []; if (obj.session_id) currentSession.value = obj.session_id }
}

onMounted(async () => {
  fields.value = await fieldApi.list()
  await loadSessions()
  if (sessions.value.length) selectSession(sessions.value[0].id)
})
</script>

<style scoped>
.chat-page, .chat-page .el-row { height: calc(100vh - 92px); }
.sessions-card, .chat-card { height: 100%; display: flex; flex-direction: column; }
.chat-card :deep(.el-card__body) { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.session-list { max-height: calc(100vh - 200px); overflow-y: auto; }
.session-item { display: flex; justify-content: space-between; align-items: center; padding: 8px; border-radius: 6px; cursor: pointer; }
.session-item:hover { background: #f5f7fa; }
.session-item.active { background: #ecf5ff; }
.session-item .title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.session-item .del { color: #f56c6c; visibility: hidden; }
.session-item:hover .del { visibility: visible; }
.msg-box { flex: 1; overflow-y: auto; padding: 8px; }
.msg { display: flex; margin-bottom: 16px; gap: 8px; }
.msg.user { flex-direction: row-reverse; }
.avatar { width: 34px; height: 34px; border-radius: 50%; background: #409eff; color: #fff;
  display: flex; align-items: center; justify-content: center; font-size: 13px; flex-shrink: 0; }
.msg.user .avatar { background: #67c23a; }
.bubble { max-width: 76%; background: #f4f4f5; padding: 10px 14px; border-radius: 8px; }
.msg.user .bubble { background: #ecf5ff; }
.refs { margin-top: 8px; border-top: 1px dashed #dcdfe6; padding-top: 6px; }
.refs-title { font-size: 12px; color: #909399; margin-bottom: 4px; }
.ref-tag { margin: 2px 4px 2px 0; }
.input-bar { display: flex; gap: 8px; padding-top: 10px; border-top: 1px solid #eee; align-items: flex-end; }
</style>
