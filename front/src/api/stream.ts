import { clearAuthAndRedirect, getJwtToken } from './authToken'

export interface StreamEvent {
  event_type?: string
  error_message?: string
  message?: string
}

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

function authHeaders(base?: HeadersInit) {
  const headers = new Headers(base)
  const token = getJwtToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  return headers
}

async function ensureOk(response: Response, fallback: string) {
  if (response.status === 401) {
    clearAuthAndRedirect()
    throw new Error('登录已过期，请重新登录')
  }
  if (!response.ok) {
    throw new Error(await readErrorResponse(response, fallback))
  }
}

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
