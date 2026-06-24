<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  Camera,
  Eye,
  EyeOff,
  Lock,
  Save,
  X,
} from '@lucide/vue'
import { authApi } from '../api/auth'
import { useUserStore } from '../stores/useUserStore'
import type { UserInfo } from '../types/api'

interface ProfileForm {
  username: string
  email: string
  phone: string
  gender: string
  genderOption: string
  genderCustom: string
  bio: string
  avatar: string
}

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')
const editing = ref(false)
const profile = ref<UserInfo | null>(null)
const form = ref<ProfileForm>({
  username: '',
  email: '',
  phone: '',
  gender: '',
  genderOption: '',
  genderCustom: '',
  bio: '',
  avatar: '',
})
const avatarInput = ref<HTMLInputElement | null>(null)
const avatarUploading = ref(false)
const avatarLoadFailed = ref(false)

const pwdOpen = ref(false)
const pwdLoading = ref(false)
const pwdError = ref('')
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const showPwd = ref({
  old: false,
  new: false,
  confirm: false,
})

let messageTimer: ReturnType<typeof setTimeout> | null = null

function setMessage(text: string, type: 'success' | 'error' = 'success') {
  message.value = text
  messageType.value = type
  if (messageTimer) {
    clearTimeout(messageTimer)
  }
  messageTimer = setTimeout(() => {
    message.value = ''
  }, 2200)
}

const avatarText = computed(() => {
  const name = (form.value.username || profile.value?.username || 'U').trim()
  return name ? name[0].toUpperCase() : 'U'
})

const avatarUrl = computed(() => {
  if (avatarLoadFailed.value) return ''
  return form.value.avatar.trim()
})

