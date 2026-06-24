<!--
模块职责：知识文档预览组件，负责原文件加载、PDF/文本/Office 预览和分片内容切换。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { Download, Eye, FileText, LoaderCircle, X } from '@lucide/vue'
import { knowledgeApi } from '../api/knowledge'
import MarkdownRenderer from './MarkdownRenderer.vue'
import type { KnowledgeDocument, KnowledgeDocumentDetail } from '../types/api'

/**
 * 类型：`PreviewKind` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
type PreviewKind = 'pdf' | 'markdown' | 'text' | 'word' | 'presentation' | 'fallback'
/**
 * 类型：`PreviewTab` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
type PreviewTab = 'rendered' | 'chunks'

// 组件入参：由父组件传入业务对象、加载态和展示模式。
const props = defineProps<{
  document: KnowledgeDocument
  detail: KnowledgeDocumentDetail | null
  loading: boolean
  error: string
  mode?: 'modal' | 'page'
}>()

// 组件事件：向父组件报告关闭、保存、选择等交互结果。
const emit = defineEmits<{ close: [] }>()

const activeTab = ref<PreviewTab>('rendered')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const fileLoading = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const fileError = ref('')
const fileBlob = ref<Blob | null>(null)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const objectUrl = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const previewMimeType = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const originalText = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const downloading = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const downloadError = ref('')
let loadSerial = 0

const PDF_VIEWER_PARAMS = '#toolbar=0&navpanes=0&view=FitH'

/**
 * 用途：执行getDocumentTitle相关业务逻辑。
 * @param doc 调用方传入的doc参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function getDocumentTitle(doc: KnowledgeDocument) {
  return doc.original_filename || doc.filename
}

/**
 * 用途：执行getExtension相关业务逻辑。
 * @param doc 调用方传入的doc参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function getExtension(doc: KnowledgeDocument) {
  const explicitExt = doc.file_ext?.trim().toLowerCase()
  if (explicitExt) {
    return explicitExt.startsWith('.') ? explicitExt : `.${explicitExt}`
  }
  const name = getDocumentTitle(doc)
  const match = name.match(/\.[^.]+$/)
  return match?.[0].toLowerCase() || ''
}

/**
 * 用途：执行formatDate相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
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

/**
 * 用途：执行formatFileSize相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function formatFileSize(value?: number | null) {
  if (!value || value <= 0) {
    return ''
  }
  if (value < 1024) {
    return `${value} B`
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`
  }
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

/**
 * 用途：执行revokeObjectUrl相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function revokeObjectUrl() {
  if (objectUrl.value) {
    URL.revokeObjectURL(objectUrl.value)
    objectUrl.value = ''
  }
}

/**
 * 用途：执行resetFileState相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function resetFileState() {
  loadSerial += 1
  revokeObjectUrl()
  fileLoading.value = false
  fileError.value = ''
  downloadError.value = ''
  fileBlob.value = null
  previewMimeType.value = ''
  originalText.value = ''
}

/**
 * 用途：执行title相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const title = computed(() => getDocumentTitle(props.document))
/**
 * 用途：执行isPageMode相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const isPageMode = computed(() => props.mode === 'page')
/**
 * 用途：执行extension相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const extension = computed(() => getExtension(props.document))
/**
 * 用途：执行fileSize相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const fileSize = computed(() => formatFileSize(props.document.file_size))
/**
 * 用途：执行createdAt相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const createdAt = computed(() => formatDate(props.document.created_at))
/**
 * 用途：执行chunks相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const chunks = computed(() => props.detail?.chunks || [])

/**
 * 用途：执行previewKind相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const previewKind = computed<PreviewKind>(() => {
  const ext = extension.value
  if (ext === '.pdf' || props.document.mime_type === 'application/pdf') {
    return 'pdf'
  }
  if (ext === '.md' || ext === '.markdown' || props.document.mime_type === 'text/markdown') {
    return 'markdown'
  }
  if (ext === '.txt' || props.document.mime_type === 'text/plain') {
    return 'text'
  }
  if (ext === '.doc' || ext === '.docx') {
    return 'word'
  }
  if (ext === '.ppt' || ext === '.pptx') {
    return 'presentation'
  }
  return 'fallback'
})

/**
 * 用途：执行renderedLabel相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const renderedLabel = computed(() => {
  switch (previewKind.value) {
    case 'pdf':
      return 'PDF'
    case 'markdown':
      return 'Markdown'
    case 'text':
      return '文本'
    case 'word':
      return 'Word'
    case 'presentation':
      return 'PPT'
    default:
      return '预览'
  }
})

/**
 * 用途：执行canLoadRenderedPreview相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const canLoadRenderedPreview = computed(() => ['pdf', 'word', 'presentation'].includes(previewKind.value))
/**
 * 用途：执行canLoadOriginalText相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const canLoadOriginalText = computed(() => ['markdown', 'text'].includes(previewKind.value))
/**
 * 用途：执行isBusy相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const isBusy = computed(() => props.loading || fileLoading.value)
/**
 * 用途：执行blockingError相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const blockingError = computed(() => props.error)
/**
 * 用途：执行previewFrameSrc相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const previewFrameSrc = computed(() => {
  if (!objectUrl.value) {
    return ''
  }
  const isPdfPreview = previewKind.value === 'pdf' || previewMimeType.value.toLowerCase().includes('application/pdf')
  return isPdfPreview ? `${objectUrl.value}${PDF_VIEWER_PARAMS}` : objectUrl.value
})
/**
 * 用途：执行isMissingSourceFile相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const isMissingSourceFile = computed(() => /源文件.*丢失|原文件不存在/.test(fileError.value))
/**
 * 用途：执行renderedErrorMessage相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const renderedErrorMessage = computed(() => {
  if (!fileError.value) {
    return ''
  }
  if (isMissingSourceFile.value) {
    return fileError.value
  }
  if (canLoadOriginalText.value) {
    return `原文件读取失败：${fileError.value}`
  }
  return `${renderedLabel.value} 原样预览不可用：${fileError.value}`
})

/**
 * 用途：执行plainTextContent相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const plainTextContent = computed(() => originalText.value)

/**
 * 用途：执行createObjectUrl相关业务逻辑。
 * @param blob 调用方传入的blob参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function createObjectUrl(blob: Blob) {
  revokeObjectUrl()
  objectUrl.value = URL.createObjectURL(blob)
}

/**
 * 用途：执行readResponseMessage相关业务逻辑。
 * @param data 调用方传入的data参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function readResponseMessage(data: unknown): string {
  if (!data || typeof data !== 'object') {
    return typeof data === 'string' ? data : ''
  }
  const detail = (data as { detail?: unknown; message?: unknown }).detail
  const message = (data as { detail?: unknown; message?: unknown }).message
  if (typeof detail === 'string') {
    return detail
  }
  if (typeof message === 'string') {
    return message
  }
  return ''
}

/**
 * 用途：执行resolveErrorMessage相关业务逻辑。
 * @param error 调用方传入的error参数，用于驱动当前前端逻辑。
 * @param fallback 调用方传入的fallback参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function resolveErrorMessage(error: unknown, fallback: string) {
  const responseData = (error as { response?: { data?: unknown } })?.response?.data
  if (responseData instanceof Blob) {
    try {
      const text = await responseData.text()
      if (text.trim().startsWith('{')) {
        const parsed = JSON.parse(text) as unknown
        const message = readResponseMessage(parsed)
        if (message) {
          return message
        }
      }
      if (text.trim()) {
        return text.trim()
      }
    } catch {
      // Fall through to the generic error message below.
    }
  }

  const responseMessage = readResponseMessage(responseData)
  if (responseMessage) {
    return responseMessage
  }
  return error instanceof Error && error.message ? error.message : fallback
}

/**
 * 用途：执行loadRenderedPreview相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function loadRenderedPreview() {
  if (!canLoadRenderedPreview.value) {
    return
  }

  const serial = ++loadSerial
  fileLoading.value = true
  fileError.value = ''

  try {
    const response = await knowledgeApi.previewBlob(props.document.id)
    if (serial !== loadSerial) {
      return
    }
    previewMimeType.value = response.data.type || ''
    createObjectUrl(response.data)
  } catch (error) {
    if (serial !== loadSerial) {
      return
    }
    fileError.value = await resolveErrorMessage(error, '预览加载失败')
  } finally {
    if (serial === loadSerial) {
      fileLoading.value = false
    }
  }
}

/**
 * 用途：执行loadOriginalText相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function loadOriginalText() {
  if (!canLoadOriginalText.value) {
    return
  }

  const serial = ++loadSerial
  fileLoading.value = true
  fileError.value = ''

  try {
    const response = await knowledgeApi.fileBlob(props.document.id)
    if (serial !== loadSerial) {
      return
    }
    fileBlob.value = response.data
    originalText.value = await response.data.text()
  } catch (error) {
    if (serial !== loadSerial) {
      return
    }
    fileError.value = await resolveErrorMessage(error, '原文件加载失败')
  } finally {
    if (serial === loadSerial) {
      fileLoading.value = false
    }
  }
}

/**
 * 用途：执行downloadOriginal相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function downloadOriginal() {
  downloading.value = true
  downloadError.value = ''
  try {
    const blob = fileBlob.value || (await knowledgeApi.fileBlob(props.document.id)).data
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = title.value
    anchor.rel = 'noopener'
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (error) {
    downloadError.value = await resolveErrorMessage(error, '原文件下载失败')
  } finally {
    downloading.value = false
  }
}

/**
 * 用途：执行close相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function close() {
  emit('close')
}

// 状态监听：在关键输入变化后同步副作用或刷新页面数据。
watch(
  () => props.document.id,
  () => {
    activeTab.value = 'rendered'
    resetFileState()
    if (canLoadRenderedPreview.value) {
      void loadRenderedPreview()
    } else if (canLoadOriginalText.value) {
      void loadOriginalText()
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  resetFileState()
})
</script>

<template>
  <section class="knowledge-preview" :class="{ 'is-page': isPageMode }">
    <header class="knowledge-preview__header">
      <div class="min-w-0">
        <div class="knowledge-preview__title-row">
          <FileText :size="19" class="shrink-0 text-[var(--color-text-tertiary)]" />
          <h3 class="truncate font-heading text-lg font-semibold">{{ title }}</h3>
        </div>
        <p class="knowledge-preview__meta">
          {{ renderedLabel }}<span v-if="fileSize"> | {{ fileSize }}</span><span v-if="createdAt"> | {{ createdAt }}</span>
          <span v-if="props.document.folder_id"> | 所属: {{ props.document.folder_id }}</span>
          <span> | {{ detail?.chunk_count ?? document.chunk_count }} chunks</span>
        </p>
      </div>
      <button
        v-if="!isPageMode"
        class="knowledge-preview__icon-button"
        type="button"
        aria-label="关闭预览"
        title="关闭"
        @click="close"
      >
        <X :size="18" />
      </button>
    </header>

    <div class="knowledge-preview__toolbar">
      <div class="knowledge-preview__tabs" role="tablist" aria-label="知识库文档预览方式">
        <button
          class="knowledge-preview__tab"
          :class="{ 'is-active': activeTab === 'rendered' }"
          type="button"
          role="tab"
          :aria-selected="activeTab === 'rendered'"
          @click="activeTab = 'rendered'"
        >
          <Eye :size="15" />
          <span>{{ renderedLabel }}</span>
        </button>
        <button
          class="knowledge-preview__tab"
          :class="{ 'is-active': activeTab === 'chunks' }"
          type="button"
          role="tab"
          :aria-selected="activeTab === 'chunks'"
          @click="activeTab = 'chunks'"
        >
          <FileText :size="15" />
          <span>切片</span>
        </button>
      </div>
      <button
        class="knowledge-preview__download"
        type="button"
        :disabled="downloading"
        title="下载原文件"
        @click="downloadOriginal"
      >
        <Download :size="16" />
        <span>{{ downloading ? '下载中' : '原文件' }}</span>
      </button>
    </div>

    <div class="knowledge-preview__body">
      <div v-if="isBusy" class="knowledge-preview__state">
        <LoaderCircle :size="18" class="animate-spin" />
        <span>正在加载预览</span>
      </div>

      <p v-else-if="blockingError" class="knowledge-preview__error">{{ blockingError }}</p>

      <template v-else-if="activeTab === 'rendered'">
        <div v-if="fileError" class="knowledge-preview__rendered-error" role="alert">
          <p>{{ renderedErrorMessage }}</p>
          <p>可切换到“切片”查看已解析内容。</p>
        </div>

        <iframe
          v-else-if="canLoadRenderedPreview && previewFrameSrc"
          class="knowledge-preview__frame"
          :src="previewFrameSrc"
          :title="title"
        />

        <MarkdownRenderer
          v-else-if="previewKind === 'markdown'"
          class="knowledge-preview__markdown"
          :content="plainTextContent"
        />

        <article v-else-if="previewKind === 'text'" class="knowledge-preview__text">
          <pre v-if="plainTextContent">{{ plainTextContent }}</pre>
          <p v-else class="knowledge-preview__empty">暂无可预览内容</p>
        </article>

        <div v-else class="knowledge-preview__fallback">
          <p>当前格式暂无专用预览器。</p>
        </div>
      </template>

      <div v-else-if="chunks.length" class="knowledge-preview__chunks">
        <article v-for="chunk in chunks" :key="chunk.chunk_id" class="knowledge-preview__chunk">
          <div class="knowledge-preview__chunk-meta">
            片段 {{ chunk.index + 1 }}<span v-if="chunk.page"> | 第 {{ chunk.page }} 页</span>
          </div>
          <p>{{ chunk.content }}</p>
        </article>
      </div>

      <p v-else class="knowledge-preview__empty">暂无可预览内容</p>

      <p v-if="downloadError" class="knowledge-preview__error knowledge-preview__download-error">{{ downloadError }}</p>
    </div>
  </section>
</template>

<style scoped>
.knowledge-preview {
  display: flex;
  max-height: 88vh;
  width: min(1120px, 100%);
  flex-direction: column;
  overflow: hidden;
  border-radius: var(--radius-md);
  background: var(--color-card);
  box-shadow: 0 22px 70px rgba(0, 0, 0, 0.22);
}

.knowledge-preview.is-page {
  height: 100%;
  min-height: 0;
  max-height: 100%;
  width: 100%;
  border: 1px solid var(--color-border);
  overflow: hidden;
  box-shadow: none;
}

.knowledge-preview__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--color-border);
  padding: 16px 20px 14px;
}

.knowledge-preview__title-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
}

.knowledge-preview__meta {
  margin-top: 4px;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.knowledge-preview__icon-button,
.knowledge-preview__download,
.knowledge-preview__tab {
  display: inline-flex;
  align-items: center;
  border-radius: var(--radius-sm);
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.knowledge-preview__icon-button {
  height: 32px;
  width: 32px;
  flex-shrink: 0;
  justify-content: center;
  color: var(--color-text-secondary);
}

.knowledge-preview__icon-button:hover {
  background: var(--color-bg-secondary);
  color: var(--color-text);
}

.knowledge-preview__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-bg-secondary);
  padding: 8px 12px;
}

.knowledge-preview__tabs {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.knowledge-preview__tab {
  height: 32px;
  gap: 6px;
  padding: 0 10px;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.knowledge-preview__tab:hover,
.knowledge-preview__tab.is-active {
  background: var(--color-card);
  color: var(--color-accent);
}

.knowledge-preview__download {
  height: 32px;
  gap: 6px;
  border: 1px solid var(--color-border);
  background: var(--color-card);
  padding: 0 10px;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.knowledge-preview__download:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.knowledge-preview__download:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.knowledge-preview__body {
  min-height: 0;
  flex: 1;
  overflow: auto;
  background: var(--color-bg);
  padding: 18px;
}

.knowledge-preview.is-page .knowledge-preview__body {
  flex: 1;
  overflow: auto;
}

.knowledge-preview__state,
.knowledge-preview__error,
.knowledge-preview__empty,
.knowledge-preview__warning,
.knowledge-preview__fallback {
  color: var(--color-text-secondary);
  font-size: 14px;
}

.knowledge-preview__state {
  display: flex;
  align-items: center;
  gap: 8px;
}

.knowledge-preview__error {
  color: var(--color-danger);
}

.knowledge-preview__warning {
  margin-top: 12px;
  color: var(--color-warning);
}

.knowledge-preview__download-error {
  margin-top: 12px;
}

.knowledge-preview__rendered-error {
  margin: 0 auto;
  max-width: 760px;
  border: 1px solid color-mix(in srgb, var(--color-warning) 42%, var(--color-border));
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-warning) 10%, var(--color-card));
  padding: 18px 20px;
  color: var(--color-warning);
  font-size: 14px;
  line-height: 1.7;
}

.knowledge-preview__rendered-error p {
  margin: 0;
}

.knowledge-preview__rendered-error p + p {
  margin-top: 6px;
}

.knowledge-preview__frame {
  height: min(72vh, 760px);
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-card);
}

.knowledge-preview.is-page .knowledge-preview__frame {
  min-height: 560px;
  height: 100%;
}

.knowledge-preview__markdown,
.knowledge-preview__text {
  margin: 0 auto;
  max-width: 820px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-card);
  padding: clamp(20px, 4vw, 48px);
}

.knowledge-preview__text pre {
  margin: 0;
  color: var(--color-text);
  font-family: var(--font-mono);
  font-size: 15px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
}

.knowledge-preview__chunk-meta {
  margin-bottom: 12px;
  color: var(--color-text-tertiary);
  font-size: 12px;
}

.knowledge-preview__chunks {
  display: grid;
  gap: 12px;
}

.knowledge-preview__chunk {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-card);
  padding: 14px 16px;
}

.knowledge-preview__chunk p {
  margin: 0;
  color: var(--color-text);
  font-size: 14px;
  line-height: 1.75;
  white-space: pre-wrap;
}

@media (max-width: 760px) {
  .knowledge-preview {
    max-height: 92vh;
  }

  .knowledge-preview__toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .knowledge-preview__tabs,
  .knowledge-preview__download {
    width: 100%;
  }

  .knowledge-preview__tab {
    flex: 1;
    justify-content: center;
  }

  .knowledge-preview__download {
    justify-content: center;
  }

  .knowledge-preview__body {
    padding: 12px;
  }

}
</style>
