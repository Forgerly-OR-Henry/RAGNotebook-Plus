/**
 * 模块职责：前端 API 模块，负责封装 HTTP/SSE 请求并保持视图层调用简洁。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
export function readJsonPref<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) as T : fallback
  } catch {
    return fallback
  }
}

/**
 * 用途：执行writeJsonPref相关业务逻辑。
 * @param key 调用方传入的key参数，用于驱动当前前端逻辑。
 * @param value 调用方传入的value参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
export function writeJsonPref(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Local preferences are best-effort only.
  }
}

/**
 * 用途：执行removePref相关业务逻辑。
 * @param key 调用方传入的key参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
export function removePref(key: string) {
  localStorage.removeItem(key)
}
