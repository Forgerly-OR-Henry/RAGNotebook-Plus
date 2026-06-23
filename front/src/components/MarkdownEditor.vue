<script setup lang="ts">
import { computed, nextTick, ref, watch, type Component } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { Columns2, Code2, Eye, Type } from '@lucide/vue'

type EditorMode = 'typora' | 'split' | 'source'

const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const mode = ref<EditorMode>('typora')
const isTyporaEditing = ref(false)
const sourceInput = ref<HTMLTextAreaElement | null>(null)

const editorModes: { value: EditorMode; label: string; icon: Component; title: string }[] = [
  { value: 'typora', label: '即时', icon: Type, title: '即时预览' },
  { value: 'split', label: '分屏', icon: Columns2, title: '分屏编辑' },
  { value: 'source', label: '源码', icon: Code2, title: 'Markdown 源码' },
]

function updateContent(event: Event) {
  const target = event.target as HTMLTextAreaElement
  emit('update:modelValue', target.value)
}

function setMode(nextMode: EditorMode) {
  mode.value = nextMode
  if (nextMode !== 'typora') {
    isTyporaEditing.value = false
  }
}

async function startTyporaEditing() {
  if (mode.value !== 'typora') return
  isTyporaEditing.value = true
  await nextTick()
  sourceInput.value?.focus()
}

function stopTyporaEditing() {
  isTyporaEditing.value = false
}

const renderedHtml = computed(() => {
  const rawHtml = marked.parse(props.modelValue || '', {
    async: false,
    breaks: true,
    gfm: true,
  }) as string

  return DOMPurify.sanitize(rawHtml, {
    USE_PROFILES: { html: true },
    ADD_ATTR: ['target', 'rel'],
  })
})

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
        placeholder="# 写下标题&#10;&#10;支持标题、列表、引用、表格、任务列表和代码块。"
        spellcheck="false"
        @input="updateContent"
        @blur="stopTyporaEditing"
      />
      <!-- eslint-disable-next-line vue/no-v-html -->
      <article v-show="!isTyporaEditing" class="markdown-body markdown-editor__preview" v-html="renderedHtml" />
      <div v-if="!modelValue && !isTyporaEditing" class="markdown-editor__empty">开始写 Markdown</div>
    </div>

    <div v-else-if="mode === 'split'" class="markdown-editor__split">
      <textarea
        class="markdown-editor__textarea"
        :value="modelValue"
        placeholder="# 写下标题&#10;&#10;支持标题、列表、引用、表格、任务列表和代码块。"
        spellcheck="false"
        @input="updateContent"
      />
      <!-- eslint-disable-next-line vue/no-v-html -->
      <article class="markdown-body markdown-editor__preview" v-html="renderedHtml" />
    </div>

    <textarea
      v-else
      class="markdown-editor__textarea markdown-editor__textarea--source"
      :value="modelValue"
      placeholder="# 写下标题&#10;&#10;支持标题、列表、引用、表格、任务列表和代码块。"
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
