/**
 * 模块职责：前端 API 模块，负责封装 HTTP/SSE 请求并保持视图层调用简洁。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
import client from './client'
import { endpoints } from './endpoints'
import type { UserInfo } from '../types/api'

// Actual Django backend response shapes (not wrapped in ApiResponse)
/**
 * 接口：`LoginResponseData` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface LoginResponseData {
  message: string
  user: UserInfo
  token: string
}

/**
 * 接口：`RegisterResponseData` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface RegisterResponseData {
  status: number
  message: string
  user: UserInfo
  token: string
}

/**
 * 接口：`ProfileResponseData` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface ProfileResponseData {
  success: boolean
  message: string
  data: UserInfo
}

/**
 * 接口：`ActionResponseData` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface ActionResponseData {
  message: string
  user?: UserInfo
  token?: string
}

/**
 * 接口：`AvatarUploadResponseData` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface AvatarUploadResponseData {
  success: boolean
  data: {
    url: string
    alt?: string
    href?: string
  }
}

export const authApi = {
  login: async (username: string, password: string) => {
    const res = await client.post<LoginResponseData>(endpoints.login, { username, password })
    return res.data
  },

  register: async (data: { username: string; password: string; email: string; telephone?: string; confirm_password: string }) => {
    const res = await client.post<RegisterResponseData>(endpoints.register, data)
    return res.data
  },

  logout: async () => {
    const res = await client.post<ActionResponseData>(endpoints.logout)
    return res.data
  },

  getProfile: async () => {
    const res = await client.get<ProfileResponseData>(endpoints.profile)
    return res.data
  },

  updateProfile: async (data: Record<string, unknown>) => {
    const res = await client.put<ActionResponseData>(endpoints.userUpdate, data)
    return res.data
  },

  uploadAvatar: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await client.post<AvatarUploadResponseData>(endpoints.uploadFile, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  updatePassword: async (oldPassword: string, newPassword: string) => {
    const res = await client.post<ActionResponseData>(endpoints.changePassword, {
      old_password: oldPassword,
      new_password: newPassword,
      confirm_password: newPassword,
    })
    return res.data
  },
}
