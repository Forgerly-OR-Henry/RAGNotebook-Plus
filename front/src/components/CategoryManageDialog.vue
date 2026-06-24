<!--
模块职责：Vue 可复用组件，负责封装局部界面、交互状态和事件输出。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
<script setup lang="ts">
import { ref, watch } from 'vue'
import { FolderTree, GripVertical, Plus, Trash2, X } from '@lucide/vue'
import ConfirmDialog from './ConfirmDialog.vue'
import { notesApi } from '../api/notes'
import { writeJsonPref } from '../api/localPrefs'

/**
 * 接口：`CategoryItem` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface CategoryItem {
  category: string
  count: number
}

const props = withDefaults(defineProps<{
  open: boolean
  categories: CategoryItem[]
  storageKey?: string
  itemName?: string
  deleteCategory?: (category: string) => Promise<unknown>
}>(), {
  storageKey: 'note_category_order',
  itemName: '笔记',
  deleteCategory: undefined,
})

// 组件事件：向父组件报告关闭、保存、选择等交互结果。
const emit = defineEmits<{
  'update:open': [open: boolean]
  refresh: []
  'create-category': [name: string]
}>()

const PREDEFINED_VALUES = new Set(['work', 'study', 'life', 'project', 'other'])
const CATEGORY_LABEL_MAP: Record<string, string> = {
  work: '工作',
  study: '学习',
  life: '生活',
  project: '技术',
  other: '其他',
}

const items = ref<CategoryItem[]>([])
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const newCategory = ref('')
const deleteTarget = ref<CategoryItem | null>(null)
const dragItem = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

// 状态监听：在关键输入变化后同步副作用或刷新页面数据。
watch(
  () => [props.open, props.categories] as const,
  () => {
    if (props.open) items.value = [...props.categories]
  },
  { immediate: true },
)

/**
 * 用途：执行label相关业务逻辑。
 * @param category 调用方传入的category参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function label(category: string) {
  return CATEGORY_LABEL_MAP[category] || category
}

/**
 * 用途：执行close相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function close() {
  emit('update:open', false)
}

/**
 * 用途：执行saveOrder相关业务逻辑。
 * @param nextItems 调用方传入的nextItems参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function saveOrder(nextItems: CategoryItem[]) {
  writeJsonPref(props.storageKey, nextItems.map((item) => item.category))
}

/**
 * 用途：执行createCategory相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function createCategory() {
  const name = newCategory.value.trim()
  if (!name || items.value.some((item) => item.category === name)) return
  items.value = [...items.value, { category: name, count: 0 }]
  newCategory.value = ''
  emit('create-category', name)
}

/**
 * 用途：执行handleDragStart相关业务逻辑。
 * @param index 调用方传入的index参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function handleDragStart(index: number) {
  dragItem.value = index
}

/**
 * 用途：执行handleDrop相关业务逻辑。
 * @param index 调用方传入的index参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function handleDrop(index: number) {
  const from = dragItem.value
  dragItem.value = null
  dragOverIndex.value = null
  if (from === null || from === index) return
  const next = [...items.value]
  const [moved] = next.splice(from, 1)
  if (!moved) return
  next.splice(index, 0, moved)
  items.value = next
  saveOrder(next)
  emit('refresh')
}

/**
 * 用途：执行confirmDelete相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function confirmDelete() {
  const target = deleteTarget.value
  if (!target) return
  try {
    await (props.deleteCategory ?? notesApi.deleteCategory)(target.category)
    items.value = items.value.filter((item) => item.category !== target.category)
    emit('refresh')
  } finally {
    deleteTarget.value = null
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-50 bg-black/40" @click="close" />
    <section
      v-if="open"
      class="fixed left-1/2 top-1/2 z-50 flex max-h-[80vh] w-[440px] max-w-[90vw] -translate-x-1/2 -translate-y-1/2 flex-col rounded-lg bg-[var(--color-card)] p-6 shadow-xl"
      role="dialog"
      aria-modal="true"
      aria-label="分类管理"
    >
      <div class="mb-4 flex items-center justify-between gap-3">
        <h3 class="text-base font-medium text-[var(--color-text)]">分类管理</h3>
        <button class="text-[var(--color-text-tertiary)] hover:text-[var(--color-text)]" type="button" aria-label="关闭" @click="close">
          <X :size="16" />
        </button>
      </div>

      <div class="mb-4 flex gap-2">
        <input
          v-model="newCategory"
          class="flex-1 rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-1.5 text-sm text-[var(--color-text)] outline-none placeholder:text-[var(--color-text-placeholder)] focus:ring-2 focus:ring-[var(--color-accent)]"
          placeholder="输入新分类名称"
          @keydown.enter="createCategory"
        />
        <button class="inline-flex items-center gap-1.5 rounded-md bg-[var(--color-accent)] px-3 py-1.5 text-sm text-white disabled:opacity-40" type="button" :disabled="!newCategory.trim()" @click="createCategory">
          <Plus :size="14" />
          新建
        </button>
      </div>

      <div class="flex-1 space-y-1 overflow-y-auto">
        <div
          v-for="(item, index) in items"
          :key="item.category"
          class="group flex cursor-default items-center justify-between rounded-md px-3 py-2 transition-colors"
          :class="dragOverIndex === index ? 'border-t-2 border-t-[var(--color-accent)] bg-[var(--color-bg-secondary)]' : 'hover:bg-[var(--color-bg-secondary)]'"
          draggable="true"
          @dragstart="handleDragStart(index)"
          @dragover.prevent="dragOverIndex = index"
          @drop.prevent="handleDrop(index)"
          @dragend="dragOverIndex = null"
        >
          <div class="flex min-w-0 items-center gap-2">
            <GripVertical :size="14" class="shrink-0 cursor-grab text-[var(--color-text-tertiary)] active:cursor-grabbing" />
            <FolderTree :size="14" class="shrink-0 text-[var(--color-text-tertiary)]" />
            <span class="truncate text-sm text-[var(--color-text)]">{{ label(item.category) }}</span>
            <span class="text-xs text-[var(--color-text-tertiary)]">({{ item.count }})</span>
          </div>
          <button
            v-if="!PREDEFINED_VALUES.has(item.category)"
            class="rounded p-1 text-[var(--color-text-tertiary)] opacity-0 transition-all hover:bg-red-500/10 hover:text-red-500 group-hover:opacity-100"
            type="button"
            aria-label="删除分类"
            @click="deleteTarget = item"
          >
            <Trash2 :size="14" />
          </button>
        </div>
        <p v-if="items.length === 0" class="py-8 text-center text-xs text-[var(--color-text-tertiary)]">暂无分类</p>
      </div>

      <p class="mt-3 text-center text-xs text-[var(--color-text-tertiary)]">预设分类不可删除</p>
    </section>
  </Teleport>

  <ConfirmDialog
    :open="deleteTarget !== null"
    title="删除分类"
    :message="`确定要删除分类「${deleteTarget ? label(deleteTarget.category) : ''}」吗？这将同步删除该分类下的 ${deleteTarget?.count ?? 0} 篇${props.itemName}。`"
    variant="danger"
    confirm-text="删除"
    @update:open="(open) => { if (!open) deleteTarget = null }"
    @confirm="confirmDelete"
  />
</template>
