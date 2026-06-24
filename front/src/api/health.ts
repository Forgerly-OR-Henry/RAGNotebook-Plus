/**
 * 模块职责：前端 API 模块，负责封装 HTTP/SSE 请求并保持视图层调用简洁。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
import axios from 'axios'
import client from './client'
import { endpoints } from './endpoints'
import type { ApiResponse } from '../types/api'

/**
 * 类型：`ReadinessState` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export type ReadinessState = 'ok' | 'starting' | 'failed'
/**
 * 类型：`ModelRuntimeState` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export type ModelRuntimeState = 'pending' | 'starting' | 'ready' | 'failed'

/**
 * 接口：`ModelRuntimeStatus` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface ModelRuntimeStatus {
  status: ModelRuntimeState
  started: boolean
  elapsed_seconds: number
  current_step: string
  error: string | null
  components: {
    models: boolean
    note_service: boolean
    reranker: boolean
  }
}

/**
 * 接口：`ReadinessStatus` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface ReadinessStatus {
  status: ReadinessState
  checks: {
    database: boolean
    runtime_store: boolean
    model_runtime: ModelRuntimeStatus
  }
}

/**
 * 用途：执行isRecord相关业务逻辑。
 * @param value 调用方传入的value参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

/**
 * 用途：执行asReadinessStatus相关业务逻辑。
 * @param value 调用方传入的value参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function asReadinessStatus(value: unknown): ReadinessStatus | null {
  if (!isRecord(value)) {
    return null
  }
  const status = value.status
  if (status !== 'ok' && status !== 'starting' && status !== 'failed') {
    return null
  }
  if (!isRecord(value.checks)) {
    return null
  }
  return value as unknown as ReadinessStatus
}

/**
 * 用途：执行extractReadinessStatus相关业务逻辑。
 * @param value 调用方传入的value参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function extractReadinessStatus(value: unknown): ReadinessStatus | null {
  const direct = asReadinessStatus(value)
  if (direct) {
    return direct
  }
  if (!isRecord(value)) {
    return null
  }
  return (
    asReadinessStatus(value.data) ||
    asReadinessStatus(value.detail) ||
    asReadinessStatus(value.message)
  )
}

export const healthApi = {
  getReadiness: async () => {
    try {
      const res = await client.get<ApiResponse<ReadinessStatus>>(endpoints.healthReady)
      return res.data.data
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const readiness = extractReadinessStatus(error.response?.data)
        if (readiness) {
          return readiness
        }
      }
      throw error
    }
  },
}
