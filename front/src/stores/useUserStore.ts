import { defineStore } from 'pinia'
import { clearAuthState, getJwtToken, setAuthState, USER_INFO_KEY, JWT_KEY } from '../api/authToken'
import type { UserInfo } from '../types/api'

const storedUser = localStorage.getItem(USER_INFO_KEY)

export const useUserStore = defineStore('user', {
  state: () => ({
    userInfo: storedUser ? (JSON.parse(storedUser) as UserInfo) : null,
    token: getJwtToken() || '',
    userBio: '',
  }),
  getters: {
    isLogin: (state) => Boolean(state.token),
  },
  actions: {
    login(token: string, user: UserInfo) {
      setAuthState(token, user)
      this.token = token
      this.userInfo = user
    },
    logout() {
      clearAuthState()
      this.token = ''
      this.userInfo = null
      this.userBio = ''
    },
    setUserInfo(info: UserInfo) {
      localStorage.setItem(USER_INFO_KEY, JSON.stringify(info))
      this.userInfo = info
    },
    setToken(token: string) {
      localStorage.setItem(JWT_KEY, token)
      this.token = token
    },
    setUserBio(bio: string) {
      this.userBio = bio
    },
  },
})
