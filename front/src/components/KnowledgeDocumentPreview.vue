<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { Download, Eye, FileText, LoaderCircle, X } from '@lucide/vue'
import { knowledgeApi } from '../api/knowledge'
import type { KnowledgeChunk, KnowledgeDocument, KnowledgeDocumentDetail } from '../types/api'

type PreviewKind = 'pdf' | 'markdown' | 'text' | 'word' | 'presentation' | 'fallback'
type PreviewTab = 'rendered' | 'chunks'

const props = defineProps<{
  document: KnowledgeDocument
  detail: KnowledgeDocumentDetail | null
  loading: boolean
  error: string
  mode?: 'modal' | 'page'
}>()

const emit = defineEmits<{ close: [] }>()

const activeTab = ref<PreviewTab>('rendered')
const fileLoading = ref(false)
const fileError = ref('')
const fileBlob = ref<Blob | null>(null)
const objectUrl = ref('')
const originalText = ref('')
const downloading = ref(false)
const downloadError = ref('')
let loadSerial = 0

function getDocumentTitle(doc: KnowledgeDocument) {
  return doc.original_filename || doc.filename
}

function getExtension(doc: KnowledgeDocument) {
  const explicitExt = doc.file_ext?.trim().toLowerCase()
  if (explicitExt) {
    return explicitExt.startsWith('.') ? explicitExt : `.${explicitExt}`
  }
  const name = getDocumentTitle(doc)
  const match = name.match(/\.[^.]+$/)
  return match?.[0].toLowerCase() || ''
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

function revokeObjectUrl() {
  if (objectUrl.value) {
    URL.revokeObjectURL(objectUrl.value)
    objectUrl.value = ''
  }
}

function resetFileState() {
  loadSerial += 1
  revokeObjectUrl()
  fileLoading.value = false
  fileError.value = ''
  downloadError.value = ''
  fileBlob.value = null
  originalText.value = ''
}

const title = computed(() => getDocumentTitle(props.document))
const isPageMode = computed(() => props.mode === 'page')
const extension = computed(() => getExtension(props.document))
const fileSize = computed(() => formatFileSize(props.document.file_size))
const createdAt = computed(() => formatDate(props.document.created_at))
const chunks = computed(() => props.detail?.chunks || [])

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

const canLoadOriginal = computed(() => ['pdf', 'markdown', 'text'].includes(previewKind.value))
const isBusy = computed(() => props.loading || fileLoading.value)
const blockingError = computed(() => props.error || (previewKind.value === 'pdf' ? fileError.value : ''))

const renderedMarkdown = computed(() => {
  const source = originalText.value || props.detail?.content || ''
  const rawHtml = marked.parse(source, {
    async: false,
    breaks: true,
    gfm: true,
  }) as string

  return DOMPurify.sanitize(rawHtml, {
    USE_PROFILES: { html: true },
    ADD_ATTR: ['target', 'rel'],
  })
})

const plainTextParagraphs = computed(() => {
  const source = originalText.value || props.detail?.content || ''
  return source.split(/\n{2,}/).map((item) => item.trim()).filter(Boolean)
})

function splitDisplayLines(content: string) {
  return content.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
}

const officeSections = computed(() => {
  const sourceChunks = chunks.value.length
    ? chunks.value
    : props.detail?.content
      ? [{ chunk_id: 'content', index: 0, content: props.detail.content, page: 0, images: [] } satisfies KnowledgeChunk]
      : []

  return sourceChunks.map((chunk, index) => {
    const lines = splitDisplayLines(chunk.content)
    const fallbackTitle = previewKind.value === 'presentation' ? `幻灯片 ${index + 1}` : `片段 ${index + 1}`
    return {
      id: chunk.chunk_id || `${index}`,
      index,
      page: chunk.page,
      title: lines[0] || fallbackTitle,
      body: lines.length > 1 ? lines.slice(1) : lines,
    }
  })
})

function createObjectUrl(blob: Blob) {
  revokeObjectUrl()
  objectUrl.value = URL.createObjectURL(blob)
}

async function loadOriginalFile() {
  if (!canLoadOriginal.value) {
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
    if (previewKind.value === 'pdf') {
      createObjectUrl(response.data)
    } else {
      originalText.value = await response.data.text()
    }
  } catch (error) {
    if (serial !== loadSerial) {
      return
    }
    fileError.value = error instanceof Error ? error.message : '原文件加载失败'
  } finally {
    if (serial === loadSerial) {
      fileLoading.value = false
    }
  }
}

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
    downloadError.value = error instanceof Error ? error.message : '原文件下载失败'
  } finally {
    downloading.value = false
  }
}

function close() {
  emit('close')
}

