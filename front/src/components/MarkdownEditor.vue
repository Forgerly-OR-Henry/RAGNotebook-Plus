<!--
模块职责：Vue 可复用组件，负责封装局部界面、交互状态和事件输出。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
<script setup lang="ts">
import { nextTick, ref, watch, type Component } from 'vue'
import { Columns2, Code2, Eye, Type } from '@lucide/vue'
import MarkdownRenderer from './MarkdownRenderer.vue'

/**
 * 类型：`EditorMode` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
type EditorMode = 'typora' | 'split' | 'source'

// 组件入参：由父组件传入业务对象、加载态和展示模式。
const props = defineProps<{ modelValue: string }>()
// 组件事件：向父组件报告关闭、保存、选择等交互结果。
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const mode = ref<EditorMode>('typora')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const isTyporaEditing = ref(false)
const sourceInput = ref<HTMLTextAreaElement | null>(null)

const editorModes: { value: EditorMode; label: string; icon: Component; title: string }[] = [
  { value: 'typora', label: '即时', icon: Type, title: '即时预览' },
  { value: 'split', label: '分屏', icon: Columns2, title: '分屏编辑' },
  { value: 'source', label: '源码', icon: Code2, title: 'Markdown 源码' },
]

/**
 * 用途：执行updateContent相关业务逻辑。
 * @param event 调用方传入的event参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function updateContent(event: Event) {
  const target = event.target as HTMLTextAreaElement
  emit('update:modelValue', target.value)
}

/**
 * 用途：执行setMode相关业务逻辑。
 * @param nextMode 调用方传入的nextMode参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function setMode(nextMode: EditorMode) {
  mode.value = nextMode
  if (nextMode !== 'typora') {
    isTyporaEditing.value = false
  }
}

/**
 * 用途：执行startTyporaEditing相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function startTyporaEditing() {
  if (mode.value !== 'typora') return
  isTyporaEditing.value = true
  await nextTick()
  sourceInput.value?.focus()
}

/**
 * 用途：执行stopTyporaEditing相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function stopTyporaEditing() {
  isTyporaEditing.value = false
}

// 状态监听：在关键输入变化后同步副作用或刷新页面数据。
watch(
  () => props.modelValue,
  () => {
    if (!props.modelValue && mode.value === 'typora') {
      isTyporaEditing.value = true
    }
  },
  { immediate: true }
)
</script>

<template>
  <section class="markdown-editor rounded-md border border-[var(--color-border)] bg-[var(--color-card)]">
    <div class="markdown-editor__toolbar">
      <div class="markdown-editor__mode-group" role="tablist" aria-label="笔记编辑模式">
        <button
          v-for="item in editorModes"
          :key="item.value"
          class="markdown-editor__mode-button"
          :class="{ 'is-active': mode === item.value }"
          type="button"
          :aria-selected="mode === item.value"
          :title="item.title"
          @click="setMode(item.value)"
        >
          <component :is="item.icon" :size="16" />
          <span>{{ item.label }}</span>
        </button>
      </div>
      <div class="markdown-editor__status">
        <Eye :size="15" />
        <span>Markdown</span>
      </div>
    </div>

    <div
      v-if="mode === 'typora'"
      class="markdown-editor__typora"
      :class="{ 'is-editing': isTyporaEditing }"
      @click="startTyporaEditing"
    >
      <textarea
        v-show="isTyporaEditing"
        ref="sourceInput"
        class="markdown-editor__textarea markdown-editor__textarea--typora"
        :value="modelValue"
        placeholder="# 写下标题&#10;&#10;支持标题、列表、引用、表格、任务列表、代码块和 LaTeX 公式。"
        spellcheck="false"
        @input="updateContent"
        @blur="stopTyporaEditing"
      />
      <MarkdownRenderer v-show="!isTyporaEditing" class="markdown-editor__preview" :content="modelValue" />
      <div v-if="!modelValue && !isTyporaEditing" class="markdown-editor__empty">开始写 Markdown</div>
    </div>

    <div v-else-if="mode === 'split'" class="markdown-editor__split">
      <textarea
        class="markdown-editor__textarea"
        :value="modelValue"
        placeholder="# 写下标题&#10;&#10;支持标题、列表、引用、表格、任务列表、代码块和 LaTeX 公式。"
        spellcheck="false"
        @input="updateContent"
      />
      <MarkdownRenderer class="markdown-editor__preview" :content="modelValue" />
    </div>

    <textarea
      v-else
      class="markdown-editor__textarea markdown-editor__textarea--source"
      :value="modelValue"
      placeholder="# 写下标题&#10;&#10;支持标题、列表、引用、表格、任务列表、代码块和 LaTeX 公式。"
      spellcheck="false"
      @input="updateContent"
    />
  </section>
</template>

<style scoped>
.markdown-editor {
  overflow: hidden;
}

.markdown-editor__toolbar {
  display: flex;
  min-height: 44px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-bg-secondary);
  padding: 6px 10px;
}

.markdown-editor__mode-group {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.markdown-editor__mode-button {
  display: inline-flex;
  height: 32px;
  align-items: center;
  gap: 6px;
  border-radius: 6px;
  padding: 0 10px;
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 1;
  transition: background 0.15s ease, color 0.15s ease;
}

.markdown-editor__mode-button:hover,
.markdown-editor__mode-button.is-active {
  background: var(--color-card);
  color: var(--color-accent);
}

.markdown-editor__status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-text-tertiary);
  font-size: 12px;
  white-space: nowrap;
}

.markdown-editor__typora {
  position: relative;
  min-height: 560px;
  cursor: text;
}

.markdown-editor__split {
  display: grid;
  min-height: 560px;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
}

.markdown-editor__split .markdown-editor__textarea {
  border-right: 1px solid var(--color-border-light);
}

.markdown-editor__textarea {
  min-height: 560px;
  width: 100%;
  resize: vertical;
  border: 0;
  background: transparent;
  color: var(--color-text);
  font-family: var(--font-mono);
  font-size: 15px;
  line-height: 1.75;
  outline: none;
  padding: 28px clamp(18px, 4vw, 52px) 80px;
  tab-size: 2;
}

.markdown-editor__textarea--typora {
  min-height: 560px;
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.8;
}

.markdown-editor__textarea--source {
  display: block;
}

.markdown-editor__preview {
  min-height: 560px;
  overflow-x: auto;
  padding: 28px clamp(18px, 4vw, 52px) 80px;
}

.markdown-editor__empty {
  position: absolute;
  left: clamp(18px, 4vw, 52px);
  top: 28px;
  color: var(--color-text-placeholder);
  pointer-events: none;
}

@media (max-width: 860px) {
  .markdown-editor__toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .markdown-editor__split {
    grid-template-columns: 1fr;
  }

  .markdown-editor__split .markdown-editor__textarea {
    border-right: 0;
    border-bottom: 1px solid var(--color-border-light);
  }

  .markdown-editor__mode-button {
    padding: 0 8px;
  }
}
</style>
