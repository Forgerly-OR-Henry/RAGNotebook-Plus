<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { FileText, LoaderCircle, Trash2, Upload, X } from '@lucide/vue'
import { knowledgeApi } from '../api/knowledge'
import type { KnowledgeDocument, KnowledgeDocumentDetail } from '../types/api'

type ApiError = {
  message?: string
  response?: {
    data?: {
      detail?: unknown
      message?: string
    }
  }
}

const documents = ref<KnowledgeDocument[]>([])
const loading = ref(false)
const uploading = ref(false)
const dragging = ref(false)
const deletingKey = ref('')
const message = ref('')
const errorMessage = ref('')
const progressMessage = ref('')
const progressValue = ref(0)
const previewDocument = ref<KnowledgeDocument | null>(null)
const previewDetail = ref<KnowledgeDocumentDetail | null>(null)
const previewLoading = ref(false)
const previewError = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

const documentCount = computed(() => documents.value.length)
const acceptTypes = '.pdf,.txt,.md,.markdown,.doc,.docx,.ppt,.pptx,application/pdf,text/plain,text/markdown,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation'

function getErrorMessage(error: unknown, fallback: string) {
  const apiError = error as ApiError
  const detail = apiError.response?.data?.detail
  if (typeof detail === 'string') {
    return detail
  }
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message?: unknown }).message)
  }
  return apiError.response?.data?.message || apiError.message || fallback
}

function getDocumentTitle(doc: KnowledgeDocument) {
  return doc.original_filename || doc.filename
}

