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

type GenderValue = 1 | 2 | ''

interface ProfileForm {
  username: string
  email: string
  phone: string
  gender: string
  bio: string
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
  bio: '',
})

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

function syncForm(payload: UserInfo | null) {
  if (!payload) {
    return
  }
  form.value = {
    username: payload.username || '',
    email: payload.email || '',
    phone: payload.phone || payload.telephone || '',
    gender: payload.gender ? String(payload.gender) : '',
    bio: payload.bio || '',
  }
}

function genderText(value: string) {
  if (value === '1') return '男'
  if (value === '2') return '女'
  return '-'
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

  saving.value = true
  try {
    const payload: Record<string, unknown> = {
      username: form.value.username.trim() || undefined,
      telephone: form.value.phone.trim() || undefined,
      gender: form.value.gender ? (Number(form.value.gender) as GenderValue | number) : undefined,
      bio: form.value.bio.trim() || undefined,
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
  } catch {
    setMessage('保存失败，请稍后重试', 'error')
  } finally {
    saving.value = false
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
            :disabled="saving"
            @click="saveProfile"
          >
            <Save :size="14" />
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </template>
      </div>
    </div>

    <p v-if="message" class="rounded-md px-4 py-2 text-sm" :class="{
      'bg-[var(--color-success-bg)] text-[var(--color-success)]': messageType === 'success',
      'bg-[var(--color-danger-bg)] text-[var(--color-danger)]': messageType === 'error',
    }">
      {{ message }}
    </p>

    <div v-if="loading" class="rounded-md border border-[var(--color-border)] bg-[var(--color-card)] p-6 text-sm text-[var(--color-text-secondary)]">
      加载中...
    </div>

    <template v-else>
      <div class="space-y-6 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] divide-y divide-[var(--color-divider)]">
        <div class="flex items-center gap-4 p-6">
          <div class="relative flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-accent-bg)] text-xl font-medium text-[var(--color-accent)]">
            <span>{{ avatarText }}</span>
            <div v-if="editing" class="absolute inset-0 flex items-center justify-center rounded-full bg-black/30">
              <Camera :size="16" />
            </div>
          </div>
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
          <span class="text-[var(--color-text)]">{{ form.email || '-' }}</span>
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
          <div v-if="editing" class="flex gap-4">
            <label class="flex items-center gap-1.5 cursor-pointer">
              <input type="radio" value="1" v-model="form.gender" />
              <span class="text-[var(--color-text)]">男</span>
            </label>
            <label class="flex items-center gap-1.5 cursor-pointer">
              <input type="radio" value="2" v-model="form.gender" />
              <span class="text-[var(--color-text)]">女</span>
            </label>
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
                :type="showPwd.old ? 'text' : 'password'"
                v-model="oldPassword"
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
                :type="showPwd.new ? 'text' : 'password'"
                v-model="newPassword"
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
                :type="showPwd.confirm ? 'text' : 'password'"
                v-model="confirmPassword"
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
            <Lock :size="14" v-if="!pwdLoading" />
            <span>{{ pwdLoading ? '处理中...' : '确认修改' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
