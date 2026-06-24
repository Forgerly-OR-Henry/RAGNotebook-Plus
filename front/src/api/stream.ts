/**
 * 模块职责：前端 API 模块，负责封装 HTTP/SSE 请求并保持视图层调用简洁。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
import { clearAuthAndRedirect, getJwtToken } from './authToken'

/**
 * 接口：`StreamEvent` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface StreamEvent {
  event_type?: string
  error_message?: string
  message?: string
}

/**
 * 接口：`StreamResult` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface StreamResult<T extends StreamEvent> {
  finalEvent: T | null
  lastError: string
}

export function parseSseBlock<T>(block: string): T | null {
  const data = block
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
    .join('\n')
    .trim()

  return data ? JSON.parse(data) as T : null
}

/**
 * 用途：执行readErrorResponse相关业务逻辑。
 * @param response 调用方传入的response参数，用于驱动当前前端逻辑。
 * @param fallback 调用方传入的fallback参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
export async function readErrorResponse(response: Response, fallback = '请求失败') {
  const text = await response.text()
  if (!text) {
    return `${fallback}：${response.status}`
  }
  try {
    const data = JSON.parse(text) as { detail?: unknown; message?: string }
    if (typeof data.detail === 'string') {
      return data.detail
    }
    return data.message || text
  } catch {
    return text
  }
}

/**
 * 用途：执行authHeaders相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function authHeaders(base?: HeadersInit) {
  const headers = new Headers(base)
  const token = getJwtToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  return headers
}

/**
 * 用途：执行ensureOk相关业务逻辑。
 * @param response 调用方传入的response参数，用于驱动当前前端逻辑。
 * @param fallback 调用方传入的fallback参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function ensureOk(response: Response, fallback: string) {
  if (response.status === 401) {
    clearAuthAndRedirect()
    throw new Error('登录已过期，请重新登录')
  }
  if (!response.ok) {
    throw new Error(await readErrorResponse(response, fallback))
  }
}

/**
 * 用途：执行postJsonStream相关业务逻辑。
 * @param url 调用方传入的url参数，用于驱动当前前端逻辑。
 * @param body 调用方传入的body参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
export async function postJsonStream(url: string, body: unknown) {
  const response = await fetch(url, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  })

  await ensureOk(response, '请求失败')
  return response
}

export async function uploadFormSse<T extends StreamEvent>(
  url: string,
  formData: FormData,
  onProgress?: (event: T) => void,
): Promise<StreamResult<T>> {
  const response = await fetch(url, {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  })

  await ensureOk(response, '上传失败')

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('浏览器无法读取上传进度流')
  }

  const decoder = new TextDecoder()
  let buffer = ''
  const result: StreamResult<T> = { finalEvent: null, lastError: '' }

  const consumeBuffer = (flush = false) => {
    const parts = buffer.split(/\r?\n\r?\n/)
    buffer = flush ? '' : parts.pop() || ''

    for (const block of parts) {
      const event = parseSseBlock<T>(block)
      if (!event) continue
      result.finalEvent = event
      if (event.event_type === 'error') {
        result.lastError = event.error_message || event.message || result.lastError
      }
      onProgress?.(event)
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    consumeBuffer()
  }

  buffer += decoder.decode()
  consumeBuffer(true)

  if (!result.finalEvent) {
    throw new Error('上传进度流中断，请重试')
  }
  if (result.finalEvent.event_type !== 'finish') {
    throw new Error(result.lastError || result.finalEvent.message || '上传处理未完成，请重试')
  }

  return result
}
