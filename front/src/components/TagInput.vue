<script setup lang="ts">
import { ref } from 'vue'
import { X } from '@lucide/vue'

const props = withDefaults(defineProps<{
  tags: string[]
  placeholder?: string
}>(), {
  placeholder: '添加标签...',
})

const emit = defineEmits<{
  'update:tags': [tags: string[]]
}>()

const value = ref('')
const inputRef = ref<HTMLInputElement | null>(null)

function update(nextTags: string[]) {
  emit('update:tags', nextTags)
}

function addTag(raw: string) {
  const tag = raw.trim()
  if (!tag) return
  if (!props.tags.includes(tag)) {
    update([...props.tags, tag])
  }
  value.value = ''
}

function removeTag(index: number) {
  update(props.tags.filter((_, currentIndex) => currentIndex !== index))
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' || event.key === ',' || event.key === '，') {
    event.preventDefault()
    addTag(value.value)
    return
  }
  if (event.key === 'Backspace' && !value.value && props.tags.length > 0) {
    removeTag(props.tags.length - 1)
  }
}

function handlePaste(event: ClipboardEvent) {
  const text = event.clipboardData?.getData('text') || ''
  if (!/[，,]/.test(text)) return
  event.preventDefault()
  const next = [...props.tags]
  for (const part of text.split(/[，,]/).map((item) => item.trim()).filter(Boolean)) {
    if (!next.includes(part)) next.push(part)
  }
  update(next)
}
</script>

<template>
  <div
    class="flex min-h-8 cursor-text flex-wrap items-center gap-1.5 rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-2.5 py-1 transition-colors focus-within:border-[var(--color-accent)] focus-within:ring-1 focus-within:ring-[var(--color-accent)]"
    @click="inputRef?.focus()"
  >
    <span
      v-for="(tag, index) in tags"
      :key="tag"
      class="inline-flex items-center gap-1 rounded-full bg-[var(--color-accent-bg)] px-2 py-0.5 text-xs text-[var(--color-accent)]"
    >
      {{ tag }}
      <button class="hover:text-[var(--color-danger)]" type="button" aria-label="删除标签" @click.stop="removeTag(index)">
        <X :size="12" />
      </button>
    </span>
    <input
      ref="inputRef"
      v-model="value"
      class="min-w-20 flex-1 border-0 bg-transparent text-xs text-[var(--color-text)] outline-none placeholder:text-[var(--color-text-placeholder)]"
      :placeholder="tags.length === 0 ? placeholder : ''"
      @keydown="handleKeydown"
      @paste="handlePaste"
    />
  </div>
</template>
