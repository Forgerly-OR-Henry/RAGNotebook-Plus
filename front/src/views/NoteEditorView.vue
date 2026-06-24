<!--
模块职责：笔记编辑页，负责笔记内容编辑、模板、自动补全、关联片段和保存状态。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, ref, watch, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  BookMarked,
  BookOpen,
  Download,
  FileText,
  Folder,
  GraduationCap,
  GripVertical,
  Link2,
  ListTodo,
  ListTree,
  Plus,
  Save,
  Sparkles,
  Trash2,
  Users,
  X,
} from '@lucide/vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import OutlinePanel from '../components/OutlinePanel.vue'
import RelatedFragments from '../components/RelatedFragments.vue'
import TagInput from '../components/TagInput.vue'
import { readJsonPref, removePref, writeJsonPref } from '../api/localPrefs'
import { noteTemplatesApi } from '../api/noteTemplates'
import { notesApi } from '../api/notes'
import type { Note, NoteFolder, NoteTemplate } from '../types/api'

/**
 * 类型：`ApiError` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
type ApiError = {
  message?: string
  response?: {
    data?: {
      detail?: unknown
      message?: string
    }
  }
}

/**
 * 接口：`TemplateForm` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface TemplateForm {
  name: string
  title: string
  content: string
  category: string
  tags: string
}

/**
 * 接口：`RichEditorExpose` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface RichEditorExpose {
  scrollToHeading: (text: string, level: number) => void
}

/**
 * 接口：`FolderOption` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface FolderOption {
  id: string
  name: string
  depth: number
}

const route = useRoute()
const router = useRouter()
/**
 * 用途：执行RichEditor相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const RichEditor = defineAsyncComponent(() => import('../components/RichEditor.vue'))
const DRAFT_KEY = 'note_draft'
const TEMPLATE_ORDER_KEY = 'template_order'

const CATEGORIES = [
  { label: '工作', value: 'work' },
  { label: '学习', value: 'study' },
  { label: '生活', value: 'life' },
  { label: '技术', value: 'project' },
  { label: '其他', value: 'other' },
]

const CATEGORY_LABEL_MAP: Record<string, string> = {
  work: '工作',
  study: '学习',
  life: '生活',
  project: '技术',
  other: '其他',
}

const ICON_MAP: Record<string, Component> = {
  FileText,
  Users,
  GraduationCap,
  BookOpen,
  ListTodo,
  BookMarked,
}

// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const currentNoteId = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const title = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const content = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const category = ref('')
const tags = ref<string[]>([])
const folderId = ref<string | null>(null)
const folders = ref<NoteFolder[]>([])
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const loading = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const saving = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const deleting = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const aiTagging = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const message = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const errorMessage = ref('')
const saveStatus = ref<'unsaved' | 'saved'>('unsaved')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const showDelete = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const showRelated = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const showOutline = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const showTemplatePicker = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const showTemplateManager = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const showSaveAsTemplate = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const showNewTemplateForm = ref(false)
const templates = ref<NoteTemplate[]>([])
const templateItems = ref<NoteTemplate[]>([])
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const templateName = ref('')
const editingTemplate = ref<NoteTemplate | null>(null)
const editForm = ref<TemplateForm>({ name: '', title: '', content: '', category: '', tags: '' })
const newTemplateForm = ref<TemplateForm>({ name: '', title: '', content: '', category: '', tags: '' })
const dragItem = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)
const editorRef = ref<RichEditorExpose | null>(null)
let autosaveTimer: number | undefined

/**
 * 用途：执行isNew相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const isNew = computed(() => !currentNoteId.value)
/**
 * 用途：执行folderOptions相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const folderOptions = computed(() => flattenFolders(folders.value))

/**
 * 用途：执行routeNoteId相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function routeNoteId() {
  const raw = route.params.id
  if (Array.isArray(raw)) return raw[0] || ''
  return raw || ''
}

function draftField<T>(key: string, fallback: T): T {
  return (readJsonPref<Record<string, unknown>>(DRAFT_KEY, {})[key] ?? fallback) as T
}

/**
 * 用途：执行loadDraft相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function loadDraft() {
  title.value = draftField('title', '')
  content.value = draftField('content', '')
  category.value = draftField('category', '')
  tags.value = draftField('tags', [])
  folderId.value = draftField<string | null>('folder_id', null)
  saveStatus.value = 'saved'
}

/**
 * 用途：执行getApiErrorMessage相关业务逻辑。
 * @param error 调用方传入的error参数，用于驱动当前前端逻辑。
 * @param fallbackMessage 调用方传入的fallbackMessage参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function getApiErrorMessage(error: unknown, fallbackMessage: string) {
  const apiError = error as ApiError
  const detail = apiError.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message?: unknown }).message)
  }
  return apiError.response?.data?.message || apiError.message || fallbackMessage
}

/**
 * 用途：执行templateIcon相关业务逻辑。
 * @param icon 调用方传入的icon参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function templateIcon(icon: string) {
  return ICON_MAP[icon] || FileText
}

/**
 * 用途：执行categoryLabel相关业务逻辑。
 * @param value 调用方传入的value参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function categoryLabel(value: string | null | undefined) {
  return value ? CATEGORY_LABEL_MAP[value] || value : ''
}

/**
 * 用途：执行tagsFromInput相关业务逻辑。
 * @param value 调用方传入的value参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function tagsFromInput(value: string) {
  return value.split(/[，,]/).map((item) => item.trim()).filter(Boolean)
}

/**
 * 用途：执行templateTags相关业务逻辑。
 * @param template 调用方传入的template参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function templateTags(template: NoteTemplate) {
  return template.tags || []
}

/**
 * 用途：执行flattenFolders相关业务逻辑。
 * @param items 调用方传入的items参数，用于驱动当前前端逻辑。
 * @param depth 调用方传入的depth参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function flattenFolders(items: NoteFolder[], depth = 0): FolderOption[] {
  const options: FolderOption[] = []
  for (const folder of items) {
    options.push({ id: folder.id, name: folder.name, depth })
    options.push(...flattenFolders(folder.children || [], depth + 1))
  }
  return options
}

/**
 * 用途：执行queryFolderId相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function queryFolderId() {
  const raw = route.query.folder_id
  if (Array.isArray(raw)) return raw[0] || null
  return raw || null
}

/**
 * 用途：执行folderOptionLabel相关业务逻辑。
 * @param item 调用方传入的item参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function folderOptionLabel(item: FolderOption) {
  return `${'-- '.repeat(item.depth)}${item.name}`
}

/**
 * 用途：执行loadTemplateOrder相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function loadTemplateOrder(): string[] {
  return readJsonPref<string[]>(TEMPLATE_ORDER_KEY, [])
}

/**
 * 用途：执行saveTemplateOrder相关业务逻辑。
 * @param ids 调用方传入的ids参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function saveTemplateOrder(ids: string[]) {
  writeJsonPref(TEMPLATE_ORDER_KEY, ids)
}

/**
 * 用途：执行refreshTemplates相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function refreshTemplates() {
  try {
    const res = await noteTemplatesApi.list()
    const list = res.data || []
    templates.value = list
    const order = loadTemplateOrder()
    if (order.length === 0) {
      templateItems.value = list
      return
    }
    /**
     * 用途：执行map相关业务逻辑。
     * 参数：无显式业务参数。
     * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
     */
    const map = new Map(list.map((template) => [template.id, template]))
    /**
     * 用途：执行ordered相关业务逻辑。
     * 参数：无显式业务参数。
     * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
     */
    const ordered = order.map((id) => map.get(id)).filter((template): template is NoteTemplate => Boolean(template))
    /**
     * 用途：执行rest相关业务逻辑。
     * 参数：无显式业务参数。
     * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
     */
    const rest = list.filter((template) => !order.includes(template.id))
    templateItems.value = [...ordered, ...rest]
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '模板加载失败')
  }
}

