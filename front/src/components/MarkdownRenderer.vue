<!--
模块职责：Vue 可复用组件，负责封装局部界面、交互状态和事件输出。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdownHtml } from '../utils/markdown'

const props = withDefaults(defineProps<{
  content: string
  compact?: boolean
}>(), {
  compact: false,
})

/**
 * 用途：执行renderedHtml相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const renderedHtml = computed(() => renderMarkdownHtml(props.content || ''))
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html -->
  <article class="markdown-body markdown-renderer" :class="{ 'markdown-renderer--compact': compact }" data-i18n-skip v-html="renderedHtml" />
</template>

<style scoped>
.markdown-renderer {
  overflow-x: auto;
}

.markdown-renderer--compact {
  font-size: 14px;
  line-height: 1.7;
}

.markdown-renderer--compact :deep(h1) {
  font-size: 1.35rem;
}

.markdown-renderer--compact :deep(h2) {
  font-size: 1.2rem;
}

.markdown-renderer--compact :deep(h3) {
  font-size: 1.05rem;
}

.markdown-renderer--compact :deep(pre) {
  margin: 0.75em 0;
}

.markdown-renderer :deep(pre code.hljs) {
  display: block;
  color: #e1e4e8;
  line-height: 1.65;
}

.markdown-renderer :deep(.math-display) {
  margin: 1.15em 0 1.35em;
  overflow-x: auto;
  overflow-y: visible;
  padding: 0.25em 0 0.35em;
  line-height: 1.45;
}

.markdown-renderer :deep(.math-inline) {
  display: inline-flex;
  max-width: 100%;
  vertical-align: baseline;
}

.markdown-renderer :deep(.katex-display) {
  margin: 0;
}

.markdown-renderer :deep(.math-display .katex) {
  line-height: 1.35;
}
</style>
