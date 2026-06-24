<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { AlertTriangle, Info, X } from '@lucide/vue'
import { useAppDialogState } from '../composables/useAppDialog'

const { activeDialog, cancelDialog, confirmActiveDialog } = useAppDialogState()

const inputValue = ref('')
const confirmButton = ref<HTMLButtonElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)

const isOpen = computed(() => Boolean(activeDialog.value))
const isPrompt = computed(() => activeDialog.value?.type === 'prompt')
const icon = computed(() => activeDialog.value?.variant === 'danger' ? AlertTriangle : Info)

watch(
  activeDialog,
  async (dialog) => {
    if (!dialog) return
    inputValue.value = dialog.type === 'prompt' ? dialog.initialValue || '' : ''
    await nextTick()
    if (dialog.type === 'prompt') {
      inputRef.value?.focus()
      inputRef.value?.select()
      return
    }
    confirmButton.value?.focus()
  },
)

function submit() {
  if (isPrompt.value) {
    confirmActiveDialog(inputValue.value)
    return
  }
  confirmActiveDialog()
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-[90] flex items-center justify-center bg-black/40 px-4 py-6 backdrop-blur-[2px]"
      @click.self="cancelDialog"
      @keydown.esc="cancelDialog"
    >
      <form
        class="w-full max-w-[440px] overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] shadow-2xl"
        role="dialog"
        aria-modal="true"
        :aria-label="activeDialog?.title"
        @submit.prevent="submit"
      >
        <header class="flex items-start justify-between gap-4 border-b border-[var(--color-border-light)] px-5 py-4">
          <div class="flex min-w-0 items-start gap-3">
            <span
              class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md"
              :class="activeDialog?.variant === 'danger' ? 'bg-[var(--color-danger-bg)] text-[var(--color-danger)]' : 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]'"
            >
              <component :is="icon" :size="18" />
            </span>
            <div class="min-w-0">
              <h2 class="text-base font-medium leading-6 text-[var(--color-text)]">{{ activeDialog?.title }}</h2>
              <p v-if="activeDialog?.message" class="mt-1 text-sm leading-relaxed text-[var(--color-text-secondary)]">{{ activeDialog.message }}</p>
            </div>
          </div>
          <button
            class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-[var(--color-text-tertiary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]"
            type="button"
            aria-label="关闭"
            @click="cancelDialog"
          >
            <X :size="16" />
          </button>
        </header>

        <div v-if="isPrompt" class="px-5 py-4">
          <input
            ref="inputRef"
            v-model="inputValue"
            class="h-10 w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 text-sm text-[var(--color-text)] outline-none placeholder:text-[var(--color-text-placeholder)] focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent-bg)]"
            :placeholder="activeDialog?.type === 'prompt' ? activeDialog.placeholder : ''"
          />
        </div>

        <footer class="flex justify-end gap-2 bg-[var(--color-bg)] px-5 py-4">
          <button
            class="rounded-md border border-[var(--color-border)] px-4 py-2 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]"
            type="button"
            @click="cancelDialog"
          >
            {{ activeDialog?.cancelText || '取消' }}
          </button>
          <button
            ref="confirmButton"
            class="rounded-md px-4 py-2 text-sm font-medium text-white"
            :class="activeDialog?.variant === 'danger' ? 'bg-[var(--color-danger)] hover:bg-red-700' : 'bg-[var(--color-accent)] hover:opacity-90'"
            type="submit"
          >
            {{ activeDialog?.confirmText || '确定' }}
          </button>
        </footer>
      </form>
    </div>
  </Teleport>
</template>
