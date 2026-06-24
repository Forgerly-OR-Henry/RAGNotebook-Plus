<!--
模块职责：Vue 可复用组件，负责封装局部界面、交互状态和事件输出。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { X } from '@lucide/vue'

const props = withDefaults(defineProps<{
  open: boolean
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  variant?: 'default' | 'danger'
}>(), {
  confirmText: '确定',
  cancelText: '取消',
  variant: 'default',
})

// 组件事件：向父组件报告关闭、保存、选择等交互结果。
const emit = defineEmits<{
  'update:open': [open: boolean]
  confirm: []
}>()

const confirmButton = ref<HTMLButtonElement | null>(null)

// 状态监听：在关键输入变化后同步副作用或刷新页面数据。
watch(
  () => props.open,
  async (open) => {
    if (!open) return
    await nextTick()
    confirmButton.value?.focus()
  },
)

/**
 * 用途：执行close相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function close() {
  emit('update:open', false)
}

/**
 * 用途：执行confirm相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function confirm() {
  emit('confirm')
  close()
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-[60] bg-black/40" @click="close" />
    <section
      v-if="open"
      class="fixed left-1/2 top-1/2 z-[70] w-[400px] max-w-[90vw] -translate-x-1/2 -translate-y-1/2 rounded-lg bg-[var(--color-card)] p-6 shadow-xl"
      role="dialog"
      aria-modal="true"
      :aria-label="title"
    >
      <div class="mb-4 flex items-center justify-between gap-3">
        <h2 class="text-base font-medium text-[var(--color-text)]">{{ title }}</h2>
        <button class="text-[var(--color-text-tertiary)] hover:text-[var(--color-text)]" type="button" aria-label="关闭" @click="close">
          <X :size="16" />
        </button>
      </div>
      <p class="mb-6 text-sm leading-relaxed text-[var(--color-text-secondary)]">{{ message }}</p>
      <div class="flex justify-end gap-3">
        <button class="rounded-md border border-[var(--color-border)] px-4 py-2 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]" type="button" @click="close">
          {{ cancelText }}
        </button>
        <button
          ref="confirmButton"
          class="rounded-md px-4 py-2 text-sm text-white"
          :class="variant === 'danger' ? 'bg-[var(--color-danger)] hover:bg-red-700' : 'bg-[var(--color-accent)] hover:opacity-90'"
          type="button"
          @click="confirm"
        >
          {{ confirmText }}
        </button>
      </div>
    </section>
  </Teleport>
</template>