/**
 * 用途：执行refreshFolders相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function refreshFolders() {
  try {
    const res = await notesApi.listFolders()
    folders.value = res.data.folders || []
    /**
     * 用途：执行known相关业务逻辑。
     * 参数：无显式业务参数。
     * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
     */
    const known = new Set(folderOptions.value.map((item) => item.id))
    if (folderId.value && !known.has(folderId.value)) {
      folderId.value = null
    }
  } catch {
    folders.value = []
  }
}

/**
 * 用途：执行loadNote相关业务逻辑。
 * @param id 调用方传入的id参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function loadNote(id: string) {
  loading.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    const res = await notesApi.get(id)
    const note = res.data as Note
    title.value = note.title || ''
    content.value = note.content || ''
    category.value = note.category || ''
    tags.value = note.tags || []
    folderId.value = note.folder_id || null
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '笔记加载失败')
  } finally {
    loading.value = false
  }
}

/**
 * 用途：执行applyTemplate相关业务逻辑。
 * @param template 调用方传入的template参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function applyTemplate(template: NoteTemplate) {
  title.value = template.title || ''
  content.value = template.content || ''
  category.value = template.category || ''
  tags.value = templateTags(template)
  showTemplatePicker.value = false
  saveStatus.value = 'unsaved'
}

/**
 * 用途：执行save相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function save() {
  if (saving.value || deleting.value) return currentNoteId.value || null
  if (!title.value.trim() && !content.value.trim()) return null

  saving.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    const payload = {
      title: title.value.trim() || '未命名笔记',
      content: content.value,
      category: category.value || undefined,
      tags: tags.value,
      folder_id: folderId.value,
    }

    if (isNew.value) {
      const res = await notesApi.create(payload)
      removePref(DRAFT_KEY)
      currentNoteId.value = res.data.id
      await router.replace(`/notes/${res.data.id}`)
      message.value = '已保存'
    } else {
      await notesApi.update(currentNoteId.value, payload)
      message.value = '已保存'
    }
    saveStatus.value = 'saved'
    return currentNoteId.value
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '保存失败，请稍后重试')
    return null
  } finally {
    saving.value = false
  }
}

/**
 * 用途：执行recognizeTagsWithAi相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function recognizeTagsWithAi() {
  if (aiTagging.value || deleting.value) return
  if (!title.value.trim() && !content.value.trim()) {
    errorMessage.value = '请先输入标题或内容后再使用 AI 识别'
    return
  }

  aiTagging.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    const noteId = currentNoteId.value || await save()
    if (!noteId) return
    const res = await notesApi.autoTag(noteId)
    category.value = res.data.category || ''
    tags.value = res.data.tags || []
    folderId.value = res.data.folder_id || folderId.value
    message.value = 'AI 识别完成'
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, 'AI 识别失败，请稍后重试')
  } finally {
    aiTagging.value = false
  }
}

/**
 * 用途：执行deleteCurrentNote相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function deleteCurrentNote() {
  if (!currentNoteId.value || deleting.value || saving.value) return
  deleting.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    await notesApi.delete(currentNoteId.value)
    await router.replace('/notes')
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '删除失败，请稍后重试')
  } finally {
    deleting.value = false
  }
}

/**
 * 用途：执行downloadCurrentNote相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function downloadCurrentNote() {
  if (!currentNoteId.value) return
  try {
    const blob = await notesApi.download(currentNoteId.value)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${title.value || 'note'}.md`
    document.body.appendChild(anchor)
    anchor.click()
    document.body.removeChild(anchor)
    URL.revokeObjectURL(url)
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '下载失败')
  }
}

/**
 * 用途：执行completeText相关业务逻辑。
 * @param context 调用方传入的context参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function completeText(context: string) {
  try {
    const res = await notesApi.autocomplete(context)
    return res.data.completion || null
  } catch {
    return null
  }
}

/**
 * 用途：执行saveAsTemplate相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function saveAsTemplate() {
  const name = templateName.value.trim()
  if (!name) return
  try {
    await noteTemplatesApi.create({
      name,
      title: title.value,
      content: content.value,
      category: category.value,
      tags: tags.value,
    })
    templateName.value = ''
    showSaveAsTemplate.value = false
    message.value = '模板已保存'
    await refreshTemplates()
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '保存模板失败')
  }
}

/**
 * 用途：执行startEditTemplate相关业务逻辑。
 * @param template 调用方传入的template参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function startEditTemplate(template: NoteTemplate) {
  editingTemplate.value = template
  showNewTemplateForm.value = false
  editForm.value = {
    name: template.name,
    title: template.title || '',
    content: template.content || '',
    category: template.category || '',
    tags: templateTags(template).join(', '),
  }
}

/**
 * 用途：执行updateTemplate相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function updateTemplate() {
  if (!editingTemplate.value) return
  try {
    await noteTemplatesApi.update(editingTemplate.value.id, {
      name: editForm.value.name,
      title: editForm.value.title,
      content: editForm.value.content,
      category: editForm.value.category,
      tags: tagsFromInput(editForm.value.tags),
    })
    editingTemplate.value = null
    await refreshTemplates()
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '模板更新失败')
  }
}

/**
 * 用途：执行createTemplate相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function createTemplate() {
  if (!newTemplateForm.value.name.trim()) return
  try {
    await noteTemplatesApi.create({
      name: newTemplateForm.value.name.trim(),
      title: newTemplateForm.value.title,
      content: newTemplateForm.value.content,
      category: newTemplateForm.value.category,
      tags: tagsFromInput(newTemplateForm.value.tags),
    })
    showNewTemplateForm.value = false
    newTemplateForm.value = { name: '', title: '', content: '', category: '', tags: '' }
    await refreshTemplates()
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '模板创建失败')
  }
}

/**
 * 用途：执行deleteTemplate相关业务逻辑。
 * @param template 调用方传入的template参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function deleteTemplate(template: NoteTemplate) {
  if (template.is_default) return
  try {
    await noteTemplatesApi.delete(template.id)
    await refreshTemplates()
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '模板删除失败')
  }
}

/**
 * 用途：执行handleTemplateDragStart相关业务逻辑。
 * @param index 调用方传入的index参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function handleTemplateDragStart(index: number) {
  dragItem.value = index
}

/**
 * 用途：执行handleTemplateDrop相关业务逻辑。
 * @param index 调用方传入的index参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function handleTemplateDrop(index: number) {
  const from = dragItem.value
  dragItem.value = null
  dragOverIndex.value = null
  if (from === null || from === index) return
  const next = [...templateItems.value]
  const [moved] = next.splice(from, 1)
  if (!moved) return
  next.splice(index, 0, moved)
  templateItems.value = next
  /**
   * 用途：执行ids相关业务逻辑。
   * 参数：无显式业务参数。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const ids = next.map((template) => template.id)
  saveTemplateOrder(ids)
  try {
    await noteTemplatesApi.reorder(ids)
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '排序保存失败')
  }
}

/**
 * 用途：执行openTemplateManager相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function openTemplateManager() {
  editingTemplate.value = null
  showNewTemplateForm.value = false
  showTemplateManager.value = true
}

/**
 * 用途：执行closeTemplateManager相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function closeTemplateManager() {
  editingTemplate.value = null
  showNewTemplateForm.value = false
  showTemplateManager.value = false
}

/**
 * 用途：执行toggleCategory相关业务逻辑。
 * @param value 调用方传入的value参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function toggleCategory(value: string) {
  category.value = category.value === value ? '' : value
}

// 状态监听：在关键输入变化后同步副作用或刷新页面数据。
watch(
  () => route.fullPath,
  async () => {
    const nextId = route.path === '/notes/new' ? '' : routeNoteId()
    currentNoteId.value = nextId
    showOutline.value = false
    showRelated.value = false
    if (!nextId) {
      loadDraft()
      folderId.value = queryFolderId() || folderId.value
      showTemplatePicker.value = true
      await refreshFolders()
      await refreshTemplates()
    } else {
      showTemplatePicker.value = false
      await refreshFolders()
      await loadNote(nextId)
    }
  },
  { immediate: true },
)

// 状态监听：在关键输入变化后同步副作用或刷新页面数据。
watch(
  [title, content, category, tags, folderId],
  () => {
    if (!isNew.value) return
    saveStatus.value = 'unsaved'
    window.clearTimeout(autosaveTimer)
    autosaveTimer = window.setTimeout(() => {
      writeJsonPref(DRAFT_KEY, {
        title: title.value,
        content: content.value,
        category: category.value,
        tags: tags.value,
        folder_id: folderId.value,
      })
      saveStatus.value = 'saved'
    }, 2000)
  },
  { deep: true },
)

// 状态监听：在关键输入变化后同步副作用或刷新页面数据。
watch(showTemplatePicker, (open) => {
  if (open) void refreshTemplates()
})

/**
 * 用途：执行handleGlobalKeydown相关业务逻辑。
 * @param event 调用方传入的event参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function handleGlobalKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
    event.preventDefault()
    void save()
  }
}

window.addEventListener('keydown', handleGlobalKeydown)

onBeforeUnmount(() => {
  window.clearTimeout(autosaveTimer)
  window.removeEventListener('keydown', handleGlobalKeydown)
})
</script>

<template>
  <div v-if="loading" class="flex h-[60vh] items-center justify-center">
    <div class="h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-accent)]" />
  </div>

  <div v-else-if="showTemplatePicker" class="mx-auto max-w-3xl space-y-6">
    <div class="flex items-center justify-between gap-3 border-b border-[var(--color-border-light)] pb-4">
      <span class="text-sm font-medium text-[var(--color-text)]">选择模板开始写作</span>
      <button class="rounded-md border border-[var(--color-border)] px-3 py-1 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]" type="button" @click="openTemplateManager">
        管理模板
      </button>
    </div>

    <p v-if="errorMessage" class="text-sm text-[var(--color-danger)]">{{ errorMessage }}</p>

    <div class="grid gap-4 sm:grid-cols-2">
      <button
        v-for="template in templates"
        :key="template.id"
        class="group flex flex-col items-start rounded-md border border-[var(--color-border)] bg-[var(--color-card)] p-5 text-left transition-colors hover:border-[var(--color-accent)]"
        type="button"
        @click="applyTemplate(template)"
      >
        <div class="mb-2 flex items-center gap-3">
          <component :is="templateIcon(template.icon)" :size="20" class="text-[var(--color-accent)]" />
          <span class="font-medium text-[var(--color-text)]">{{ template.name }}</span>
        </div>
        <p class="line-clamp-3 text-xs leading-relaxed text-[var(--color-text-secondary)]">{{ template.content || '从空白内容开始写作' }}</p>
        <div class="mt-3 flex flex-wrap items-center gap-2">
          <span v-if="template.category" class="text-xs text-[var(--color-text-tertiary)]">{{ categoryLabel(template.category) }}</span>
          <span v-for="tag in templateTags(template)" :key="tag" class="rounded-full bg-[var(--color-accent-bg)] px-2 py-0.5 text-xs text-[var(--color-accent)]">{{ tag }}</span>
        </div>
      </button>
    </div>
  </div>

  <div v-else class="flex h-[calc(100vh-7rem)] flex-col overflow-hidden bg-[var(--color-bg)]">
    <p v-if="errorMessage" class="mb-3 text-sm text-[var(--color-danger)]">{{ errorMessage }}</p>

    <div class="flex min-h-0 flex-1">
      <OutlinePanel :content="content" :open="showOutline" @close="showOutline = false" @heading-click="(text, level) => editorRef?.scrollToHeading(text, level)" />

      <main class="flex min-h-0 min-w-0 flex-1 flex-col">
        <div class="shrink-0 px-2 pb-5">
          <div class="flex flex-wrap items-center justify-between gap-4">
            <input v-model="title" class="min-w-0 flex-1 border-0 bg-transparent font-heading text-[30px] font-bold leading-tight text-[var(--color-text)] outline-none placeholder:text-[var(--color-text-placeholder)]" placeholder="未命名笔记" />

            <div class="flex shrink-0 items-center gap-1">
              <span v-if="isNew && saveStatus === 'saved'" class="mr-2 text-xs text-[var(--color-text-tertiary)]">草稿已保存</span>
              <span v-if="message" class="mr-2 text-xs text-[var(--color-success)]">{{ message }}</span>
              <button
                class="flex h-8 w-8 items-center justify-center rounded-md transition-colors"
                :class="showOutline ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'text-[var(--color-text-tertiary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]'"
                type="button"
                title="目录"
                @click="showOutline = !showOutline"
              >
                <ListTree :size="16" />
              </button>
              <span class="mx-0.5 h-5 w-px bg-[var(--color-border-light)]" />
              <button
                v-if="!isNew"
                class="flex h-8 w-8 items-center justify-center rounded-md transition-colors"
                :class="showRelated ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'text-[var(--color-text-tertiary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]'"
                type="button"
                title="关联片段"
                @click="showRelated = !showRelated"
              >
                <Link2 :size="16" />
              </button>
              <button v-if="!isNew" class="flex h-8 w-8 items-center justify-center rounded-md text-[var(--color-text-tertiary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]" type="button" title="下载" @click="downloadCurrentNote">
                <Download :size="16" />
              </button>
              <button v-if="!isNew" class="flex h-8 w-8 items-center justify-center rounded-md text-[var(--color-text-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger)]" type="button" title="删除" @click="showDelete = true">
                <Trash2 :size="16" />
              </button>
              <button v-if="!isNew" class="flex h-8 w-8 items-center justify-center rounded-md text-[var(--color-text-tertiary)] hover:bg-[var(--color-accent-bg)] hover:text-[var(--color-accent)]" type="button" title="存为模板" @click="showSaveAsTemplate = true">
                <Plus :size="16" />
              </button>
              <label class="ml-1 inline-flex h-8 shrink-0 items-center gap-1.5 rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-2.5 text-xs text-[var(--color-text-secondary)]">
                <Folder :size="13" />
                <select v-model="folderId" class="max-w-36 border-0 bg-transparent text-xs text-[var(--color-text)] outline-none">
                  <option :value="null">未归档</option>
                  <option v-for="item in folderOptions" :key="item.id" :value="item.id">{{ folderOptionLabel(item) }}</option>
                </select>
              </label>
              <button class="ml-1 inline-flex h-8 items-center gap-1.5 rounded-md bg-[var(--color-accent)] px-4 text-sm font-medium text-white hover:opacity-90 disabled:opacity-40" type="button" :disabled="saving || deleting" @click="save">
                <Save :size="15" />
                {{ saving ? '保存中' : '保存' }}
              </button>
            </div>
          </div>
        </div>

        <div class="shrink-0 px-2 pb-6">
          <div class="flex flex-wrap items-center gap-3">
            <div class="flex flex-wrap items-center gap-1">
              <button
                v-for="item in CATEGORIES"
                :key="item.value"
                class="rounded-full px-3 py-1 text-xs font-medium transition-colors"
                :class="category === item.value ? 'bg-[var(--color-accent)] text-white shadow-sm' : 'bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] hover:text-[var(--color-text)]'"
                type="button"
                @click="toggleCategory(item.value)"
              >
                {{ item.label }}
              </button>
            </div>
            <div class="min-w-44 flex-1">
              <TagInput v-model:tags="tags" placeholder="添加标签..." />
            </div>
            <button
              class="inline-flex h-8 shrink-0 items-center gap-1 rounded-md border border-[var(--color-border)] px-2.5 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-accent-bg)] hover:text-[var(--color-accent)] disabled:cursor-not-allowed disabled:opacity-60"
              type="button"
              :disabled="aiTagging || saving || deleting"
              title="自动识别分类并提炼关键词"
              @click="recognizeTagsWithAi"
            >
              <Sparkles :size="13" />
              {{ aiTagging ? '识别中' : 'AI识别' }}
            </button>
          </div>
        </div>

        <RichEditor ref="editorRef" v-model="content" :autocomplete="completeText" class="min-h-0 flex-1" placeholder="开始写作..." />
      </main>

      <RelatedFragments v-if="currentNoteId" :note-id="currentNoteId" :open="showRelated" @close="showRelated = false" />
    </div>
  </div>

  <Teleport to="body">
    <div v-if="showTemplateManager" class="fixed inset-0 z-50 bg-black/40" @click="closeTemplateManager" />
    <section v-if="showTemplateManager" class="fixed left-1/2 top-1/2 z-50 flex max-h-[86vh] w-[560px] max-w-[94vw] -translate-x-1/2 -translate-y-1/2 flex-col rounded-lg bg-[var(--color-card)] p-6 shadow-xl">
      <div class="mb-4 flex items-center justify-between gap-3">
        <h3 class="text-base font-medium text-[var(--color-text)]">管理模板</h3>
        <div class="flex items-center gap-2">
          <button v-if="!editingTemplate && !showNewTemplateForm" class="inline-flex items-center gap-1.5 rounded-md bg-[var(--color-accent)] px-3 py-1.5 text-xs text-white" type="button" @click="showNewTemplateForm = true">
            <Plus :size="14" />
            新建模板
          </button>
          <button class="text-[var(--color-text-tertiary)] hover:text-[var(--color-text)]" type="button" aria-label="关闭模板管理" @click="closeTemplateManager">
            <X :size="16" />
          </button>
        </div>
      </div>

      <div v-if="showNewTemplateForm" class="space-y-3 overflow-y-auto">
        <button class="text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text)]" type="button" @click="showNewTemplateForm = false">返回</button>
        <input v-model="newTemplateForm.name" class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-2 text-sm outline-none" placeholder="模板名称" />
        <input v-model="newTemplateForm.title" class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-2 text-sm outline-none" placeholder="笔记默认标题" />
        <select v-model="newTemplateForm.category" class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-2 text-sm outline-none">
          <option value="">无分类</option>
          <option v-for="item in CATEGORIES" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
        <input v-model="newTemplateForm.tags" class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-2 text-sm outline-none" placeholder="标签1, 标签2" />
        <textarea v-model="newTemplateForm.content" class="min-h-56 w-full resize-y rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-2 font-mono text-sm outline-none" placeholder="## 标题&#10;&#10;内容..." />
        <div class="flex justify-end gap-2">
          <button class="rounded-md border border-[var(--color-border)] px-4 py-1.5 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]" type="button" @click="showNewTemplateForm = false">取消</button>
          <button class="rounded-md bg-[var(--color-accent)] px-4 py-1.5 text-sm text-white disabled:opacity-40" type="button" :disabled="!newTemplateForm.name.trim()" @click="createTemplate">创建模板</button>
        </div>
      </div>

      <div v-else-if="editingTemplate" class="space-y-3 overflow-y-auto">
        <button class="text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text)]" type="button" @click="editingTemplate = null">返回</button>
        <input v-model="editForm.name" class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-2 text-sm outline-none" placeholder="模板名称" />
        <input v-model="editForm.title" class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-2 text-sm outline-none" placeholder="笔记默认标题" />
        <select v-model="editForm.category" class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-2 text-sm outline-none">
          <option value="">无分类</option>
          <option v-for="item in CATEGORIES" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
        <input v-model="editForm.tags" class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-2 text-sm outline-none" placeholder="标签1, 标签2" />
        <textarea v-model="editForm.content" class="min-h-56 w-full resize-y rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-2 font-mono text-sm outline-none" />
        <div class="flex justify-end gap-2">
          <button class="rounded-md border border-[var(--color-border)] px-4 py-1.5 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]" type="button" @click="editingTemplate = null">取消</button>
          <button class="rounded-md bg-[var(--color-accent)] px-4 py-1.5 text-sm text-white" type="button" @click="updateTemplate">保存修改</button>
        </div>
      </div>

      <div v-else class="flex-1 space-y-2 overflow-y-auto">
        <p v-if="templateItems.length === 0" class="py-8 text-center text-sm text-[var(--color-text-tertiary)]">暂无模板</p>
        <article
          v-for="(template, index) in templateItems"
          :key="template.id"
          class="flex items-start gap-3 rounded-md border border-[var(--color-border-light)] p-3"
          :class="dragOverIndex === index ? 'border-t-2 border-t-[var(--color-accent)] bg-[var(--color-bg-secondary)]' : ''"
          draggable="true"
          @dragstart="handleTemplateDragStart(index)"
          @dragover.prevent="dragOverIndex = index"
          @drop.prevent="handleTemplateDrop(index)"
          @dragend="dragOverIndex = null"
        >
          <GripVertical :size="15" class="mt-1 shrink-0 cursor-grab text-[var(--color-text-tertiary)]" />
          <component :is="templateIcon(template.icon)" :size="18" class="mt-0.5 shrink-0 text-[var(--color-accent)]" />
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <h4 class="truncate text-sm font-medium text-[var(--color-text)]">{{ template.name }}</h4>
              <span v-if="template.is_default" class="rounded bg-[var(--color-bg-secondary)] px-1.5 py-0.5 text-[10px] text-[var(--color-text-tertiary)]">内置</span>
            </div>
            <p class="mt-1 line-clamp-2 text-xs text-[var(--color-text-secondary)]">{{ template.content || '空白模板' }}</p>
            <div class="mt-2 flex flex-wrap gap-2">
              <span v-if="template.category" class="text-xs text-[var(--color-text-tertiary)]">{{ categoryLabel(template.category) }}</span>
              <span v-for="tag in templateTags(template)" :key="tag" class="rounded-full bg-[var(--color-accent-bg)] px-2 py-0.5 text-xs text-[var(--color-accent)]">{{ tag }}</span>
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-1">
            <button class="rounded px-2 py-1 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]" type="button" @click="startEditTemplate(template)">编辑</button>
            <button v-if="!template.is_default" class="rounded px-2 py-1 text-xs text-[var(--color-danger)] hover:bg-[var(--color-danger-bg)]" type="button" @click="deleteTemplate(template)">删除</button>
          </div>
        </article>
      </div>
    </section>
  </Teleport>

  <Teleport to="body">
    <div v-if="showSaveAsTemplate" class="fixed inset-0 z-50 bg-black/40" @click="showSaveAsTemplate = false" />
    <section v-if="showSaveAsTemplate" class="fixed left-1/2 top-1/2 z-50 w-[400px] max-w-[90vw] -translate-x-1/2 -translate-y-1/2 rounded-lg bg-[var(--color-card)] p-6 shadow-xl">
      <h3 class="mb-4 text-base font-medium text-[var(--color-text)]">保存为模板</h3>
      <input
        v-model="templateName"
        class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-2 text-sm outline-none placeholder:text-[var(--color-text-placeholder)] focus:ring-2 focus:ring-[var(--color-accent)]"
        placeholder="输入模板名称"
        @keydown.enter="saveAsTemplate"
      />
      <div class="mt-4 flex justify-end gap-2">
        <button class="rounded-md border border-[var(--color-border)] px-4 py-1.5 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]" type="button" @click="showSaveAsTemplate = false">取消</button>
        <button class="rounded-md bg-[var(--color-accent)] px-4 py-1.5 text-sm text-white disabled:opacity-40" type="button" :disabled="!templateName.trim()" @click="saveAsTemplate">保存</button>
      </div>
    </section>
  </Teleport>

  <ConfirmDialog
    v-model:open="showDelete"
    title="删除笔记"
    :message="`确认删除「${title || '未命名笔记'}」？删除后无法恢复。`"
    variant="danger"
    confirm-text="删除"
    @confirm="deleteCurrentNote"
  />
</template>
