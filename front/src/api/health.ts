import axios from 'axios'
import client from './client'
import { endpoints } from './endpoints'
import type { ApiResponse } from '../types/api'

export type ReadinessState = 'ok' | 'starting' | 'failed'
export type ModelRuntimeState = 'pending' | 'starting' | 'ready' | 'failed'

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

export interface ReadinessStatus {
  status: ReadinessState
  checks: {
    database: boolean
    runtime_store: boolean
    model_runtime: ModelRuntimeStatus
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

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
