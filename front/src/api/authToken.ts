export const JWT_KEY = 'jwt_token'
export const USER_INFO_KEY = 'user_info'

export function getJwtToken() {
  return localStorage.getItem(JWT_KEY)
}

export function setAuthState(token: string, user: unknown) {
  localStorage.setItem(JWT_KEY, token)
  localStorage.setItem(USER_INFO_KEY, JSON.stringify(user))
}

export function clearAuthState() {
  localStorage.removeItem(JWT_KEY)
  localStorage.removeItem(USER_INFO_KEY)
}

export function redirectToLogin() {
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

export function clearAuthAndRedirect() {
  clearAuthState()
  redirectToLogin()
}
