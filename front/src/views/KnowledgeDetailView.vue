<!--
模块职责：Vue 页面组件，负责组合业务 API、页面状态和用户交互。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Sparkles } from '@lucide/vue'
import KnowledgeDocumentPreview from '../components/KnowledgeDocumentPreview.vue'
import TagInput from '../components/TagInput.vue'
import { knowledgeApi } from '../api/knowledge'
import type { KnowledgeDocument, KnowledgeDocumentDetail } from '../types/api'

/**
 * 类型：`ApiError` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
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
const documentId = route.params.id as string | undefined
const document = ref<KnowledgeDocument | null>(null)
const detail = ref<KnowledgeDocumentDetail | null>(null)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const loading = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const savingMetadata = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const aiTagging = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const metadataReady = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const errorMessage = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const metadataError = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const message = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const category = ref('')
const tags = ref<string[]>([])
let metadataTimer: number | undefined

const CATEGORIES = [
  { label: '工作', value: 'work' },
  { label: '学习', value: 'study' },
  { label: '生活', value: 'life' },
  { label: '技术', value: 'project' },
  { label: '其他', value: 'other' },
]

/**
 * 用途：执行getErrorMessage相关业务逻辑。
 * @param error 调用方传入的error参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function getErrorMessage(error: unknown) {
  const apiError = error as ApiError
  const detailMessage = apiError.response?.data?.detail
  if (typeof detailMessage === 'string') {
    return detailMessage
  }
  if (detailMessage && typeof detailMessage === 'object' && 'message' in detailMessage) {
    return String((detailMessage as { message?: unknown }).message)
  }
  return apiError.response?.data?.message || apiError.message || '加载知识库内容失败，请稍后重试'
}

/**
 * 用途：执行load相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function load() {
  if (!documentId) {
    errorMessage.value = '文档不存在'
    return
  }

  loading.value = true
  metadataReady.value = false
  errorMessage.value = ''
  metadataError.value = ''
  message.value = ''
  try {
    const res = await knowledgeApi.detail(documentId)
    detail.value = res.data
    document.value = res.data
    category.value = res.data.category || ''
    tags.value = res.data.tags || []
    await nextTick()
    metadataReady.value = true
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

/**
 * 用途：执行applyMetadata相关业务逻辑。
 * @param nextDocument 调用方传入的nextDocument参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function applyMetadata(nextDocument: KnowledgeDocument) {
  document.value = { ...(document.value || nextDocument), ...nextDocument }
  if (detail.value) {
    detail.value = { ...detail.value, ...nextDocument }
  }
}

/**
 * 用途：执行saveMetadata相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function saveMetadata() {
  if (!documentId || !metadataReady.value || savingMetadata.value) return
  savingMetadata.value = true
  message.value = ''
  metadataError.value = ''
  try {
    const res = await knowledgeApi.updateMetadata(documentId, {
      category: category.value || null,
      tags: tags.value,
    })
    applyMetadata(res.data)
    message.value = '已保存'
  } catch (error) {
    metadataError.value = getErrorMessage(error)
  } finally {
    savingMetadata.value = false
  }
}

/**
 * 用途：执行scheduleMetadataSave相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function scheduleMetadataSave() {
  if (!metadataReady.value) return
  window.clearTimeout(metadataTimer)
  metadataTimer = window.setTimeout(() => {
    void saveMetadata()
  }, 500)
}

/**
 * 用途：执行toggleCategory相关业务逻辑。
 * @param value 调用方传入的value参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function toggleCategory(value: string) {
  category.value = category.value === value ? '' : value
  void saveMetadata()
}

/**
 * 用途：执行recognizeTagsWithAi相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function recognizeTagsWithAi() {
  if (!documentId || aiTagging.value || savingMetadata.value) return
  aiTagging.value = true
  message.value = ''
  metadataError.value = ''
  try {
    const res = await knowledgeApi.autoTag(documentId)
    metadataReady.value = false
    category.value = res.data.category || ''
    tags.value = res.data.tags || []
    applyMetadata(res.data)
    await nextTick()
    metadataReady.value = true
    message.value = 'AI 识别完成'
  } catch (error) {
    metadataError.value = getErrorMessage(error)
  } finally {
    aiTagging.value = false
  }
}

onMounted(load)

// 状态监听：在关键输入变化后同步副作用或刷新页面数据。
watch(tags, () => {
  scheduleMetadataSave()
}, { deep: true })

onBeforeUnmount(() => {
  window.clearTimeout(metadataTimer)
})
</script>

<template>
  <div class="mx-auto flex h-[calc(100vh-7rem)] max-w-6xl flex-col overflow-hidden">
    <div v-if="!document && loading" class="flex min-h-0 flex-1 items-center justify-center text-sm text-[var(--color-text-secondary)]">加载中</div>
    <p v-else-if="!document" class="text-sm text-[var(--color-danger)]">{{ errorMessage }}</p>
    <template v-else>
      <div class="shrink-0 px-2 pb-6">
        <div class="flex flex-wrap items-center gap-3">
          <div class="flex flex-wrap items-center gap-1">
            <button
              v-for="item in CATEGORIES"
              :key="item.value"
              class="rounded-full px-3 py-1 text-xs font-medium transition-colors"
              :class="category === item.value ? 'bg-[var(--color-accent)] text-white shadow-sm' : 'bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] hover:text-[var(--color-text)]'"
              type="button"
              @click="toggleCategory(item.value)"
            >
              {{ item.label }}
            </button>
          </div>
          <div class="min-w-44 flex-1">
            <TagInput v-model:tags="tags" placeholder="添加标签..." />
          </div>
          <button
            class="inline-flex h-8 shrink-0 items-center gap-1 rounded-md border border-[var(--color-border)] px-2.5 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-accent-bg)] hover:text-[var(--color-accent)] disabled:cursor-not-allowed disabled:opacity-60"
            type="button"
            :disabled="aiTagging || savingMetadata"
            title="自动识别分类并提炼关键词"
            @click="recognizeTagsWithAi"
          >
            <Sparkles :size="13" />
            {{ aiTagging ? '识别中' : 'AI识别' }}
          </button>
        </div>
        <p v-if="message" class="mt-2 text-xs text-[var(--color-success)]">{{ message }}</p>
        <p v-if="metadataError" class="mt-2 text-xs text-[var(--color-danger)]">{{ metadataError }}</p>
      </div>

      <KnowledgeDocumentPreview
        class="min-h-0 flex-1"
        :document="document"
        :detail="detail"
        :loading="loading"
        :error="errorMessage"
        mode="page"
      />
    </template>
  </div>
</template>
