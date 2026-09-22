import axios from 'axios'
import { ElMessage } from 'element-plus'

// 普通 CRUD 30 秒；AI 推理类单独放宽到 3 分钟
export const request = axios.create({ baseURL: '/api', timeout: 30000 })
export const aiRequest = axios.create({ baseURL: '/api', timeout: 180000 })

function unwrap(resp) {
  const body = resp.data
  if (body && typeof body === 'object' && 'code' in body) {
    if (body.code === 200) return body.data
    if (body.code === 401) {
      localStorage.removeItem('token')
      window.location.hash = '#/login'
    }
    return Promise.reject(new Error(body.msg || '请求失败'))
  }
  return body
}

function onError(err) {
  let msg = '网络错误'
  if (err.response) {
    const s = err.response.status
    if (s === 504) msg = '网关超时：AI 推理耗时较长，请稍后重试或切换离线模式'
    else if (s >= 500) msg = `服务器错误(${s})`
    else msg = err.response.data?.msg || `请求失败(${s})`
  } else if (err.code === 'ECONNABORTED') {
    msg = '请求超时，请稍后重试'
  }
  ElMessage.error(msg)
  return Promise.reject(err)
}

request.interceptors.response.use(unwrap, onError)
aiRequest.interceptors.response.use(unwrap, onError)

for (const inst of [request, aiRequest]) {
  inst.interceptors.request.use(cfg => {
    const t = localStorage.getItem('token')
    if (t) cfg.headers.Authorization = `Bearer ${t}`
    return cfg
  })
}
