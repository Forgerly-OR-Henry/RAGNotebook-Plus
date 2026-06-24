<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import type { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight'
import ImageExtension from '@tiptap/extension-image'
import LinkExtension from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import TableExtension from '@tiptap/extension-table'
import TableCell from '@tiptap/extension-table-cell'
import TableHeader from '@tiptap/extension-table-header'
import TableRow from '@tiptap/extension-table-row'
import TaskItem from '@tiptap/extension-task-item'
import TaskList from '@tiptap/extension-task-list'
import Underline from '@tiptap/extension-underline'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import TurndownService from 'turndown'
import { common, createLowlight } from 'lowlight'
import MarkdownRenderer from './MarkdownRenderer.vue'
import {
  Bold,
  Code,
  Eye,
  FileCode,
  Heading1,
  Image,
  Italic,
  Link,
  List,
  ListChecks,
  ListOrdered,
  Minus,
  Quote,
  Redo2,
  Rows3,
  Strikethrough,
  Table,
  Type,
  Underline as UnderlineIcon,
  Undo2,
} from '@lucide/vue'
import { promptDialog } from '../composables/useAppDialog'

type AutocompleteFn = (context: string) => Promise<string | null>
type EditorMode = 'rich' | 'preview' | 'source'

const props = withDefaults(defineProps<{
  modelValue: string
  placeholder?: string
  autocomplete?: AutocompleteFn
}>(), {
  placeholder: '开始写作...',
  autocomplete: undefined,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const lowlight = createLowlight(common)
const updatingFromModel = ref(false)
const editorMode = ref<EditorMode>('rich')
const wrapperRef = ref<HTMLElement | null>(null)
const sourceInput = ref<HTMLTextAreaElement | null>(null)
const ghost = ref<{ text: string; left: number; top: number } | null>(null)
const ghostText = ref<string | null>(null)
const ghostFrom = ref(0)
let autocompleteTimer: number | undefined

const turndown = new TurndownService({
  headingStyle: 'atx',
  codeBlockStyle: 'fenced',
  bulletListMarker: '-',
  emDelimiter: '*',
  strongDelimiter: '**',
})

turndown.addRule('taskListItem', {
  filter: (node) => node.nodeName === 'LI' && (node as HTMLElement).getAttribute('data-type') === 'taskItem',
  replacement: (content, node) => {
    const li = node as HTMLElement
    const checked = li.getAttribute('data-checked') === 'true'
    const text = content.replace(/<[^>]*>/g, '').trim()
    return `- [${checked ? 'x' : ' '}] ${text}\n`
  },
})

function markdownToHtml(value: string) {
  const rawHtml = marked.parse(value || '', {
    async: false,
    breaks: true,
    gfm: true,
  }) as string

  return DOMPurify.sanitize(rawHtml, {
    USE_PROFILES: { html: true },
    ADD_ATTR: ['target', 'rel', 'checked', 'disabled'],
  })
}

function htmlToMarkdown(html: string) {
  const md = turndown.turndown(html)
  return md.trim() ? md : ''
}

function editorMarkdown(editorInstance: Editor) {
  return htmlToMarkdown(editorInstance.getHTML())
}

const editor = useEditor({
  extensions: [
    StarterKit.configure({
      heading: { levels: [1, 2, 3, 4, 5, 6] },
      codeBlock: false,
    }),
    CodeBlockLowlight.configure({ lowlight }),
    Placeholder.configure({ placeholder: props.placeholder }),
    ImageExtension,
    LinkExtension.configure({ openOnClick: false }),
    TableExtension.configure({ resizable: true }),
    TableRow,
    TableHeader,
    TableCell,
    TaskList,
    TaskItem.configure({ nested: true }),
    Underline,
  ],
  content: markdownToHtml(props.modelValue),
  editorProps: {
    attributes: {
      class: 'min-h-[560px] px-10 py-8 outline-none',
    },
  },
  onUpdate: ({ editor: currentEditor }) => {
    if (updatingFromModel.value) return
    emit('update:modelValue', editorMarkdown(currentEditor))
  },
})

const activeHeading = computed(() => {
  const currentEditor = editor.value
  if (!currentEditor) return '0'
  for (const level of [1, 2, 3, 4, 5, 6] as const) {
    if (currentEditor.isActive('heading', { level })) return String(level)
  }
  return '0'
})

const inTable = computed(() => editor.value?.isActive('table') ?? false)

function isRichMode() {
  return editorMode.value === 'rich'
}

async function setEditorMode(mode: EditorMode) {
  editorMode.value = mode
  clearGhost()

  if (mode === 'source') {
    await nextTick()
    sourceInput.value?.focus()
    return
  }

  if (mode === 'rich') {
    await nextTick()
    editor.value?.commands.focus()
  }
}

function updateSource(event: Event) {
  const target = event.target as HTMLTextAreaElement
  emit('update:modelValue', target.value)
}

function run(command: (editorInstance: Editor) => void) {
  const currentEditor = editor.value
  if (!currentEditor || !isRichMode()) return
  command(currentEditor)
}

function setHeading(value: string) {
  run((currentEditor) => {
    if (value === '0') {
      currentEditor.chain().focus().setParagraph().run()
      return
    }
    currentEditor.chain().focus().toggleHeading({ level: Number(value) as 1 | 2 | 3 | 4 | 5 | 6 }).run()
  })
}

async function addLink() {
  const currentEditor = editor.value
  if (!currentEditor) return
  const previous = currentEditor.getAttributes('link').href as string | undefined
  const href = await promptDialog({
    title: '插入链接',
    message: '输入链接地址',
    initialValue: previous || 'https://',
    placeholder: 'https://example.com',
  })
  if (href === null) return
  if (!href.trim()) {
    currentEditor.chain().focus().unsetLink().run()
    return
  }
  currentEditor.chain().focus().extendMarkRange('link').setLink({ href: href.trim() }).run()
}

async function addImage() {
  const currentEditor = editor.value
  if (!currentEditor) return
  const src = await promptDialog({
    title: '插入图片',
    message: '输入图片地址',
    placeholder: 'https://example.com/image.png',
  })
  if (!src?.trim()) return
  currentEditor.chain().focus().setImage({ src: src.trim() }).run()
}

function updateGhostPosition() {
  const currentEditor = editor.value
  const wrapper = wrapperRef.value
  if (!currentEditor || !wrapper || !ghostText.value) {
    ghost.value = null
    return
  }

  try {
    const coords = currentEditor.view.coordsAtPos(ghostFrom.value)
    const rect = wrapper.getBoundingClientRect()
    ghost.value = {
      text: ghostText.value,
      left: coords.left - rect.left,
      top: coords.top - rect.top,
    }
  } catch {
    ghost.value = null
  }
}

function clearGhost() {
  ghostText.value = null
  ghost.value = null
}

function scheduleAutocomplete() {
  window.clearTimeout(autocompleteTimer)
  clearGhost()
  const currentEditor = editor.value
  if (!currentEditor || !props.autocomplete) return

  autocompleteTimer = window.setTimeout(async () => {
    const latestEditor = editor.value
    if (!latestEditor || !props.autocomplete) return
    const { from } = latestEditor.state.selection
    const start = Math.max(0, from - 200)
    const context = latestEditor.state.doc.textBetween(start, from)
    try {
      const result = await props.autocomplete(context)
      if (!result) return
      ghostText.value = result
      ghostFrom.value = from
      updateGhostPosition()
    } catch {
      clearGhost()
    }
  }, 3000)
}

function handleKeydown(event: KeyboardEvent) {
  const currentEditor = editor.value
  if (!currentEditor) return
  const isCtrl = event.ctrlKey || event.metaKey

  if (event.key === 'Tab' && ghostText.value) {
    event.preventDefault()
    const { from } = currentEditor.state.selection
    currentEditor.view.dispatch(currentEditor.state.tr.insertText(ghostText.value, from))
    clearGhost()
    return
  }

  if (isCtrl && event.key === '/') {
    event.preventDefault()
    void setEditorMode(editorMode.value === 'preview' ? 'rich' : 'preview')
    return
  }

  if (isCtrl && event.key >= '1' && event.key <= '6') {
    event.preventDefault()
    const level = Number(event.key) as 1 | 2 | 3 | 4 | 5 | 6
    if (currentEditor.isActive('heading', { level })) {
      currentEditor.chain().focus().setParagraph().run()
    } else {
      currentEditor.chain().focus().toggleHeading({ level }).run()
    }
    return
  }

  if (isCtrl && event.key.toLowerCase() === 't') {
    event.preventDefault()
    currentEditor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
  }
}

watch(
  () => props.modelValue,
  (value) => {
    const currentEditor = editor.value
    if (!currentEditor) return
    if (editorMarkdown(currentEditor) === value) {
      scheduleAutocomplete()
      return
    }
    updatingFromModel.value = true
    currentEditor.commands.setContent(markdownToHtml(value || ''), false)
    updatingFromModel.value = false
    scheduleAutocomplete()
  },
)

watch(
  editor,
  (currentEditor, previousEditor) => {
    previousEditor?.view.dom.removeEventListener('keydown', handleKeydown)
    currentEditor?.view.dom.addEventListener('keydown', handleKeydown)
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  window.clearTimeout(autocompleteTimer)
  editor.value?.view.dom.removeEventListener('keydown', handleKeydown)
  editor.value?.destroy()
})

async function scrollToHeading(text: string, level: number) {
  if (editorMode.value !== 'rich') {
    await setEditorMode('rich')
  }

  const currentEditor = editor.value
  if (!currentEditor) return
  const normalize = (value: string) => value.replace(/\\([.![\]()*_`~-])/g, '$1').trim().toLowerCase()
  const target = normalize(text)

  currentEditor.state.doc.descendants((node, pos) => {
    if (node.type.name !== 'heading' || node.attrs.level !== level) return true
    const nodeText = normalize(node.textContent)
    if (nodeText === target || nodeText.startsWith(target) || target.startsWith(nodeText)) {
      const dom = currentEditor.view.nodeDOM(pos)
      if (dom instanceof HTMLElement) {
        dom.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
      currentEditor.commands.setTextSelection({ from: pos + 1, to: pos + 1 })
      currentEditor.commands.focus()
      return false
    }
    return true
  })
}

defineExpose({ scrollToHeading })
</script>

<template>
  <div ref="wrapperRef" class="tiptap-wrapper relative flex h-full min-h-0 flex-col rounded-md border border-[var(--color-border)] bg-[var(--color-card)]">
    <div class="tiptap-toolbar">
      <div v-if="editorMode === 'rich'" class="toolbar-inner">
        <button class="top-bar-item" :class="{ 'is-active': editor?.isActive('bold') }" type="button" title="加粗" @click="run((instance) => instance.chain().focus().toggleBold().run())">
          <Bold :size="15" />
        </button>
        <button class="top-bar-item" :class="{ 'is-active': editor?.isActive('italic') }" type="button" title="斜体" @click="run((instance) => instance.chain().focus().toggleItalic().run())">
          <Italic :size="15" />
        </button>
        <button class="top-bar-item" :class="{ 'is-active': editor?.isActive('underline') }" type="button" title="下划线" @click="run((instance) => instance.chain().focus().toggleUnderline().run())">
          <UnderlineIcon :size="15" />
        </button>
        <button class="top-bar-item" :class="{ 'is-active': editor?.isActive('strike') }" type="button" title="删除线" @click="run((instance) => instance.chain().focus().toggleStrike().run())">
          <Strikethrough :size="15" />
        </button>
        <button class="top-bar-item" :class="{ 'is-active': editor?.isActive('code') }" type="button" title="行内代码" @click="run((instance) => instance.chain().focus().toggleCode().run())">
          <Code :size="15" />
        </button>
        <span class="toolbar-divider" />

        <select class="toolbar-select" title="标题级别" :value="activeHeading" @change="setHeading(($event.target as HTMLSelectElement).value)">
          <option value="0">正文</option>
          <option value="1">H1</option>
          <option value="2">H2</option>
          <option value="3">H3</option>
          <option value="4">H4</option>
          <option value="5">H5</option>
          <option value="6">H6</option>
        </select>
        <button class="top-bar-item" type="button" title="一级标题" @click="setHeading('1')">
          <Heading1 :size="15" />
        </button>
        <span class="toolbar-divider" />

        <button class="top-bar-item" :class="{ 'is-active': editor?.isActive('bulletList') }" type="button" title="无序列表" @click="run((instance) => instance.chain().focus().toggleBulletList().run())">
          <List :size="15" />
        </button>
        <button class="top-bar-item" :class="{ 'is-active': editor?.isActive('orderedList') }" type="button" title="有序列表" @click="run((instance) => instance.chain().focus().toggleOrderedList().run())">
          <ListOrdered :size="15" />
        </button>
        <button class="top-bar-item" :class="{ 'is-active': editor?.isActive('taskList') }" type="button" title="任务列表" @click="run((instance) => instance.chain().focus().toggleTaskList().run())">
          <ListChecks :size="15" />
        </button>
        <button class="top-bar-item" :class="{ 'is-active': editor?.isActive('blockquote') }" type="button" title="引用" @click="run((instance) => instance.chain().focus().toggleBlockquote().run())">
          <Quote :size="15" />
        </button>
        <button class="top-bar-item" :class="{ 'is-active': editor?.isActive('codeBlock') }" type="button" title="代码块" @click="run((instance) => instance.chain().focus().toggleCodeBlock().run())">
          <FileCode :size="15" />
        </button>
        <span class="toolbar-divider" />

        <button class="top-bar-item" type="button" title="插入链接" @click="addLink">
          <Link :size="15" />
        </button>
        <button class="top-bar-item" type="button" title="插入图片" @click="addImage">
          <Image :size="15" />
        </button>
        <button class="top-bar-item" type="button" title="插入表格" @click="run((instance) => instance.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run())">
          <Table :size="15" />
        </button>
        <button v-if="inTable" class="top-bar-item" type="button" title="新增行" @click="run((instance) => instance.chain().focus().addRowAfter().run())">
          <Rows3 :size="15" />
        </button>
        <button v-if="inTable" class="top-bar-item" type="button" title="删除表格" @click="run((instance) => instance.chain().focus().deleteTable().run())">
          删除表
        </button>
        <button class="top-bar-item" type="button" title="分隔线" @click="run((instance) => instance.chain().focus().setHorizontalRule().run())">
          <Minus :size="15" />
        </button>
        <span class="toolbar-divider" />

        <button class="top-bar-item" type="button" title="撤销" @click="run((instance) => instance.chain().focus().undo().run())">
          <Undo2 :size="15" />
        </button>
        <button class="top-bar-item" type="button" title="重做" @click="run((instance) => instance.chain().focus().redo().run())">
          <Redo2 :size="15" />
        </button>
        <button class="top-bar-item" type="button" title="预览" @click="setEditorMode('preview')">
          <Eye :size="15" />
        </button>
      </div>

      <div v-else class="tiptap-toolbar__status">
        <Eye v-if="editorMode === 'preview'" :size="15" />
        <FileCode v-else :size="15" />
        <span>{{ editorMode === 'preview' ? 'Markdown 预览' : 'Markdown 源码' }}</span>
      </div>

      <div class="tiptap-mode-group" role="tablist" aria-label="笔记显示模式">
        <button class="tiptap-mode-button" :class="{ 'is-active': editorMode === 'rich' }" type="button" role="tab" :aria-selected="editorMode === 'rich'" title="富文本编辑" @click="setEditorMode('rich')">
          <Type :size="14" />
          <span>富文本</span>
        </button>
        <button class="tiptap-mode-button" :class="{ 'is-active': editorMode === 'preview' }" type="button" role="tab" :aria-selected="editorMode === 'preview'" title="Markdown 预览" @click="setEditorMode('preview')">
          <Eye :size="14" />
          <span>预览</span>
        </button>
        <button class="tiptap-mode-button" :class="{ 'is-active': editorMode === 'source' }" type="button" role="tab" :aria-selected="editorMode === 'source'" title="Markdown 源码" @click="setEditorMode('source')">
          <FileCode :size="14" />
          <span>源码</span>
        </button>
      </div>
    </div>

    <div v-if="editorMode === 'preview'" class="tiptap-preview-panel flex-1 overflow-auto">
      <MarkdownRenderer :content="modelValue" />
    </div>

    <div v-else-if="editorMode === 'source'" class="tiptap-source-panel flex-1 overflow-hidden">
      <textarea
        ref="sourceInput"
        class="tiptap-source-input"
        :value="modelValue"
        spellcheck="false"
        placeholder="# 一级标题&#10;&#10;## 二级标题&#10;&#10;**加粗**、*斜体*、列表、引用、表格和代码块。"
        @input="updateSource"
      />
      <aside class="tiptap-source-guide" aria-label="Markdown 源码说明">
        <h3>源码说明</h3>
        <dl>
          <div>
            <dt># / ## / ###</dt>
            <dd>一级、二级、三级标题</dd>
          </div>
          <div>
            <dt>**文字**</dt>
            <dd>加粗文字</dd>
          </div>
          <div>
            <dt>*文字*</dt>
            <dd>倾斜文字</dd>
          </div>
          <div>
            <dt>- / 1.</dt>
            <dd>无序或有序列表</dd>
          </div>
          <div>
            <dt>&gt; 引用</dt>
            <dd>引用块</dd>
          </div>
          <div>
            <dt>`code`</dt>
            <dd>行内代码</dd>
          </div>
        </dl>
      </aside>
    </div>

    <div v-else class="relative flex-1 overflow-auto">
      <div class="mx-auto max-w-3xl">
        <EditorContent :editor="editor" />
      </div>
      <div
        v-if="ghost"
        class="pointer-events-none absolute select-none text-[var(--color-text)]"
        :style="{ left: `${ghost.left}px`, top: `${ghost.top}px`, whiteSpace: 'pre' }"
      >
        <span class="opacity-30">{{ ghost.text }}</span>
        <span class="ml-1.5 inline-flex items-center rounded bg-[var(--color-accent-bg)] px-1.5 py-0.5 text-[11px] font-medium text-[var(--color-accent)]">Tab 补全</span>
      </div>
    </div>
  </div>
</template>
