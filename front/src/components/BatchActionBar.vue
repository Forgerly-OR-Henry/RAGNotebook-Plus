<!--
模块职责：Vue 可复用组件，负责封装局部界面、交互状态和事件输出。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
<script setup lang="ts">
import { Brain, Download, FolderInput, FolderTree, Pin, Trash2, X } from '@lucide/vue'

defineProps<{
  selectedCount: number
}>()

// 组件事件：向父组件报告关闭、保存、选择等交互结果。
const emit = defineEmits<{
  cancel: []
  delete: []
  download: []
  category: []
  folder: []
  mindmap: []
  pin: []
}>()
</script>

<template>
  <div class="mb-3 flex flex-wrap items-center gap-3 rounded-md border border-[var(--color-border)] bg-[var(--color-card)] px-5 py-3">
    <button class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text)]" type="button" @click="emit('cancel')">
      <X :size="14" />
      取消
    </button>
    <div class="flex-1 text-center text-sm font-medium text-[var(--color-accent)]">已选择 {{ selectedCount }} 篇</div>
    <div class="flex flex-wrap items-center gap-2">
      <button class="inline-flex items-center gap-1.5 rounded-md bg-[var(--color-bg-secondary)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text)]" type="button" @click="emit('pin')">
        <Pin :size="14" />
        置顶
      </button>
      <button class="inline-flex items-center gap-1.5 rounded-md bg-[var(--color-bg-secondary)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text)]" type="button" @click="emit('category')">
        <FolderTree :size="14" />
        分类
      </button>
      <button class="inline-flex items-center gap-1.5 rounded-md bg-[var(--color-bg-secondary)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text)]" type="button" @click="emit('folder')">
        <FolderInput :size="14" />
        移动
      </button>
      <button class="inline-flex items-center gap-1.5 rounded-md bg-[var(--color-bg-secondary)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text)]" type="button" @click="emit('mindmap')">
        <Brain :size="14" />
        导图
      </button>
      <button class="inline-flex items-center gap-1.5 rounded-md bg-[var(--color-bg-secondary)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text)]" type="button" @click="emit('download')">
        <Download :size="14" />
        下载
      </button>
      <button class="inline-flex items-center gap-1.5 rounded-md bg-red-500/10 px-3 py-1.5 text-xs text-red-500 hover:bg-red-500/20" type="button" @click="emit('delete')">
        <Trash2 :size="14" />
        删除
      </button>
    </div>
  </div>
</template>
