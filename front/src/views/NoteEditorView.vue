<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Trash2 } from '@lucide/vue'
import RichEditor from '../components/RichEditor.vue'
import { notesApi } from '../api/notes'

type ApiError = {
  message?: string
  response?: {
    data?: {
      detail?: unknown
      message?: string
    }
  }
}

const route = useRoute()
const router = useRouter()
const noteId = route.params.id as string | undefined
const isNew = !noteId
const title = ref('')
const content = ref('')
const category = ref('')
const saving = ref(false)
const deleting = ref(false)
const message = ref('')
const errorMessage = ref('')

async function load() {
  if (!noteId) return
  const res = await notesApi.get(noteId)
  title.value = res.data.title
  content.value = res.data.content
  category.value = res.data.category || ''
}

function getApiErrorMessage(error: unknown, fallbackMessage: string) {
  const apiError = error as ApiError
  const detail = apiError.response?.data?.detail
  if (typeof detail === 'string') {
    return detail
  }
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message?: unknown }).message)
  }
  return apiError.response?.data?.message || apiError.message || fallbackMessage
}

async function save() {
  if (saving.value || deleting.value) return

  saving.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    if (isNew) {
      const res = await notesApi.create({ title: title.value || '未命名笔记', content: content.value, category: category.value })
      router.replace(`/notes/${res.data.id}`)
    } else if (noteId) {
      await notesApi.update(noteId, { title: title.value, content: content.value, category: category.value })
      message.value = '已保存'
    }
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '保存失败，请稍后重试')
  } finally {
    saving.value = false
  }
}

async function deleteCurrentNote() {
  if (!noteId || deleting.value || saving.value) return

  const confirmed = window.confirm(`确认删除「${title.value || '未命名笔记'}」？删除后无法恢复。`)
  if (!confirmed) {
    return
  }

  deleting.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    await notesApi.delete(noteId)
    await router.replace('/notes')
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '删除失败，请稍后重试')
  } finally {
    deleting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-4">
    <div class="flex items-center gap-3">
      <input v-model="title" class="h-11 flex-1 bg-transparent font-heading text-2xl font-semibold outline-none" placeholder="未命名笔记" />
      <input v-model="category" class="h-10 w-36 rounded-md border border-[var(--color-border)] bg-[var(--color-card)] px-3" placeholder="分类" />
      <button class="rounded-md bg-[var(--color-accent)] px-4 py-2 text-white disabled:opacity-60" :disabled="saving || deleting" @click="save">
        {{ saving ? '保存中' : '保存' }}
      </button>
      <button
        v-if="!isNew"
        class="inline-flex h-10 items-center gap-2 rounded-md border border-[var(--color-border)] px-3 text-sm text-[var(--color-danger)] hover:bg-[var(--color-danger-bg)] disabled:cursor-not-allowed disabled:opacity-50"
        type="button"
        :disabled="saving || deleting"
        @click="deleteCurrentNote"
      >
        <Trash2 :size="16" />
        {{ deleting ? '删除中' : '删除' }}
      </button>
    </div>
    <p v-if="message" class="text-sm text-[var(--color-success)]">{{ message }}</p>
    <p v-if="errorMessage" class="text-sm text-[var(--color-danger)]">{{ errorMessage }}</p>
    <RichEditor v-model="content" />
  </div>
</template>
