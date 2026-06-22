<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { Plus, Tag, Trash2, Upload } from '@lucide/vue'
import { notesApi } from '../api/notes'
import type { Note } from '../types/api'

type ApiError = {
  message?: string
  response?: {
    data?: {
      detail?: unknown
      message?: string
    }
  }
}

const router = useRouter()
const notes = ref<Note[]>([])
const loading = ref(false)
const importing = ref(false)
const deletingId = ref<string | null>(null)
const query = ref('')
const selectedCategory = ref('')
const categoryOptions = ref<{ category: string; count: number }[]>([])
const importError = ref('')
const actionError = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const preferredCategoryOrder = ['工作', '学习', '生活', '技术', '其他']

const hasCategoryFilters = computed(() => categoryOptions.value.length > 0)

async function load() {
  loading.value = true
  try {
    const searchText = query.value.trim()
    const category = selectedCategory.value || undefined
    const res = searchText
      ? await notesApi.search(searchText)
      : await notesApi.list({ page: 1, page_size: 30, category })

    notes.value = searchText && category
      ? res.data.notes.filter((note) => note.category === category)
      : res.data.notes
  } finally {
    loading.value = false
  }
}

async function loadCategories() {
  const res = await notesApi.stats()
  categoryOptions.value = res.data.categories
    .filter((item) => item.category)
    .sort((a, b) => {
      const aIndex = preferredCategoryOrder.indexOf(a.category)
      const bIndex = preferredCategoryOrder.indexOf(b.category)
      if (aIndex !== -1 || bIndex !== -1) {
        return (aIndex === -1 ? preferredCategoryOrder.length : aIndex) - (bIndex === -1 ? preferredCategoryOrder.length : bIndex)
      }
      return a.category.localeCompare(b.category, 'zh-Hans-CN')
    })

  if (selectedCategory.value && !categoryOptions.value.some((item) => item.category === selectedCategory.value)) {
    selectedCategory.value = ''
  }
}

async function selectCategory(category: string) {
  selectedCategory.value = category
  await load()
}

function openImportPicker() {
  if (!importing.value) {
    fileInput.value?.click()
  }
}

function getImportErrorMessage(error: unknown) {
  const apiError = error as ApiError
  const detail = apiError.response?.data?.detail
  if (typeof detail === 'string') {
    return detail
  }
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message?: unknown }).message)
  }
  return apiError.response?.data?.message || apiError.message || '导入失败，请确认文件格式和内容后重试'
}

function getDeleteErrorMessage(error: unknown) {
  const apiError = error as ApiError
  const detail = apiError.response?.data?.detail
  if (typeof detail === 'string') {
    return detail
  }
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message?: unknown }).message)
  }
  return apiError.response?.data?.message || apiError.message || '删除失败，请稍后重试'
}

async function importSelectedFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) {
    return
  }

  importing.value = true
  importError.value = ''
  try {
    const res = await notesApi.importFile(file)
    await router.push(`/notes/${res.data.id}`)
  } catch (error) {
    importError.value = getImportErrorMessage(error)
  } finally {
    importing.value = false
    input.value = ''
  }
}

async function deleteNote(note: Note) {
  if (deletingId.value) return

  const confirmed = window.confirm(`确认删除「${note.title || '未命名笔记'}」？删除后无法恢复。`)
  if (!confirmed) {
    return
  }

  deletingId.value = note.id
  actionError.value = ''
  try {
    await notesApi.delete(note.id)
    await loadCategories()
    await load()
  } catch (error) {
    actionError.value = getDeleteErrorMessage(error)
  } finally {
    deletingId.value = null
  }
}

onMounted(() => {
  void loadCategories()
  void load()
})
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center gap-3">
      <input
        v-model="query"
        class="h-10 min-w-64 flex-1 rounded-md border border-[var(--color-border)] bg-[var(--color-card)] px-3"
        placeholder="搜索笔记"
        @keydown.enter="load"
      />
      <button class="rounded-md border border-[var(--color-border)] px-4 py-2" @click="load">搜索</button>
      <div class="flex h-10 shrink-0 overflow-hidden rounded-md border border-[var(--color-accent)]">
        <RouterLink class="inline-flex items-center gap-2 bg-[var(--color-accent)] px-3 text-sm font-medium text-white" to="/notes/new">
          <Plus :size="16" />
          新建
        </RouterLink>
        <button
          class="inline-flex items-center gap-2 border-l border-white/30 bg-[var(--color-accent)] px-3 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
          type="button"
          :disabled="importing"
          @click="openImportPicker"
        >
          <Upload :size="16" />
          {{ importing ? '导入中' : '导入' }}
        </button>
      </div>
      <input
        ref="fileInput"
        class="sr-only"
        type="file"
        accept=".md,.markdown,.txt,.doc,.docx,text/markdown,text/plain,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        @change="importSelectedFile"
      />
    </div>
    <p v-if="importError" class="text-sm text-[var(--color-danger)]">{{ importError }}</p>
    <p v-if="actionError" class="text-sm text-[var(--color-danger)]">{{ actionError }}</p>

    <div v-if="hasCategoryFilters" class="flex flex-wrap gap-2">
      <button
        class="rounded-md px-4 py-2 text-sm transition-colors"
        :class="selectedCategory === '' ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'"
        type="button"
        @click="selectCategory('')"
      >
        全部
      </button>
      <button
        v-for="item in categoryOptions"
        :key="item.category"
        class="rounded-md px-4 py-2 text-sm transition-colors"
        :class="selectedCategory === item.category ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'"
        type="button"
        @click="selectCategory(item.category)"
      >
        {{ item.category }}
      </button>
    </div>

    <div v-if="loading" class="text-sm text-[var(--color-text-secondary)]">加载中</div>
    <div v-else class="grid gap-3">
      <article
        v-for="note in notes"
        :key="note.id"
        class="rounded-md border border-[var(--color-border)] bg-[var(--color-card)] p-4 hover:border-[var(--color-accent)]"
      >
        <div class="flex items-center justify-between gap-3">
          <RouterLink :to="`/notes/${note.id}`" class="min-w-0 flex-1">
            <h2 class="truncate font-medium">{{ note.title }}</h2>
          </RouterLink>
          <div class="flex shrink-0 items-center gap-2">
            <button
              class="inline-flex h-8 w-8 items-center justify-center rounded-md text-[var(--color-text-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger)] disabled:cursor-not-allowed disabled:opacity-50"
              type="button"
              :disabled="deletingId === note.id"
              aria-label="删除笔记"
              title="删除笔记"
              @click.stop="deleteNote(note)"
            >
              <Trash2 :size="16" />
            </button>
          </div>
        </div>
        <RouterLink :to="`/notes/${note.id}`" class="mt-2 block">
          <p class="line-clamp-2 text-sm text-[var(--color-text-secondary)]">{{ note.content }}</p>
        </RouterLink>
        <div class="mt-3 flex flex-wrap items-center gap-2">
          <span
            v-for="tag in note.tags || []"
            :key="tag"
            class="rounded-full bg-[var(--color-accent-bg)] px-3 py-0.5 text-sm font-medium text-[var(--color-accent)]"
          >
            {{ tag }}
          </span>
          <span class="inline-flex items-center gap-1 text-sm text-[var(--color-text-tertiary)]">
            <Tag :size="14" />
            {{ note.category || '未分类' }}
          </span>
        </div>
      </article>
    </div>
  </div>
</template>