function formatDate(value?: string | null) {
  if (!value) {
    return ''
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return `${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

async function load() {
  loading.value = true
  try {
    const res = await knowledgeApi.list()
    documents.value = res.data.documents
  } finally {
    loading.value = false
  }
}

function openFilePicker() {
  if (!uploading.value) {
    fileInput.value?.click()
  }
}

async function uploadFiles(fileList: FileList | File[]) {
  const files = Array.from(fileList)
  if (!files.length || uploading.value) {
    return
  }

  uploading.value = true
  message.value = ''
  errorMessage.value = ''
  progressMessage.value = '正在上传文件...'
  progressValue.value = 0
  try {
    const result = await knowledgeApi.uploadStream(files, (event) => {
      progressValue.value = event.progress ?? progressValue.value
      progressMessage.value = event.filename ? `${event.filename}：${event.message || ''}` : event.message || progressMessage.value
      if (event.event_type === 'error') {
        errorMessage.value = event.error_message || event.message || '部分文档处理失败'
      }
    })
    const finalEvent = result.finalEvent
    const successCount = finalEvent?.success_count ?? files.length
    const failedCount = finalEvent?.failed_count ?? 0

    progressValue.value = finalEvent?.progress ?? 100
    message.value = failedCount > 0 ? `已完成 ${successCount} 个文档，失败 ${failedCount} 个` : `已上传 ${successCount} 个文档`
    if (failedCount > 0 && result.lastError) {
      errorMessage.value = result.lastError
    }
    await load()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '上传失败，请确认文件格式和大小后重试')
  } finally {
    uploading.value = false
    progressMessage.value = ''
  }
}

async function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files) {
    await uploadFiles(input.files)
  }
  input.value = ''
}

function handleDragOver(event: DragEvent) {
  event.preventDefault()
  dragging.value = true
}

function handleDragLeave(event: DragEvent) {
  event.preventDefault()
  dragging.value = false
}

async function handleDrop(event: DragEvent) {
  event.preventDefault()
  dragging.value = false
  if (event.dataTransfer?.files) {
    await uploadFiles(event.dataTransfer.files)
  }
}

async function deleteDocument(doc: KnowledgeDocument) {
  const filename = getDocumentTitle(doc)
  const confirmed = window.confirm(`确认删除「${filename}」？删除后会从知识库检索中移除。`)
  if (!confirmed) {
    return
  }

  deletingKey.value = doc.id
  message.value = ''
  errorMessage.value = ''
  try {
    await knowledgeApi.delete(doc.id)
    if (previewDocument.value?.id === doc.id) {
      closePreview()
    }
    await load()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '删除文档失败，请稍后重试')
  } finally {
    deletingKey.value = ''
  }
}

async function openPreview(doc: KnowledgeDocument) {
  previewDocument.value = doc
  previewDetail.value = null
  previewError.value = ''
  previewLoading.value = true
  try {
    const res = await knowledgeApi.detail(doc.id)
    previewDetail.value = res.data
  } catch (error) {
    previewError.value = getErrorMessage(error, '加载知识库内容失败，请稍后重试')
  } finally {
    previewLoading.value = false
  }
}

function closePreview() {
  previewDocument.value = null
  previewDetail.value = null
  previewError.value = ''
  previewLoading.value = false
}

async function cleanAll() {
  if (!documents.value.length) {
    return
  }
  const confirmed = window.confirm('确认清空所有知识库文档？清空后无法恢复。')
  if (!confirmed) {
    return
  }

  deletingKey.value = '__all__'
  message.value = ''
  errorMessage.value = ''
  try {
    await knowledgeApi.cleanAll()
    documents.value = []
    closePreview()
    message.value = '已清空知识库'
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '清空知识库失败，请稍后重试')
  } finally {
    deletingKey.value = ''
  }
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-8">
    <div class="flex items-center justify-between gap-4">
      <h2 class="font-heading text-2xl font-semibold">知识库管理</h2>
      <button
        class="inline-flex h-11 items-center gap-2 rounded-md border border-[var(--color-border)] px-4 text-sm text-[var(--color-danger)] hover:bg-[var(--color-danger-bg)] disabled:cursor-not-allowed disabled:opacity-50"
        type="button"
        :disabled="!documents.length || deletingKey === '__all__'"
        @click="cleanAll"
      >
        <Trash2 :size="17" />
        清空所有
      </button>
    </div>

    <section
      class="flex min-h-72 flex-col items-center justify-center rounded-lg border border-dashed border-[var(--color-border)] bg-[var(--color-card)] px-6 py-12 text-center transition-colors"
      :class="{ 'border-[var(--color-accent)] bg-[var(--color-accent-bg)]': dragging }"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
    >
      <Upload :size="34" class="text-[var(--color-text-tertiary)]" />
      <p class="mt-5 text-base text-[var(--color-text-secondary)]">拖拽文件到此处，或点击选择</p>
      <p class="mt-2 text-sm text-[var(--color-text-tertiary)]">支持 PDF、TXT、Markdown、Word、PPT 格式</p>
      <button
        class="mt-6 rounded-md bg-[var(--color-accent)] px-5 py-2.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
        type="button"
        :disabled="uploading"
        @click="openFilePicker"
      >
        {{ uploading ? '上传中' : '上传文档' }}
      </button>
      <input
        ref="fileInput"
        class="sr-only"
        type="file"
        multiple
        :accept="acceptTypes"
        @change="handleFileChange"
      />
    </section>

    <div class="space-y-2">
      <div v-if="uploading || progressMessage" class="space-y-2">
        <div class="h-2 overflow-hidden rounded-full bg-[var(--color-bg-secondary)]">
          <div
            class="h-full rounded-full bg-[var(--color-accent)] transition-all"
            :style="{ width: `${Math.max(4, Math.min(progressValue, 100))}%` }"
          />
        </div>
        <p class="text-sm text-[var(--color-text-secondary)]">{{ progressMessage || '正在处理文档...' }}</p>
      </div>
      <p v-if="message" class="text-sm text-[var(--color-success)]">{{ message }}</p>
      <p v-if="errorMessage" class="text-sm text-[var(--color-danger)]">{{ errorMessage }}</p>
    </div>

    <section class="space-y-4">
      <h3 class="font-heading text-lg font-semibold">知识库管理 ({{ documentCount }})</h3>
      <div v-if="loading" class="text-sm text-[var(--color-text-secondary)]">加载中</div>
      <div v-else-if="!documents.length" class="rounded-md border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-8 text-center text-sm text-[var(--color-text-secondary)]">
        暂无知识库文档
      </div>
      <div v-else class="space-y-3">
        <article
          v-for="doc in documents"
          :key="doc.id"
          class="flex items-center gap-3 rounded-md border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-4"
        >
          <button
            class="flex min-w-0 flex-1 items-center gap-3 text-left"
            type="button"
            @click="openPreview(doc)"
          >
            <FileText :size="22" class="shrink-0 text-[var(--color-text-tertiary)]" />
            <span class="min-w-0 flex-1">
              <span class="block truncate font-medium">{{ getDocumentTitle(doc) }}</span>
              <span class="mt-0.5 block text-sm text-[var(--color-text-secondary)]">
                {{ doc.chunk_count }} chunks<span v-if="doc.created_at"> | {{ formatDate(doc.created_at) }}</span>
              </span>
            </span>
          </button>
          <button
            class="inline-flex h-8 w-8 items-center justify-center rounded-md text-[var(--color-text-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger)] disabled:cursor-not-allowed disabled:opacity-50"
            type="button"
            :disabled="deletingKey === doc.id"
            aria-label="删除知识库文档"
            title="删除文档"
            @click="deleteDocument(doc)"
          >
            <Trash2 :size="16" />
          </button>
        </article>
      </div>
    </section>

    <div v-if="previewDocument" class="fixed inset-0 z-40 flex items-center justify-center bg-black/40 px-4 py-6">
      <section class="flex max-h-[86vh] w-full max-w-4xl flex-col rounded-lg bg-[var(--color-card)] shadow-xl">
        <header class="flex items-start justify-between gap-4 border-b border-[var(--color-border)] px-5 py-4">
          <div class="min-w-0">
            <h3 class="truncate font-heading text-lg font-semibold">{{ getDocumentTitle(previewDocument) }}</h3>
            <p class="mt-1 text-sm text-[var(--color-text-secondary)]">
              {{ previewDetail?.chunk_count ?? previewDocument.chunk_count }} chunks<span v-if="previewDocument.created_at"> | {{ formatDate(previewDocument.created_at) }}</span>
            </p>
          </div>
          <button
            class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]"
            type="button"
            aria-label="关闭预览"
            title="关闭"
            @click="closePreview"
          >
            <X :size="18" />
          </button>
        </header>

        <div class="min-h-0 flex-1 overflow-auto px-5 py-4">
          <div v-if="previewLoading" class="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
            <LoaderCircle :size="17" class="animate-spin" />
            正在加载内容
          </div>
          <p v-else-if="previewError" class="text-sm text-[var(--color-danger)]">{{ previewError }}</p>
          <div v-else-if="previewDetail?.chunks?.length" class="space-y-4">
            <article
              v-for="chunk in previewDetail.chunks"
              :key="chunk.chunk_id"
              class="rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-4"
            >
              <div class="mb-2 text-xs text-[var(--color-text-tertiary)]">
                片段 {{ chunk.index + 1 }}<span v-if="chunk.page"> | 第 {{ chunk.page }} 页</span>
              </div>
              <p class="whitespace-pre-wrap text-sm leading-6 text-[var(--color-text)]">{{ chunk.content }}</p>
            </article>
          </div>
          <p v-else class="text-sm text-[var(--color-text-secondary)]">暂无可预览内容</p>
        </div>
      </section>
    </div>
  </div>
</template>