function getErrorMessage(err: unknown, fallback: string) {
  const detail = (err as { response?: { data?: { detail?: string | { [key: string]: string } } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object') {
    const first = Object.values(detail)[0]
    if (typeof first === 'string') return first
  }
  return fallback
}

function normalizeGender(value: UserInfo['gender']) {
  if (value === 1 || value === '1') return 'male'
  if (value === 2 || value === '2') return 'female'
  if (typeof value !== 'string') return ''

  const normalized = value.trim()
  if (normalized === '男') return 'male'
  if (normalized === '女') return 'female'
  return normalized
}

function genderOptionFor(value: string) {
  if (value === 'male' || value === 'female') return value
  return value ? 'custom' : ''
}

function syncForm(payload: UserInfo | null) {
  if (!payload) {
    return
  }
  const gender = normalizeGender(payload.gender)
  avatarLoadFailed.value = false
  form.value = {
    username: payload.username || '',
    email: payload.email || '',
    phone: payload.phone || payload.telephone || '',
    gender,
    genderOption: genderOptionFor(gender),
    genderCustom: genderOptionFor(gender) === 'custom' ? gender : '',
    bio: payload.bio || '',
    avatar: payload.avatar || '',
  }
}

function genderText(value: string) {
  if (value === 'male') return '男'
  if (value === 'female') return '女'
  return value.trim() || '-'
}

async function loadProfile() {
  loading.value = true
  try {
    const res = await authApi.getProfile()
    profile.value = res.data
    userStore.setUserInfo(res.data)
    syncForm(res.data)
  } catch {
    profile.value = userStore.userInfo
    syncForm(userStore.userInfo)
    setMessage('用户信息加载失败，请稍后重试', 'error')
  } finally {
    loading.value = false
  }
}

function enterEdit() {
  syncForm(profile.value)
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  syncForm(profile.value)
}

async function saveProfile() {
  if (!form.value.username.trim()) {
    setMessage('用户名不能为空', 'error')
    return
  }
  if (!form.value.email.trim()) {
    setMessage('邮箱不能为空', 'error')
    return
  }
  if (form.value.genderOption === 'custom' && !form.value.genderCustom.trim()) {
    setMessage('请填写自定义性别', 'error')
    return
  }

  saving.value = true
  try {
    const gender = form.value.genderOption === 'custom'
      ? form.value.genderCustom.trim()
      : form.value.genderOption
    const payload: Record<string, unknown> = {
      username: form.value.username.trim() || undefined,
      email: form.value.email.trim(),
      telephone: form.value.phone.trim() || undefined,
      gender: gender || undefined,
      bio: form.value.bio.trim() || undefined,
      avatar: form.value.avatar.trim() || undefined,
    }
    const res = await authApi.updateProfile(payload)
    const next = res.user
    if (next) {
      userStore.setUserInfo(next)
      profile.value = next
      syncForm(next)
    }
    if (res.token) {
      userStore.setToken(res.token)
    }
    editing.value = false
    setMessage('账号资料更新成功')
  } catch (err: unknown) {
    setMessage(getErrorMessage(err, '保存失败，请稍后重试'), 'error')
  } finally {
    saving.value = false
  }
}

function openAvatarPicker() {
  if (!editing.value || avatarUploading.value) return
  avatarInput.value?.click()
}

function handleAvatarError() {
  avatarLoadFailed.value = true
}

async function handleAvatarChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  if (!file.type.startsWith('image/')) {
    setMessage('请选择图片文件', 'error')
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    setMessage('头像图片不能超过 5MB', 'error')
    return
  }

  avatarUploading.value = true
  try {
    const res = await authApi.uploadAvatar(file)
    const nextAvatar = res.data.url
    if (!nextAvatar) {
      throw new Error('missing avatar url')
    }
    form.value.avatar = nextAvatar
    avatarLoadFailed.value = false
    if (profile.value) {
      profile.value = { ...profile.value, avatar: nextAvatar }
    }
    if (userStore.userInfo) {
      userStore.setUserInfo({ ...userStore.userInfo, avatar: nextAvatar })
    }
    setMessage('头像更新成功')
  } catch (err: unknown) {
    setMessage(getErrorMessage(err, '头像上传失败，请稍后重试'), 'error')
  } finally {
    avatarUploading.value = false
  }
}

function openPasswordDialog() {
  pwdOpen.value = true
  pwdError.value = ''
  oldPassword.value = ''
  newPassword.value = ''
  confirmPassword.value = ''
  showPwd.value = { old: false, new: false, confirm: false }
}

function closePasswordDialog() {
  pwdOpen.value = false
}

async function changePassword() {
  if (!oldPassword.value || !newPassword.value || !confirmPassword.value) {
    pwdError.value = '请填写所有字段'
    return
  }
  if (newPassword.value.length < 6) {
    pwdError.value = '新密码长度至少6位'
    return
  }
  if (oldPassword.value === newPassword.value) {
    pwdError.value = '新密码不能与原密码相同'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    pwdError.value = '两次输入的新密码不一致'
    return
  }

  pwdLoading.value = true
  try {
    await authApi.updatePassword(oldPassword.value, newPassword.value)
    closePasswordDialog()
    setMessage('密码修改成功')
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string | { [key: string]: string } } } })?.response?.data?.detail
    if (typeof detail === 'string') {
      pwdError.value = detail
    } else if (detail && typeof detail === 'object') {
      const first = Object.values(detail)[0]
      pwdError.value = typeof first === 'string' ? first : '密码修改失败，请检查输入'
    } else {
      pwdError.value = '密码修改失败，请检查原密码是否正确'
    }
  } finally {
    pwdLoading.value = false
  }
}

