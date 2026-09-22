import { request, aiRequest } from './request'

// 通用 CRUD 封装
export const crud = (base) => ({
  list: () => request.get(base),
  page: (page = 1, size = 20) => request.get(`${base}/page`, { params: { page, size } }),
  get: (id) => request.get(`${base}/${id}`),
  create: (data) => request.post(base, data),
  update: (id, data) => request.put(`${base}/${id}`, data),
  remove: (id) => request.delete(`${base}/${id}`),
})

export const auth = {
  login: (data) => request.post('/auth/login', data),
  me: (username) => request.get('/auth/me', { params: { username } }),
}

export const agent = {
  engine: () => request.get('/agent/engine'),
  run: (data) => aiRequest.post('/agent/run', data),
  logs: (params) => request.get('/agent/logs', { params }),
  trace: (rid) => request.get(`/agent/trace/${rid}`),
}

export const diagnosis = {
  ...crud('/diagnosis'),
  run: (data) => aiRequest.post('/diagnosis/run', data),
  resume: (id, decision) => aiRequest.post(`/diagnosis/${id}/resume`, { decision }),
}

export const growth = {
  ...crud('/growth'),
  run: (data) => aiRequest.post('/growth/run', data),
  history: (fieldId) => request.get(`/growth/history/${fieldId}`),
}

export const task = {
  ...crud('/task'),
  run: (data) => aiRequest.post('/task/run', data),
  setStatus: (id, status) => request.post(`/task/${id}/status`, { status }),
}

export const alert = {
  ...crud('/alert'),
  run: (data) => aiRequest.post('/alert/run', data),
  scan: () => aiRequest.post('/alert/scan'),
  resolve: (id) => request.post(`/alert/${id}/resolve`),
}

export const chat = {
  sessions: () => request.get('/chat/sessions'),
  newSession: () => request.post('/chat/sessions'),
  messages: (sid) => request.get(`/chat/sessions/${sid}/messages`),
  removeSession: (sid) => request.delete(`/chat/sessions/${sid}`),
  send: (data) => aiRequest.post('/chat/send', data),
  streamUrl: '/api/chat/stream',
}

export const knowledge = {
  docs: (page = 1, size = 20) => request.get('/knowledge/docs', { params: { page, size } }),
  search: (q, top_k = 5) => request.get('/knowledge/search', { params: { q, top_k } }),
  addText: (data) => request.post('/knowledge/text', data),
  reindex: () => request.post('/knowledge/reindex'),
  chunks: (docId) => request.get(`/knowledge/${docId}/chunks`),
  remove: (docId) => request.delete(`/knowledge/${docId}`),
  uploadUrl: '/api/knowledge/upload',
}

export const media = {
  list: () => request.get('/media'),
  page: (page = 1, size = 20) => request.get('/media/page', { params: { page, size } }),
  uploadUrl: '/api/media/upload',
}

export const sensor = {
  ...crud('/sensor'),
  data: (id, limit = 100) => request.get(`/sensor/${id}/data`, { params: { limit } }),
  stat: (id, window = 20) => request.get(`/sensor/${id}/stat`, { params: { window } }),
  simulate: (id, count = 10) => request.post(`/sensor/simulate/${id}`, null, { params: { count } }),
}

export const device = {
  ...crud('/device'),
  sendCommand: (data) => request.post('/device/command', data),
  commands: (id, page = 1, size = 20) => request.get(`/device/${id}/commands`, { params: { page, size } }),
}

export const fieldApi = { ...crud('/field'), detail: (id) => request.get(`/field/${id}/detail`) }
export const crop = crud('/crop')
export const weather = {
  forecast: (fieldId, days = 3) => request.get('/weather/forecast', { params: { field_id: fieldId, days } }),
  history: (page = 1, size = 20) => request.get('/weather/history', { params: { page, size } }),
}

export const dashboard = { overview: () => request.get('/dashboard/overview') }
export const report = { operations: () => aiRequest.get('/report/operations') }

export const llmConfig = {
  ...crud('/llm-config'),
  activate: (id) => request.post(`/llm-config/${id}/activate`),
  test: (id) => request.get(`/llm-config/${id}/test`),
}

export const health = () => request.get('/health')
