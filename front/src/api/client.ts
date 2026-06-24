/**
 * 模块职责：Axios 客户端封装，负责基础地址、认证头、响应解包和登录态失效处理。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
import axios from 'axios'
import { clearAuthAndRedirect, getJwtToken } from './authToken'

const API_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS)

if (!Number.isFinite(API_TIMEOUT_MS) || API_TIMEOUT_MS <= 0) {
  throw new Error('VITE_API_TIMEOUT_MS must be a positive number')
}

const client = axios.create({
  baseURL: '',
  timeout: API_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use((config) => {
  const token = getJwtToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearAuthAndRedirect()
    }
    return Promise.reject(error)
  }
)

export default client
