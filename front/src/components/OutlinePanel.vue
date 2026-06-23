<script setup lang="ts">
import { computed } from 'vue'
import { Heading1, Heading2, Heading3, X } from '@lucide/vue'

interface HeadingItem {
  level: number
  text: string
}

const props = defineProps<{
  content: string
  open: boolean
}>()

const emit = defineEmits<{
  close: []
  'heading-click': [text: string, level: number]
}>()

function stripInlineFormatting(text: string) {
  return text
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/`[^`]*`/g, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/_([^_]+)_/g, '$1')
    .replace(/~~([^~]+)~~/g, '$1')
    .replace(/#+\s*$/, '')
    .trim()
}

function parseHeadings(markdown: string): HeadingItem[] {
  const noCode = markdown.replace(/```[\s\S]*?```/g, '').replace(/`{1,3}[^`]*`{1,3}/g, '')
  const regex = /^(#{1,6})\s+(.+)$/gm
  const items: HeadingItem[] = []
  let match: RegExpExecArray | null
  while ((match = regex.exec(noCode)) !== null) {
    const text = stripInlineFormatting(match[2] || '')
    if (text) items.push({ level: match[1].length, text })
  }
  return items
}

const headings = computed(() => parseHeadings(props.content))
</script>

<template>
  <aside v-if="open" class="flex w-60 shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-card)]">
    <div class="flex h-12 items-center justify-between border-b border-[var(--color-border-light)] px-4">
      <h2 class="text-sm font-medium text-[var(--color-text)]">
        目录
        <span class="ml-1.5 text-xs text-[var(--color-text-tertiary)]">({{ headings.length }})</span>
      </h2>
      <button class="rounded-md p-1 text-[var(--color-text-tertiary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]" type="button" aria-label="关闭目录" @click="emit('close')">
        <X :size="16" />
      </button>
    </div>
    <div class="flex-1 overflow-y-auto">
      <div v-if="headings.length === 0" class="px-4 py-12 text-center text-sm text-[var(--color-text-tertiary)]">暂无标题</div>
      <div v-else class="space-y-0.5 p-2">
        <button
          v-for="(heading, index) in headings"
          :key="`${heading.text}-${index}`"
          class="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]"
          :style="{ paddingLeft: `${8 + (heading.level - 1) * 16}px` }"
          type="button"
          @click="emit('heading-click', heading.text, heading.level)"
        >
          <Heading1 v-if="heading.level === 1" :size="14" class="shrink-0 text-[var(--color-text-tertiary)]" />
          <Heading2 v-else-if="heading.level === 2" :size="14" class="shrink-0 text-[var(--color-text-tertiary)]" />
          <Heading3 v-else-if="heading.level === 3" :size="14" class="shrink-0 text-[var(--color-text-tertiary)]" />
          <span v-else class="shrink-0 text-xs font-bold text-[var(--color-text-tertiary)]">H{{ heading.level }}</span>
          <span class="truncate">{{ heading.text }}</span>
        </button>
      </div>
    </div>
  </aside>
</template>