watch(
  () => props.document.id,
  () => {
    activeTab.value = 'rendered'
    resetFileState()
    void loadOriginalFile()
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
        <iframe
          v-if="previewKind === 'pdf' && objectUrl"
          class="knowledge-preview__pdf"
          :src="objectUrl"
          :title="title"
        />

        <!-- eslint-disable vue/no-v-html -->
        <article
          v-else-if="previewKind === 'markdown'"
          class="markdown-body knowledge-preview__markdown"
          v-html="renderedMarkdown"
        />
        <!-- eslint-enable vue/no-v-html -->

        <article v-else-if="previewKind === 'text'" class="knowledge-preview__text">
          <p v-for="(paragraph, index) in plainTextParagraphs" :key="index">{{ paragraph }}</p>
          <p v-if="!plainTextParagraphs.length" class="knowledge-preview__empty">暂无可预览内容</p>
        </article>

        <div v-else-if="previewKind === 'presentation'" class="knowledge-preview__slides">
          <article v-for="section in officeSections" :key="section.id" class="knowledge-preview__slide">
            <div class="knowledge-preview__slide-label">幻灯片 {{ section.index + 1 }}</div>
            <h4>{{ section.title }}</h4>
            <ul v-if="section.body.length > 1">
              <li v-for="(line, index) in section.body" :key="index">{{ line }}</li>
            </ul>
            <p v-else-if="section.body.length === 1">{{ section.body[0] }}</p>
          </article>
          <p v-if="!officeSections.length" class="knowledge-preview__empty">暂无可预览内容</p>
        </div>

        <div v-else-if="previewKind === 'word'" class="knowledge-preview__pages">
          <article v-for="section in officeSections" :key="section.id" class="knowledge-preview__page">
            <div class="knowledge-preview__page-meta">
              片段 {{ section.index + 1 }}<span v-if="section.page"> | 第 {{ section.page }} 页</span>
            </div>
            <h4>{{ section.title }}</h4>
            <p v-for="(line, index) in section.body" :key="index">{{ line }}</p>
          </article>
          <p v-if="!officeSections.length" class="knowledge-preview__empty">暂无可预览内容</p>
        </div>

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

      <p v-if="fileError && activeTab === 'rendered' && previewKind !== 'pdf'" class="knowledge-preview__warning">
        原文件读取失败，当前使用解析后的内容预览。
      </p>
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
  min-height: calc(100vh - 9rem);
  max-height: none;
  width: 100%;
  border: 1px solid var(--color-border);
  overflow: visible;
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
  flex: none;
  overflow: visible;
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

.knowledge-preview__pdf {
  height: min(72vh, 760px);
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-card);
}

.knowledge-preview.is-page .knowledge-preview__pdf {
  min-height: 560px;
  height: calc(100vh - 15rem);
}

.knowledge-preview__markdown,
.knowledge-preview__text,
.knowledge-preview__page {
  margin: 0 auto;
  max-width: 820px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-card);
  padding: clamp(20px, 4vw, 48px);
}

.knowledge-preview__text p {
  margin: 0 0 0.9em;
  color: var(--color-text);
  font-size: 15px;
  line-height: 1.8;
  white-space: pre-wrap;
}

.knowledge-preview__pages {
  display: grid;
  gap: 18px;
}

.knowledge-preview__page {
  min-height: 360px;
}

.knowledge-preview__page-meta,
.knowledge-preview__chunk-meta,
.knowledge-preview__slide-label {
  margin-bottom: 12px;
  color: var(--color-text-tertiary);
  font-size: 12px;
}

.knowledge-preview__page h4 {
  margin: 0 0 16px;
  font-family: var(--font-heading);
  font-size: 1.2rem;
  line-height: 1.35;
}

.knowledge-preview__page p {
  margin: 0 0 0.8em;
  color: var(--color-text);
  font-size: 15px;
  line-height: 1.8;
}

.knowledge-preview__slides {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 18px;
}

.knowledge-preview__slide {
  aspect-ratio: 16 / 9;
  min-height: 260px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-card);
  padding: 28px;
}

.knowledge-preview__slide h4 {
  margin: 0 0 18px;
  font-family: var(--font-heading);
  font-size: clamp(1.15rem, 2vw, 1.55rem);
  line-height: 1.3;
}

.knowledge-preview__slide p,
.knowledge-preview__slide li {
  color: var(--color-text);
  font-size: 15px;
  line-height: 1.65;
}

.knowledge-preview__slide ul {
  margin: 0;
  padding-left: 1.2em;
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

  .knowledge-preview__slides {
    grid-template-columns: 1fr;
  }

  .knowledge-preview__slide {
    min-height: 220px;
    padding: 20px;
  }
}
</style>
