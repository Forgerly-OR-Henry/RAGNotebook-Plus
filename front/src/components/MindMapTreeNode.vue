<script setup lang="ts">
interface MindMapTreeNodeData {
  id: string
  label: string
  summary?: string | null
  children: MindMapTreeNodeData[]
}

defineOptions({ name: 'MindMapTreeNode' })

withDefaults(defineProps<{
  node: MindMapTreeNodeData
  depth?: number
}>(), {
  depth: 0,
})

function nodeClass(depth: number) {
  if (depth === 0) {
    return 'border-transparent bg-[var(--color-accent)] text-white text-sm font-semibold'
  }
  if (depth === 1) {
    return 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 text-xs font-medium dark:text-emerald-300'
  }
  if (depth === 2) {
    return 'border-sky-500/30 bg-sky-500/10 text-sky-600 text-[11px] dark:text-sky-300'
  }
  return 'border-[var(--color-border)] bg-[var(--color-card)] text-[var(--color-text)] text-[10px]'
}
</script>

<template>
  <div class="relative flex items-center select-none">
    <div v-if="depth > 0" class="absolute left-[-24px] top-1/2 h-px w-6 -translate-y-1/2 bg-[var(--color-border)]" />

    <div
      class="z-10 max-w-[220px] shrink-0 rounded-md border px-4 py-2.5 text-center leading-snug shadow-sm transition-transform duration-150 hover:scale-[1.03]"
      :class="nodeClass(depth)"
      :title="node.summary || node.label"
    >
      <span class="block break-words">{{ node.label }}</span>
    </div>

    <div v-if="node.children.length > 0" class="h-px w-6 shrink-0 bg-[var(--color-border)]" />

    <div v-if="node.children.length > 0" class="relative flex flex-col gap-4 border-l-2 border-dashed border-[var(--color-border)]/70 py-2 pl-6">
      <MindMapTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :depth="depth + 1"
      />
    </div>
  </div>
</template>