onMounted(() => {
  profile.value = userStore.userInfo
  syncForm(userStore.userInfo)
  void loadProfile()
})
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="font-heading text-xl font-semibold">账号资料</h1>
      <div class="flex gap-2">
        <button
          v-if="!editing"
          type="button"
          class="rounded-md border border-[var(--color-border)] px-4 py-2 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]"
          @click="enterEdit"
        >
          编辑
        </button>
        <template v-else>
          <button
            type="button"
            class="rounded-md border border-[var(--color-border)] px-4 py-2 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]"
            :disabled="saving"
            @click="cancelEdit"
          >
            取消
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-1.5 rounded-md bg-[var(--color-accent)] px-4 py-2 text-sm text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="saving || avatarUploading"
            @click="saveProfile"
          >
            <Save :size="14" />
            {{ avatarUploading ? '上传中...' : saving ? '保存中...' : '保存' }}
          </button>
        </template>
      </div>
    </div>

    <p
      v-if="message" class="rounded-md px-4 py-2 text-sm" :class="{
        'bg-[var(--color-success-bg)] text-[var(--color-success)]': messageType === 'success',
        'bg-[var(--color-danger-bg)] text-[var(--color-danger)]': messageType === 'error',
      }"
    >
      {{ message }}
    </p>

    <div v-if="loading" class="rounded-md border border-[var(--color-border)] bg-[var(--color-card)] p-6 text-sm text-[var(--color-text-secondary)]">
      加载中...
    </div>

    <template v-else>
      <div class="space-y-6 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] divide-y divide-[var(--color-divider)]">
        <div class="flex items-center gap-4 p-6">
          <button
            type="button"
            class="relative flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[var(--color-accent-bg)] text-xl font-medium text-[var(--color-accent)] outline-none transition-opacity"
            :class="editing ? 'cursor-pointer hover:opacity-90' : 'cursor-default'"
            title="更换头像"
            @click="openAvatarPicker"
          >
            <img
              v-if="avatarUrl"
              :src="avatarUrl"
              alt="用户头像"
              class="h-full w-full object-cover"
              @error="handleAvatarError"
            />
            <span v-else>{{ avatarText }}</span>
            <div
              v-if="editing"
              class="absolute inset-0 flex items-center justify-center rounded-full bg-black/35 text-white"
              :class="{ 'animate-pulse': avatarUploading }"
            >
              <Camera :size="16" />
            </div>
          </button>
          <input
            ref="avatarInput"
            type="file"
            accept="image/*"
            class="hidden"
            @change="handleAvatarChange"
          />
          <div>
            <p class="text-sm font-medium text-[var(--color-text)]">{{ form.username || '-' }}</p>
            <p class="text-xs text-[var(--color-text-secondary)]">{{ form.email || '-' }}</p>
          </div>
        </div>

        <div class="flex items-center justify-between px-6 py-4 text-sm">
          <span class="text-[var(--color-text-secondary)]">用户名</span>
          <input
            v-if="editing"
            v-model="form.username"
            type="text"
            class="w-56 rounded-md border border-[var(--color-border)] bg-transparent px-3 py-1.5 text-[var(--color-text)] outline-none"
          />
          <span v-else class="text-[var(--color-text)]">{{ form.username || '-' }}</span>
        </div>

        <div class="flex items-center justify-between px-6 py-4 text-sm">
          <span class="text-[var(--color-text-secondary)]">邮箱</span>
          <input
            v-if="editing"
            v-model="form.email"
            type="email"
            class="w-56 rounded-md border border-[var(--color-border)] bg-transparent px-3 py-1.5 text-[var(--color-text)] outline-none"
          />
          <span v-else class="text-[var(--color-text)]">{{ form.email || '-' }}</span>
        </div>

        <div class="flex items-center justify-between px-6 py-4 text-sm">
          <span class="text-[var(--color-text-secondary)]">手机号</span>
          <input
            v-if="editing"
            v-model="form.phone"
            type="tel"
            class="w-56 rounded-md border border-[var(--color-border)] bg-transparent px-3 py-1.5 text-[var(--color-text)] outline-none"
          />
          <span v-else class="text-[var(--color-text)]">{{ form.phone || '-' }}</span>
        </div>

        <div class="flex items-center justify-between px-6 py-4 text-sm">
          <span class="text-[var(--color-text-secondary)]">性别</span>
          <div v-if="editing" class="flex max-w-md flex-wrap items-center justify-end gap-3">
            <label class="flex items-center gap-1.5 cursor-pointer">
              <input v-model="form.genderOption" type="radio" value="male" />
              <span class="text-[var(--color-text)]">男</span>
            </label>
            <label class="flex items-center gap-1.5 cursor-pointer">
              <input v-model="form.genderOption" type="radio" value="female" />
              <span class="text-[var(--color-text)]">女</span>
            </label>
            <label class="flex items-center gap-1.5 cursor-pointer">
              <input v-model="form.genderOption" type="radio" value="custom" />
              <span class="text-[var(--color-text)]">自定义</span>
            </label>
            <input
              v-if="form.genderOption === 'custom'"
              v-model="form.genderCustom"
              type="text"
              maxlength="50"
              placeholder="填写性别"
              class="h-9 w-32 rounded-md border border-[var(--color-border)] bg-transparent px-3 text-[var(--color-text)] outline-none"
            />
          </div>
          <span v-else class="text-[var(--color-text)]">{{ genderText(form.gender) }}</span>
        </div>

        <div class="flex items-center justify-between px-6 py-4 text-sm">
          <span class="text-[var(--color-text-secondary)]">个人简介</span>
          <textarea
            v-if="editing"
            v-model="form.bio"
            rows="3"
            class="w-56 resize-none rounded-md border border-[var(--color-border)] bg-transparent px-3 py-1.5 text-sm text-[var(--color-text)] outline-none"
          />
          <span v-else class="max-w-56 text-right text-sm text-[var(--color-text)]">
            {{ form.bio || '-' }}
          </span>
        </div>
      </div>

      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-md border border-[var(--color-border)] px-4 py-2 text-sm text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-secondary)]"
        @click="openPasswordDialog"
      >
        <Lock :size="14" />
        修改密码
      </button>
    </template>

    <div v-if="pwdOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div class="w-full max-w-md rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6">
        <div class="mb-5 flex items-center justify-between">
          <h2 class="text-base font-medium">修改密码</h2>
          <button type="button" class="text-[var(--color-text-tertiary)] hover:text-[var(--color-text)]" @click="closePasswordDialog">
            <X :size="16" />
          </button>
        </div>

        <p v-if="pwdError" class="mb-4 rounded-md bg-[var(--color-danger-bg)] px-4 py-2 text-sm text-[var(--color-danger)]">
          {{ pwdError }}
        </p>

        <div class="space-y-4">
          <div class="space-y-1.5">
            <label class="text-sm text-[var(--color-text-secondary)]">原密码</label>
            <div class="relative">
              <input
                v-model="oldPassword"
                :type="showPwd.old ? 'text' : 'password'"
                class="w-full rounded-md border border-[var(--color-border)] bg-transparent px-3 py-2 pr-10 text-sm text-[var(--color-text)] outline-none"
              />
              <button
                type="button"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]"
                @click="showPwd.old = !showPwd.old"
              >
                <Eye v-if="showPwd.old" :size="16" />
                <EyeOff v-else :size="16" />
              </button>
            </div>
          </div>

          <div class="space-y-1.5">
            <label class="text-sm text-[var(--color-text-secondary)]">新密码</label>
            <div class="relative">
              <input
                v-model="newPassword"
                :type="showPwd.new ? 'text' : 'password'"
                class="w-full rounded-md border border-[var(--color-border)] bg-transparent px-3 py-2 pr-10 text-sm text-[var(--color-text)] outline-none"
              />
              <button
                type="button"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]"
                @click="showPwd.new = !showPwd.new"
              >
                <Eye v-if="showPwd.new" :size="16" />
                <EyeOff v-else :size="16" />
              </button>
            </div>
          </div>

          <div class="space-y-1.5">
            <label class="text-sm text-[var(--color-text-secondary)]">确认新密码</label>
            <div class="relative">
              <input
                v-model="confirmPassword"
                :type="showPwd.confirm ? 'text' : 'password'"
                class="w-full rounded-md border border-[var(--color-border)] bg-transparent px-3 py-2 pr-10 text-sm text-[var(--color-text)] outline-none"
              />
              <button
                type="button"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]"
                @click="showPwd.confirm = !showPwd.confirm"
              >
                <Eye v-if="showPwd.confirm" :size="16" />
                <EyeOff v-else :size="16" />
              </button>
            </div>
          </div>
        </div>

        <div class="mt-6 flex justify-end gap-3">
          <button
            type="button"
            class="rounded-md border border-[var(--color-border)] px-4 py-2 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]"
            @click="closePasswordDialog"
          >
            取消
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-2 rounded-md bg-[var(--color-accent)] px-4 py-2 text-sm text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="pwdLoading"
            @click="changePassword"
          >
            <Lock v-if="!pwdLoading" :size="14" />
            <span>{{ pwdLoading ? '处理中...' : '确认修改' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
