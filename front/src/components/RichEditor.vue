<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
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
  Underline as UnderlineIcon,
  Undo2,
} from '@lucide/vue'

type AutocompleteFn = (context: string) => Promise<string | null>

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
const preview = ref(false)
const wrapperRef = ref<HTMLElement | null>(null)
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
  return marked.parse(value || '', {
    async: false,
    breaks: true,
    gfm: true,
  }) as string
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

const renderedPreview = computed(() => {
  return DOMPurify.sanitize(markdownToHtml(props.modelValue), {
    USE_PROFILES: { html: true },
    ADD_ATTR: ['target', 'rel', 'checked'],
  })
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

function run(command: (editorInstance: Editor) => void) {
  const currentEditor = editor.value
  if (!currentEditor) return
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

function addLink() {
  run((currentEditor) => {
    const previous = currentEditor.getAttributes('link').href as string | undefined
    const href = window.prompt('输入链接地址', previous || 'https://')
    if (href === null) return
    if (!href.trim()) {
      currentEditor.chain().focus().unsetLink().run()
      return
    }
    currentEditor.chain().focus().extendMarkRange('link').setLink({ href: href.trim() }).run()
  })
}

function addImage() {
  run((currentEditor) => {
    const src = window.prompt('输入图片地址')
    if (!src?.trim()) return
    currentEditor.chain().focus().setImage({ src: src.trim() }).run()
  })
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
    preview.value = !preview.value
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

function scrollToHeading(text: string, level: number) {
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
      <div class="toolbar-inner">
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
        <button class="top-bar-item" :class="{ 'is-active': preview }" type="button" title="预览" @click="preview = !preview">
          <Eye :size="15" />
        </button>
      </div>
    </div>

    <div v-if="preview" class="flex-1 overflow-auto">
      <!-- eslint-disable-next-line vue/no-v-html -->
      <article class="markdown-body mx-auto max-w-3xl px-10 py-10" v-html="renderedPreview" />
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
