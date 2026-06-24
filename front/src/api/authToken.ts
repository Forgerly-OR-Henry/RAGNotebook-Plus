/**
 * 模块职责：前端 API 模块，负责封装 HTTP/SSE 请求并保持视图层调用简洁。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
export const JWT_KEY = 'jwt_token'
export const USER_INFO_KEY = 'user_info'

/**
 * 用途：执行getJwtToken相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
export function getJwtToken() {
  return localStorage.getItem(JWT_KEY)
}

/**
 * 用途：执行setAuthState相关业务逻辑。
 * @param token 调用方传入的token参数，用于驱动当前前端逻辑。
 * @param user 调用方传入的user参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
export function setAuthState(token: string, user: unknown) {
  localStorage.setItem(JWT_KEY, token)
  localStorage.setItem(USER_INFO_KEY, JSON.stringify(user))
}

/**
 * 用途：执行clearAuthState相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
export function clearAuthState() {
  localStorage.removeItem(JWT_KEY)
  localStorage.removeItem(USER_INFO_KEY)
}

/**
 * 用途：执行redirectToLogin相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
export function redirectToLogin() {
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

/**
 * 用途：执行clearAuthAndRedirect相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
export function clearAuthAndRedirect() {
  clearAuthState()
  redirectToLogin()
}
