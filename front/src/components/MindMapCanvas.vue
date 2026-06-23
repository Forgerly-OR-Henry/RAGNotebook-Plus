<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { Copy, RotateCcw, ZoomIn, ZoomOut } from '@lucide/vue'
import MindMapTreeNode from './MindMapTreeNode.vue'
import type { MindMapNode, MindMapResponse } from '../types/api'

interface MindMapTreeNodeData {
  id: string
  label: string
  summary?: string | null
  children: MindMapTreeNodeData[]
}

const props = withDefaults(defineProps<{
  mindmap: MindMapResponse | null
  loading?: boolean
  emptyText?: string
}>(), {
  loading: false,
  emptyText: '请选择来源后生成导图。',
})

const scale = ref(1)
const offset = ref({ x: 0, y: 0 })
const dragging = ref(false)
const dragStart = ref({ x: 0, y: 0 })
const copyMessage = ref('')
let copyTimer: number | undefined

const tree = computed(() => buildTree(props.mindmap))
const scaleLabel = computed(() => `${Math.round(scale.value * 100)}%`)

watch(() => props.mindmap?.mindmap_id, () => resetView())

onBeforeUnmount(() => {
  if (copyTimer) window.clearTimeout(copyTimer)
})

function buildTree(mindmap: MindMapResponse | null): MindMapTreeNodeData | null {
  if (!mindmap?.nodes.length) return null

  const nodeMap = new Map<string, MindMapTreeNodeData>()
  const targets = new Set<string>()

  mindmap.nodes.forEach((node) => {
    nodeMap.set(node.id, {
      id: node.id,
      label: node.label,
      summary: node.summary,
      children: [],
    })
  })

  mindmap.edges.forEach((edge) => {
    const source = nodeMap.get(edge.source)
    const target = nodeMap.get(edge.target)
    if (!source || !target || source.children.some((child) => child.id === target.id)) return
    source.children.push(target)
    targets.add(target.id)
  })

  const rootNode = pickRoot(mindmap.nodes, targets, nodeMap)
  const attached = new Set<string>()
  collectTreeIds(rootNode, attached)

  mindmap.nodes.forEach((node) => {
    const candidate = nodeMap.get(node.id)
    if (candidate && !attached.has(candidate.id)) {
      rootNode.children.push(candidate)
    }
  })

  return rootNode
}

function pickRoot(nodes: MindMapNode[], targets: Set<string>, nodeMap: Map<string, MindMapTreeNodeData>) {
  const root = nodes.find((node) => node.level === 0 && !targets.has(node.id))
    || nodes.find((node) => !targets.has(node.id))
    || nodes[0]
  return nodeMap.get(root.id) || {
    id: root.id,
    label: root.label,
    summary: root.summary,
    children: [],
  }
}

function collectTreeIds(node: MindMapTreeNodeData, ids: Set<string>) {
  if (ids.has(node.id)) return
  ids.add(node.id)
  node.children.forEach((child) => collectTreeIds(child, ids))
}

function startPan(event: PointerEvent) {
  if (!tree.value || event.button !== 0) return
  dragging.value = true
  dragStart.value = {
    x: event.clientX - offset.value.x,
    y: event.clientY - offset.value.y,
  }
  const target = event.currentTarget as HTMLElement
  target.setPointerCapture?.(event.pointerId)
}

function movePan(event: PointerEvent) {
  if (!dragging.value) return
  offset.value = {
    x: event.clientX - dragStart.value.x,
    y: event.clientY - dragStart.value.y,
  }
}

function endPan(event: PointerEvent) {
  dragging.value = false
  const target = event.currentTarget as HTMLElement
  try {
    target.releasePointerCapture?.(event.pointerId)
  } catch {
    // Pointer capture may already be released when the pointer leaves the canvas.
  }
}

function zoomBy(delta: number) {
  scale.value = Math.min(2.5, Math.max(0.5, Number((scale.value + delta).toFixed(2))))
}

function handleWheel(event: WheelEvent) {
  if (!tree.value) return
  zoomBy(event.deltaY < 0 ? 0.1 : -0.1)
}

function resetView() {
  scale.value = 1
  offset.value = { x: 0, y: 0 }
}

function outlineText(node: MindMapTreeNodeData, indent = ''): string {
  return `${indent}- ${node.label}\n${node.children.map((child) => outlineText(child, `${indent}  `)).join('')}`
}

async function copyOutline() {
  if (!tree.value) return
  const text = outlineText(tree.value)
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      fallbackCopy(text)
    }
    showCopyMessage('大纲已复制')
  } catch {
    try {
      fallbackCopy(text)
      showCopyMessage('大纲已复制')
    } catch {
      showCopyMessage('复制失败')
    }
  }
}

function fallbackCopy(text: string) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', 'true')
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  document.body.removeChild(textarea)
}

function showCopyMessage(message: string) {
  copyMessage.value = message
  if (copyTimer) window.clearTimeout(copyTimer)
  copyTimer = window.setTimeout(() => {
    copyMessage.value = ''
  }, 1800)
}
</script>

<template>
  <section class="relative flex h-full min-h-[560px] flex-col overflow-hidden rounded-md border border-[var(--color-border)] bg-[var(--color-card)]">
    <div v-if="mindmap" class="absolute left-4 right-4 top-4 z-20 flex flex-wrap items-center justify-between gap-3 rounded-md border border-[var(--color-border)] bg-[var(--color-card)]/95 px-4 py-3 shadow-sm backdrop-blur">
      <div class="min-w-0">
        <div class="flex items-center gap-2">
          <h2 class="truncate font-heading text-base font-semibold text-[var(--color-text)]">{{ mindmap.title }}</h2>
          <span class="rounded bg-[var(--color-bg-secondary)] px-1.5 py-0.5 text-[10px] text-[var(--color-text-tertiary)]">v{{ mindmap.version }}</span>
        </div>
        <p class="mt-0.5 text-xs text-[var(--color-text-tertiary)]">{{ mindmap.source_ids.length }} 个来源 · {{ mindmap.nodes.length }} 个节点</p>
      </div>

      <div class="flex items-center gap-2">
        <span v-if="copyMessage" class="text-xs text-[var(--color-success)]">{{ copyMessage }}</span>
        <button class="inline-flex items-center gap-1.5 rounded-md border border-[var(--color-border)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]" type="button" @click="copyOutline">
          <Copy :size="14" />
          复制大纲
        </button>
        <div class="h-4 w-px bg-[var(--color-border)]" />
        <button class="rounded-md border border-[var(--color-border)] p-1.5 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]" type="button" title="放大" @click="zoomBy(0.1)">
          <ZoomIn :size="14" />
        </button>
        <button class="rounded-md border border-[var(--color-border)] p-1.5 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]" type="button" title="缩小" @click="zoomBy(-0.1)">
          <ZoomOut :size="14" />
        </button>
        <button class="rounded-md border border-[var(--color-border)] p-1.5 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]" type="button" title="重置视图" @click="resetView">
          <RotateCcw :size="14" />
        </button>
        <span class="w-10 text-right text-[10px] text-[var(--color-text-tertiary)]">{{ scaleLabel }}</span>
      </div>
    </div>

    <div v-if="loading" class="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-[var(--color-card)]/90">
      <div class="h-9 w-9 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-accent)]" />
      <p class="text-sm font-medium text-[var(--color-text)]">AI 正在整理知识脉络</p>
      <p class="text-xs text-[var(--color-text-tertiary)]">正在生成层级导图，请稍后...</p>
    </div>

    <div
      v-else-if="tree"
      class="relative min-h-0 flex-1 cursor-grab overflow-hidden active:cursor-grabbing"
      @pointerdown="startPan"
      @pointermove="movePan"
      @pointerup="endPan"
      @pointercancel="endPan"
      @pointerleave="endPan"
      @wheel.prevent="handleWheel"
    >
      <div
        class="absolute origin-center select-none transition-transform duration-75"
        :style="{ left: '28%', top: '40%', transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})` }"
      >
        <div class="flex items-center">
          <MindMapTreeNode :node="tree" />
        </div>
      </div>
    </div>

    <div v-else class="flex min-h-[560px] flex-1 items-center justify-center px-6 text-center text-sm text-[var(--color-text-secondary)]">
      {{ emptyText }}
    </div>
  </section>
</template>
