<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Bot,
  ChevronRight,
  FileText,
  Folder,
  Library,
  Link,
  MessageSquare,
  Plus,
  Search,
  Send,
  Trash2,
  Upload,
  X,
} from '@lucide/vue'
import { chatApi } from '../api/chat'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'
import { knowledgeApi } from '../api/knowledge'
import { notesApi } from '../api/notes'
import { projectsApi } from '../api/projects'
import { sessionsApi } from '../api/sessions'
import { confirmDialog } from '../composables/useAppDialog'
import { useUserStore } from '../stores/useUserStore'
import type {
  ChatProject,
  ChatQueryRequest,
  ChatSession,
  ChatSourceRef,
  KnowledgeDocument,
  KnowledgeFolder,
  KnowledgeUploadProgress,
  Note,
  NoteFolder,
  ProjectSource,
  SSEMessage,
  SourceRefType,
} from '../types/api'

type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  references?: ChatSourceRef[]
  status?: 'thinking' | 'streaming' | 'done' | 'error'
  elapsedSeconds?: number
}

type MentionOption = ChatSourceRef & {
  title: string
  subtitle: string
}

type ReferenceFolder = {
  id: string
  name: string
  children?: ReferenceFolder[]
}

type ReferenceFile = {
  id: string
  folderId?: string | null
  title: string
  subtitle: string
  sourceType: SourceRefType
}

type ReferenceTreeRow = {
  key: string
  kind: 'folder' | 'file' | 'empty'
  title: string
  subtitle?: string
  depth: number
  count?: number
  sourceType?: SourceRefType
  sourceId?: string
  collapsed?: boolean
}

type MentionSection = {
  key: string
  title: string
  count: number
  icon: typeof FileText
  rows: ReferenceTreeRow[]
}

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const RAG_STORAGE_KEY = 'ragnotebook.chat.rag_enabled'

const projects = ref<ChatProject[]>([])
const normalSessions = ref<ChatSession[]>([])
const projectSessionMap = ref<Record<string, ChatSession[]>>({})
const projectSources = ref<ProjectSource[]>([])
const notes = ref<Note[]>([])
const docs = ref<KnowledgeDocument[]>([])
const noteFolders = ref<NoteFolder[]>([])
const knowledgeFolders = ref<KnowledgeFolder[]>([])
const messages = ref<ChatMessage[]>([])
const responseTimingBySession = ref<Record<string, number>>({})
const query = ref('')
const selectedRefs = ref<MentionOption[]>([])
const loading = ref(false)
const contextLoading = ref(false)
const errorMessage = ref('')
const thinkingMessage = ref('')
const uploadMessage = ref('')
const uploadProgress = ref(0)
const showMention = ref(false)
const mentionSearch = ref('')
const addSourceType = ref<SourceRefType>('note')
const addSourceId = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const knowledgeFileInput = ref<HTMLInputElement | null>(null)
const noteFileInput = ref<HTMLInputElement | null>(null)
const projectNameInput = ref<HTMLInputElement | null>(null)
const activeAssistantIndex = ref<number | null>(null)
const processingStartedAt = ref(0)
const processingElapsedSeconds = ref(0)
const createProjectModalOpen = ref(false)
const newProjectName = ref('')
const newProjectDescription = ref('')
const createProjectLoading = ref(false)
const createProjectError = ref('')
const ragEnabled = ref(localStorage.getItem(RAG_STORAGE_KEY) === 'true')
const collapsedReferenceFolderKeys = ref<Set<string>>(new Set())

const activeProjectId = computed(() => String(route.params.projectId || ''))
const activeSessionId = computed(() => String(route.params.sessionId || ''))
const isProjectMode = computed(() => Boolean(activeProjectId.value))
const activeProject = computed(() => projects.value.find((project) => project.id === activeProjectId.value) || null)
const effectiveRagEnabled = computed(() => ragEnabled.value || selectedRefs.value.length > 0)
const selectedReferenceKeys = computed(() => new Set(selectedRefs.value.map((ref) => `${ref.source_type}:${ref.source_id}`)))

const userId = computed(() => userStore.userInfo?.id || userStore.userInfo?.uuid || userStore.userInfo?.user_id || '')
const userAvatarLoadFailed = ref(false)
const userDisplayName = computed(() => userStore.userInfo?.username || userStore.userInfo?.email || '用户')
const userAvatarText = computed(() => {
  const name = userDisplayName.value.trim()
  return name ? name[0].toUpperCase() : 'U'
})
const userAvatarUrl = computed(() => {
  if (userAvatarLoadFailed.value) return ''
  return userStore.userInfo?.avatar?.trim() || ''
})

const projectSourceKeys = computed(() => new Set(projectSources.value.map((source) => `${source.source_type}:${source.source_id}`)))
const projectSourceByKey = computed(() => {
  const map = new Map<string, ProjectSource>()
  for (const source of projectSources.value) {
    map.set(`${source.source_type}:${source.source_id}`, source)
  }
  return map
})

const notesById = computed(() => new Map(notes.value.map((note) => [note.id, note])))
const docsById = computed(() => new Map(docs.value.map((doc) => [doc.id, doc])))
const projectNoteSourceCount = computed(() => projectSources.value.filter((source) => source.source_type === 'note').length)
const projectKnowledgeSourceCount = computed(() => projectSources.value.filter((source) => source.source_type === 'knowledge').length)

let processingTimer: number | undefined

const addSourceOptions = computed(() => {
  if (addSourceType.value === 'note') {
    return notes.value
      .filter((note) => !projectSourceKeys.value.has(`note:${note.id}`))
      .map((note) => ({ id: note.id, title: note.title || '未命名笔记' }))
  }
  return docs.value
    .filter((doc) => !projectSourceKeys.value.has(`knowledge:${doc.id}`))
    .map((doc) => ({ id: doc.id, title: doc.original_filename || doc.title || doc.filename }))
})

const globalNoteReferenceFiles = computed<ReferenceFile[]>(() => notes.value.map((note) => ({
    id: note.id,
    folderId: note.folder_id,
    title: note.title || '无标题',
    subtitle: note.category || '未分类',
    sourceType: 'note' as const,
})))

const globalKnowledgeReferenceFiles = computed<ReferenceFile[]>(() => docs.value.map((doc) => ({
  id: doc.id,
  folderId: doc.folder_id,
  title: getKnowledgeTitle(doc),
  subtitle: doc.status || 'ready',
  sourceType: 'knowledge' as const,
})))

const projectNoteReferenceFiles = computed<ReferenceFile[]>(() => projectSources.value
  .filter((source) => source.source_type === 'note')
  .map((source) => {
    const note = notesById.value.get(source.source_id)
    return {
      id: source.source_id,
      folderId: note?.folder_id,
      title: note?.title || source.title || '无标题',
      subtitle: note?.category || '项目笔记',
      sourceType: 'note' as const,
    }
  }))

const projectKnowledgeReferenceFiles = computed<ReferenceFile[]>(() => projectSources.value
  .filter((source) => source.source_type === 'knowledge')
  .map((source) => {
    const doc = docsById.value.get(source.source_id)
    return {
      id: source.source_id,
      folderId: doc?.folder_id,
      title: doc ? getKnowledgeTitle(doc) : source.title || '未命名文档',
      subtitle: source.status || doc?.status || 'ready',
      sourceType: 'knowledge' as const,
    }
  }))

const noteReferenceRows = computed(() => buildReferenceTreeRows(
  noteFolders.value,
  globalNoteReferenceFiles.value,
  '暂无笔记',
  collapsedReferenceFolderKeys.value,
  'global-note:',
  true,
))

const knowledgeReferenceRows = computed(() => buildReferenceTreeRows(
  knowledgeFolders.value,
  globalKnowledgeReferenceFiles.value,
  '暂无知识库文件',
  collapsedReferenceFolderKeys.value,
  'global-knowledge:',
  true,
))

const projectNoteReferenceRows = computed(() => buildReferenceTreeRows(
  noteFolders.value,
  projectNoteReferenceFiles.value,
  '暂无项目笔记',
  collapsedReferenceFolderKeys.value,
  'project-note:',
  true,
))

const projectKnowledgeReferenceRows = computed(() => buildReferenceTreeRows(
  knowledgeFolders.value,
  projectKnowledgeReferenceFiles.value,
  '暂无项目知识库文件',
  collapsedReferenceFolderKeys.value,
  'project-knowledge:',
  true,
))

const filteredMentionSections = computed<MentionSection[]>(() => {
  const keyword = mentionSearch.value.trim().toLowerCase()
  const collapsedKeys = keyword ? new Set<string>() : collapsedReferenceFolderKeys.value
  const noteFiles = filterMentionFiles(isProjectMode.value ? projectNoteReferenceFiles.value : globalNoteReferenceFiles.value, keyword)
  const knowledgeFiles = filterMentionFiles(isProjectMode.value ? projectKnowledgeReferenceFiles.value : globalKnowledgeReferenceFiles.value, keyword)
  const noteRows = buildReferenceTreeRows(noteFolders.value, noteFiles, '', collapsedKeys, 'mention-note:', !keyword)
    .filter((row) => row.kind !== 'empty')
  const knowledgeRows = buildReferenceTreeRows(knowledgeFolders.value, knowledgeFiles, '', collapsedKeys, 'mention-knowledge:', !keyword)
    .filter((row) => row.kind !== 'empty')

  return [
    { key: 'note', title: isProjectMode.value ? '项目笔记' : '笔记', count: noteFiles.length, icon: FileText, rows: noteRows },
    { key: 'knowledge', title: isProjectMode.value ? '项目知识库' : '知识库', count: knowledgeFiles.length, icon: Library, rows: knowledgeRows },
  ].filter((section) => section.rows.length)
})

function getSourceIcon(type: SourceRefType) {
  return type === 'note' ? FileText : Library
}

function handleUserAvatarError() {
  userAvatarLoadFailed.value = true
}

function getKnowledgeTitle(doc: KnowledgeDocument) {
  return doc.original_filename || doc.title || doc.filename || '未命名文档'
}

function filterMentionFiles(files: ReferenceFile[], keyword: string) {
  return files
    .filter((file) => !selectedReferenceKeys.value.has(`${file.sourceType}:${file.id}`))
    .filter((file) => !keyword || file.title.toLowerCase().includes(keyword) || file.subtitle.toLowerCase().includes(keyword))
}

function buildReferenceTreeRows(
  folders: ReferenceFolder[],
  files: ReferenceFile[],
  emptyTitle: string,
  folderStateKeys: ReadonlySet<string> = new Set<string>(),
  rowKeyPrefix = '',
  defaultCollapsed = false,
): ReferenceTreeRow[] {
  const rows: ReferenceTreeRow[] = []
  const filesByFolder = new Map<string, ReferenceFile[]>()

  for (const file of files) {
    const folderKey = file.folderId || ''
    const group = filesByFolder.get(folderKey) || []
    group.push(file)
    filesByFolder.set(folderKey, group)
  }

  const folderFileCount = (folder: ReferenceFolder): number => {
    const directCount = filesByFolder.get(folder.id)?.length || 0
    return directCount + (folder.children || []).reduce((sum, child) => sum + folderFileCount(child), 0)
  }

  const pushFileRows = (group: ReferenceFile[] | undefined, depth: number) => {
    for (const file of group || []) {
      rows.push({
        key: `${rowKeyPrefix}file:${file.sourceType}:${file.id}`,
        kind: 'file',
        title: file.title,
        subtitle: file.subtitle,
        depth,
        sourceType: file.sourceType,
        sourceId: file.id,
      })
    }
  }

  const walk = (items: ReferenceFolder[], depth: number) => {
    for (const folder of items) {
      const count = folderFileCount(folder)
      if (!count) continue
      const key = `${rowKeyPrefix}folder:${folder.id}`
      const collapsed = defaultCollapsed ? !folderStateKeys.has(key) : folderStateKeys.has(key)
      rows.push({
        key,
        kind: 'folder',
        title: folder.name,
        depth,
        count,
        collapsed,
      })
      if (!collapsed) {
        walk(folder.children || [], depth + 1)
        pushFileRows(filesByFolder.get(folder.id), depth + 1)
      }
    }
  }

  walk(folders, 0)

  const unfiledFiles = filesByFolder.get('')
  if (unfiledFiles?.length) {
    const key = `${rowKeyPrefix}folder:unfiled`
    const collapsed = defaultCollapsed ? !folderStateKeys.has(key) : folderStateKeys.has(key)
    rows.push({
      key,
      kind: 'folder',
      title: '未归档',
      depth: 0,
      count: unfiledFiles.length,
      collapsed,
    })
    if (!collapsed) {
      pushFileRows(unfiledFiles, 1)
    }
  }

  if (!rows.length) {
    rows.push({ key: `empty:${emptyTitle}`, kind: 'empty', title: emptyTitle, depth: 0 })
  }

  return rows
}

function removeTreeProjectSource(row: ReferenceTreeRow) {
  if (row.kind !== 'file' || !row.sourceType || !row.sourceId) return
  const source = projectSourceByKey.value.get(`${row.sourceType}:${row.sourceId}`)
  if (source) {
    void removeProjectSource(source)
  }
}

function mentionOptionFromRow(row: ReferenceTreeRow): MentionOption | null {
  if (row.kind !== 'file' || !row.sourceType || !row.sourceId) return null
  return {
    source_type: row.sourceType,
    source_id: row.sourceId,
    title: row.title,
    subtitle: row.subtitle || (row.sourceType === 'note' ? '笔记' : '知识库'),
  }
}

function addReference(option: MentionOption) {
  if (!selectedReferenceKeys.value.has(`${option.source_type}:${option.source_id}`)) {
    selectedRefs.value.push(option)
  }
  ragEnabled.value = true
}

function selectReferenceRow(row: ReferenceTreeRow) {
  const option = mentionOptionFromRow(row)
  if (!option) return
  addReference(option)
  showMention.value = false
  mentionSearch.value = ''
}

function selectMentionRow(row: ReferenceTreeRow) {
  const option = mentionOptionFromRow(row)
  if (option) {
    selectMention(option)
  }
}

function isReferenceSelected(row: ReferenceTreeRow) {
  return row.kind === 'file'
    && Boolean(row.sourceType && row.sourceId)
    && selectedReferenceKeys.value.has(`${row.sourceType}:${row.sourceId}`)
}

function toggleReferenceFolder(row: ReferenceTreeRow) {
  if (row.kind !== 'folder') return
  const nextKeys = new Set(collapsedReferenceFolderKeys.value)
  if (nextKeys.has(row.key)) {
    nextKeys.delete(row.key)
  } else {
    nextKeys.add(row.key)
  }
  collapsedReferenceFolderKeys.value = nextKeys
}

function sessionPath(session: ChatSession) {
  if (session.project_id) {
    return `/chat/project/${session.project_id}/session/${session.id}`
  }
  return `/chat/session/${session.id}`
}

function activeScopePath() {
  return activeProjectId.value ? `/chat/project/${activeProjectId.value}` : '/chat'
}

function sessionsForProject(projectId: string) {
  return projectSessionMap.value[projectId] || []
}

function formatSessionTime(value?: string | null) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const diffMs = Date.now() - date.getTime()
  if (diffMs >= 0) {
    const diffMinutes = Math.floor(diffMs / 60000)
    if (diffMinutes < 1) return '刚刚'
    if (diffMinutes < 60) return `${diffMinutes} 分`
    const diffHours = Math.floor(diffMinutes / 60)
    if (diffHours < 24) return `${diffHours} 小时`
    const diffDays = Math.floor(diffHours / 24)
    if (diffDays < 7) return `${diffDays} 天`
  }
  return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

async function scrollToBottom() {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

function startProcessingTimer(index: number) {
  clearProcessingTimer()
  activeAssistantIndex.value = index
  processingStartedAt.value = Date.now()
  processingElapsedSeconds.value = 0
  setAssistantStatus(index, 'thinking')
  updateProcessingElapsed(index)
  processingTimer = window.setInterval(() => {
    updateProcessingElapsed()
  }, 1000)
}

function finishProcessingTimer(status: NonNullable<ChatMessage['status']> = 'done') {
  const index = activeAssistantIndex.value
  const seconds = updateProcessingElapsed(index)
  if (processingTimer) {
    window.clearInterval(processingTimer)
    processingTimer = undefined
  }
  if (index !== null) {
    setAssistantStatus(index, status)
  }
  activeAssistantIndex.value = null
  processingStartedAt.value = 0
  return seconds
}

function clearProcessingTimer() {
  if (processingTimer) {
    window.clearInterval(processingTimer)
    processingTimer = undefined
  }
  activeAssistantIndex.value = null
  processingStartedAt.value = 0
  processingElapsedSeconds.value = 0
}

function updateProcessingElapsed(index = activeAssistantIndex.value) {
  if (index === null || !processingStartedAt.value) return processingElapsedSeconds.value
  const seconds = Math.max(0, Math.floor((Date.now() - processingStartedAt.value) / 1000))
  processingElapsedSeconds.value = seconds
  const message = messages.value[index]
  if (message?.role === 'assistant') {
    message.elapsedSeconds = seconds
  }
  return seconds
}

function setAssistantStatus(index: number, status: NonNullable<ChatMessage['status']>) {
  const message = messages.value[index]
  if (message?.role === 'assistant') {
    message.status = status
  }
}

function messageElapsedSeconds(message: ChatMessage, index: number) {
  if (message.role !== 'assistant') return null
  if (activeAssistantIndex.value === index) return processingElapsedSeconds.value
  return typeof message.elapsedSeconds === 'number' ? message.elapsedSeconds : null
}

function processingMetaLabel(message: ChatMessage, index: number) {
  const seconds = messageElapsedSeconds(message, index)
  if (seconds === null) return ''
  return `已处理 ${formatProcessingSeconds(seconds)}`
}

function formatProcessingSeconds(seconds: number) {
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return `${minutes}m ${String(rest).padStart(2, '0')}s`
}

function shouldShowThinkingPlaceholder(message: ChatMessage, index: number) {
  return message.role === 'assistant'
    && activeAssistantIndex.value === index
    && !message.content.trim()
}

async function loadSourceLibrary() {
  const [noteRes, docRes, noteFolderRes, knowledgeFolderRes] = await Promise.all([
    notesApi.list({ page: 1, page_size: 100 }),
    knowledgeApi.list(),
    notesApi.listFolders(),
    knowledgeApi.listFolders(),
  ])
  notes.value = noteRes.data.notes
  docs.value = docRes.data.documents
  noteFolders.value = noteFolderRes.data.folders
  knowledgeFolders.value = knowledgeFolderRes.data.folders
}

async function loadProjects() {
  const res = await projectsApi.list()
  projects.value = res.data.projects
}

async function loadSessions() {
  if (!userId.value) return
  const normalRes = await sessionsApi.list(userId.value, null)
  normalSessions.value = normalRes.data.sessions

  if (!projects.value.length) {
    projectSessionMap.value = {}
    return
  }

  const projectResults = await Promise.all(
    projects.value.map(async (project) => {
      const res = await sessionsApi.list(userId.value, project.id)
      return [project.id, res.data.sessions] as const
    }),
  )
  projectSessionMap.value = Object.fromEntries(projectResults)
}

async function loadProjectSources() {
  if (!activeProjectId.value) {
    projectSources.value = []
    return
  }
  const res = await projectsApi.sources(activeProjectId.value)
  projectSources.value = res.data.sources
}

async function loadSessionHistory(sessionId: string) {
  const res = await sessionsApi.get(sessionId)
  const historyMessages: ChatMessage[] = res.data.history.flatMap(([user, assistant]) => [
    { role: 'user' as const, content: user },
    { role: 'assistant' as const, content: assistant },
  ])
  const lastElapsed = responseTimingBySession.value[sessionId]
  if (typeof lastElapsed === 'number') {
    const lastAssistant = [...historyMessages].reverse().find((message) => message.role === 'assistant')
    if (lastAssistant) {
      lastAssistant.elapsedSeconds = lastElapsed
      lastAssistant.status = 'done'
    }
  }
  messages.value = historyMessages
  await scrollToBottom()
}

async function refreshWorkspace() {
  if (!userId.value) return
  contextLoading.value = true
  errorMessage.value = ''
  try {
    await Promise.all([loadProjects(), loadSourceLibrary()])
    await loadProjectSources()
    await loadSessions()
    if (activeSessionId.value) {
      await loadSessionHistory(activeSessionId.value)
    } else {
      messages.value = []
      selectedRefs.value = []
      thinkingMessage.value = ''
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载聊天工作区失败'
  } finally {
    contextLoading.value = false
  }
}

function openNormalChat() {
  void router.push('/chat')
}

function openProject(projectId: string) {
  void router.push(`/chat/project/${projectId}`)
}

function openSession(session: ChatSession) {
  void router.push(sessionPath(session))
}

function newChat() {
  clearProcessingTimer()
  messages.value = []
  selectedRefs.value = []
  query.value = ''
  void router.push(activeScopePath())
}

async function openCreateProjectModal() {
  newProjectName.value = ''
  newProjectDescription.value = ''
  createProjectError.value = ''
  createProjectModalOpen.value = true
  await nextTick()
  projectNameInput.value?.focus()
}

function closeCreateProjectModal() {
  if (createProjectLoading.value) return
  createProjectModalOpen.value = false
}

async function submitCreateProject() {
  const name = newProjectName.value.trim()
  if (!name) {
    createProjectError.value = '请输入项目名称'
    projectNameInput.value?.focus()
    return
  }

  createProjectLoading.value = true
  createProjectError.value = ''
  try {
    const res = await projectsApi.create({
      name,
      description: newProjectDescription.value.trim() || undefined,
    })
    createProjectModalOpen.value = false
    await loadProjects()
    void router.push(`/chat/project/${res.data.id}`)
  } catch (error) {
    createProjectError.value = error instanceof Error ? error.message : '项目创建失败'
  } finally {
    createProjectLoading.value = false
  }
}

async function deleteProject(project: ChatProject) {
  const confirmed = await confirmDialog({
    title: '删除项目',
    message: `确认删除项目「${project.name}」？项目内对话会删除，原笔记和知识库文件会保留。`,
    confirmText: '删除',
    variant: 'danger',
  })
  if (!confirmed) return
  await projectsApi.delete(project.id)
  await router.push('/chat')
  await refreshWorkspace()
}

async function deleteSession(session: ChatSession) {
  const confirmed = await confirmDialog({
    title: '删除对话',
    message: `确认删除「${session.title || '新的对话'}」？`,
    confirmText: '删除',
    variant: 'danger',
  })
  if (!confirmed) return
  await sessionsApi.delete(session.id)
  if (activeSessionId.value === session.id) {
    await router.push(activeScopePath())
  }
  await loadSessions()
}

function handleComposerInput() {
  const atIndex = query.value.lastIndexOf('@')
  if (atIndex < 0) {
    showMention.value = false
    mentionSearch.value = ''
    return
  }
  const fragment = query.value.slice(atIndex + 1)
  if (fragment.includes(' ') || fragment.includes('\n')) {
    showMention.value = false
    mentionSearch.value = ''
    return
  }
  mentionSearch.value = fragment
  showMention.value = true
}

function selectMention(option: MentionOption) {
  addReference(option)
  const atIndex = query.value.lastIndexOf('@')
  if (atIndex >= 0) {
    query.value = `${query.value.slice(0, atIndex)}@${option.title} `
  }
  showMention.value = false
  mentionSearch.value = ''
}

function removeReference(ref: ChatSourceRef) {
  selectedRefs.value = selectedRefs.value.filter((item) => !(item.source_type === ref.source_type && item.source_id === ref.source_id))
}

function toggleRag() {
  ragEnabled.value = !ragEnabled.value
}

function parseSseBlock(block: string): SSEMessage | null {
  const data = block
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
    .join('\n')
    .trim()
  if (!data || data === '[DONE]') return null
  return JSON.parse(data) as SSEMessage
}

async function send() {
  const current = query.value.trim()
  if (!current || loading.value) return

  const references = selectedRefs.value.map((ref) => ({ source_type: ref.source_type, source_id: ref.source_id }))
  const request: ChatQueryRequest = { query: current, rag_enabled: effectiveRagEnabled.value }
  if (activeSessionId.value) request.session_id = activeSessionId.value
  if (activeProjectId.value) request.project_id = activeProjectId.value
  if (references.length) request.references = references

  query.value = ''
  showMention.value = false
  thinkingMessage.value = ''
  errorMessage.value = ''
  messages.value.push({ role: 'user', content: current, references })
  loading.value = true
  messages.value.push({ role: 'assistant', content: '', status: 'thinking', elapsedSeconds: 0 })
  const assistantIndex = messages.value.length - 1
  startProcessingTimer(assistantIndex)
  await scrollToBottom()

  let returnedSessionId = activeSessionId.value
  let buffer = ''
  let responseElapsed = 0
  let processingFinished = false
  const finishCurrentResponse = (status: NonNullable<ChatMessage['status']>) => {
    if (!processingFinished) {
      responseElapsed = finishProcessingTimer(status)
      processingFinished = true
    }
    return responseElapsed
  }

  try {
    const response = await chatApi.queryStream(request)
    if (!response.ok) {
      throw new Error(`请求失败：${response.status}`)
    }
    const reader = response.body?.getReader()
    if (!reader) throw new Error('浏览器无法读取响应流')
    const decoder = new TextDecoder()

    const consumeBuffer = (flush = false) => {
      const blocks = buffer.split(/\r?\n\r?\n/)
      buffer = flush ? '' : blocks.pop() || ''
      for (const block of blocks) {
        const data = parseSseBlock(block)
        if (!data) continue
        if (data.session_id) returnedSessionId = data.session_id
        if (data.type === 'thinking' && data.content) {
          thinkingMessage.value = data.content
        }
        if (data.type === 'response' && data.content) {
          setAssistantStatus(assistantIndex, 'streaming')
          messages.value[assistantIndex].content += data.content
          void scrollToBottom()
        }
        if (data.type === 'error') {
          errorMessage.value = data.content || 'AI 响应失败'
        }
      }
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      consumeBuffer()
    }
    buffer += decoder.decode()
    consumeBuffer(true)
    finishCurrentResponse('done')
    if (returnedSessionId) {
      responseTimingBySession.value[returnedSessionId] = responseElapsed
    }

    selectedRefs.value = []
    await loadSessions()
    if (returnedSessionId && returnedSessionId !== activeSessionId.value) {
      const target = activeProjectId.value
        ? `/chat/project/${activeProjectId.value}/session/${returnedSessionId}`
        : `/chat/session/${returnedSessionId}`
      await router.replace(target)
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : '发送失败'
    errorMessage.value = message
    if (!processingFinished) {
      finishCurrentResponse('error')
      messages.value[assistantIndex].content = message
    }
  } finally {
    loading.value = false
    thinkingMessage.value = ''
  }
}

async function addExistingSource() {
  if (!activeProjectId.value || !addSourceId.value) return
  await projectsApi.addSources(activeProjectId.value, [{ source_type: addSourceType.value, source_id: addSourceId.value }])
  addSourceId.value = ''
  await loadProjectSources()
  await loadProjects()
}

async function removeProjectSource(source: ProjectSource) {
  if (!activeProjectId.value) return
  await projectsApi.removeSource(activeProjectId.value, { source_type: source.source_type, source_id: source.source_id })
  await loadProjectSources()
  await loadProjects()
}

function openKnowledgePicker() {
  knowledgeFileInput.value?.click()
}

function openNotePicker() {
  noteFileInput.value?.click()
}

async function uploadKnowledgeFiles(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  if (!activeProjectId.value || !files.length) return
  uploadMessage.value = '正在导入知识库文件...'
  uploadProgress.value = 0
  try {
    await projectsApi.uploadKnowledge(activeProjectId.value, files, (progress: KnowledgeUploadProgress) => {
      uploadProgress.value = progress.progress ?? uploadProgress.value
      uploadMessage.value = progress.filename ? `${progress.filename}：${progress.message || ''}` : progress.message || uploadMessage.value
    })
    uploadMessage.value = '知识库文件已导入项目'
    await Promise.all([loadProjectSources(), loadSourceLibrary(), loadProjects()])
  } catch (error) {
    uploadMessage.value = error instanceof Error ? error.message : '知识库导入失败'
  }
}

async function importNoteFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!activeProjectId.value || !file) return
  uploadMessage.value = '正在导入笔记...'
  try {
    await projectsApi.importNote(activeProjectId.value, file)
    uploadMessage.value = '笔记已导入项目'
    await Promise.all([loadProjectSources(), loadSourceLibrary(), loadProjects()])
  } catch (error) {
    uploadMessage.value = error instanceof Error ? error.message : '笔记导入失败'
  }
}

watch(() => [route.fullPath, userId.value], () => {
  void refreshWorkspace()
}, { immediate: true })

watch(() => userStore.userInfo?.avatar, () => {
  userAvatarLoadFailed.value = false
})

watch(ragEnabled, (value) => {
  localStorage.setItem(RAG_STORAGE_KEY, value ? 'true' : 'false')
})

onBeforeUnmount(() => {
  clearProcessingTimer()
})
</script>

<template>
  <div class="grid h-[calc(100vh-8rem)] gap-4 xl:grid-cols-[286px_minmax(0,1fr)_320px]">
    <aside class="flex min-h-0 flex-col rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
      <div class="p-3">
        <button
          class="flex h-9 w-full items-center justify-center gap-2 rounded-md bg-[var(--color-accent)] px-3 text-[15px] font-medium text-white"
          type="button"
          @click="newChat"
        >
          <Plus :size="16" />
          新对话
        </button>
      </div>

      <div class="min-h-0 flex-1 overflow-auto px-3 pb-3">
        <div class="mb-1 flex items-center justify-between px-1 text-[15px] font-medium text-[var(--color-text-tertiary)]">
          <span>项目</span>
          <button class="inline-flex h-7 w-7 items-center justify-center rounded-md text-[var(--color-text-secondary)] hover:bg-[var(--color-card)] hover:text-[var(--color-text)]" type="button" title="新建项目" @click="openCreateProjectModal">
            <Plus :size="15" />
          </button>
        </div>
        <div v-if="contextLoading && !projects.length" class="px-2 py-3 text-[15px] text-[var(--color-text-secondary)]">加载中</div>
        <div v-else class="space-y-1">
          <div v-for="project in projects" :key="project.id" class="space-y-1">
            <div
              class="group flex min-h-9 items-center gap-1 rounded-md"
              :class="activeProjectId === project.id && !activeSessionId ? 'bg-[var(--color-accent-bg)]' : 'hover:bg-[var(--color-card)]'"
            >
              <button
                class="flex min-w-0 flex-1 items-center gap-2 px-2.5 py-2 text-left text-[15px]"
                :class="activeProjectId === project.id ? 'text-[var(--color-text)]' : 'text-[var(--color-text-secondary)]'"
                type="button"
                @click="openProject(project.id)"
              >
                <Folder :size="16" class="shrink-0" />
                <span class="truncate">{{ project.name }}</span>
              </button>
              <span v-if="sessionsForProject(project.id).length" class="shrink-0 pr-1 text-[13px] text-[var(--color-text-tertiary)]">
                {{ sessionsForProject(project.id).length }}
              </span>
              <button
                class="mr-1 hidden h-7 w-7 shrink-0 items-center justify-center rounded-md text-[var(--color-text-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger)] group-hover:inline-flex"
                type="button"
                title="删除项目"
                @click.stop="deleteProject(project)"
              >
                <Trash2 :size="14" />
              </button>
            </div>

            <div v-if="sessionsForProject(project.id).length" class="ml-6 space-y-1">
              <div
                v-for="session in sessionsForProject(project.id)"
                :key="session.id"
                class="group flex min-h-8 items-center gap-1 rounded-md"
                :class="activeSessionId === session.id ? 'bg-[var(--color-card)] text-[var(--color-accent)] shadow-sm' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-card)] hover:text-[var(--color-text)]'"
              >
                <button class="min-w-0 flex-1 px-2 py-1.5 text-left" type="button" @click="openSession(session)">
                  <div class="flex min-w-0 items-center justify-between gap-2">
                    <span class="truncate text-[15px]">{{ session.title || '新的对话' }}</span>
                    <span class="shrink-0 text-[13px] text-[var(--color-text-tertiary)]">{{ formatSessionTime(session.updated_at) }}</span>
                  </div>
                </button>
                <button
                  class="mr-1 hidden h-7 w-7 shrink-0 items-center justify-center rounded-md text-[var(--color-text-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger)] group-hover:inline-flex"
                  type="button"
                  title="删除对话"
                  @click.stop="deleteSession(session)"
                >
                  <Trash2 :size="14" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="mb-1 mt-5 flex items-center justify-between px-1 text-[15px] font-medium text-[var(--color-text-tertiary)]">
          <span>对话</span>
          <span>{{ normalSessions.length }}</span>
        </div>
        <button
          class="mb-1 flex min-h-9 w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-[15px]"
          :class="!isProjectMode ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-card)] hover:text-[var(--color-text)]'"
          type="button"
          @click="openNormalChat"
        >
          <MessageSquare :size="16" class="shrink-0" />
          <span class="truncate">普通对话</span>
        </button>
        <div v-if="contextLoading" class="px-2 py-3 text-[15px] text-[var(--color-text-secondary)]">加载中</div>
        <div v-else-if="!normalSessions.length" class="px-2 py-3 text-[15px] text-[var(--color-text-secondary)]">暂无对话</div>
        <div v-else class="space-y-1">
          <div
            v-for="session in normalSessions"
            :key="session.id"
            class="group flex min-h-8 items-center gap-1 rounded-md"
            :class="activeSessionId === session.id ? 'bg-[var(--color-card)] text-[var(--color-accent)] shadow-sm' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-card)] hover:text-[var(--color-text)]'"
          >
            <button class="min-w-0 flex-1 px-2 py-1.5 text-left" type="button" @click="openSession(session)">
              <div class="flex min-w-0 items-center justify-between gap-2">
                <span class="truncate text-[15px]">{{ session.title || '新的对话' }}</span>
                <span class="shrink-0 text-[13px] text-[var(--color-text-tertiary)]">{{ formatSessionTime(session.updated_at) }}</span>
              </div>
            </button>
            <button
              class="mr-1 hidden h-7 w-7 shrink-0 items-center justify-center rounded-md text-[var(--color-text-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger)] group-hover:inline-flex"
              type="button"
              title="删除对话"
              @click.stop="deleteSession(session)"
            >
              <Trash2 :size="14" />
            </button>
          </div>
        </div>
      </div>
    </aside>

    <section class="flex min-h-0 flex-col rounded-md border border-[var(--color-border)] bg-[var(--color-card)]">
      <header class="flex items-center justify-between border-b border-[var(--color-border)] px-5 py-3">
        <div class="min-w-0">
          <h2 class="truncate font-heading text-lg font-semibold">{{ activeProject?.name || '普通对话' }}</h2>
          <p class="truncate text-sm text-[var(--color-text-secondary)]">
            {{ effectiveRagEnabled ? (isProjectMode ? '默认参考项目文件；输入 @ 可指定本轮参考文件' : '默认参考全局笔记和知识库；输入 @ 可指定文件') : '普通聊天；输入 @ 可指定文件并启用检索' }}
          </p>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <button
            class="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm"
            :class="effectiveRagEnabled ? 'border-[var(--color-accent)] bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]'"
            type="button"
            title="RAG 检索"
            :aria-pressed="effectiveRagEnabled"
            @click="toggleRag"
          >
            <Search :size="15" />
            RAG
          </button>
        </div>
      </header>

      <div ref="messagesContainer" class="min-h-0 flex-1 space-y-5 overflow-auto p-5">
        <div v-if="!messages.length" class="flex h-full items-center justify-center text-center text-sm text-[var(--color-text-secondary)]">
          <div>
            <MessageSquare :size="30" class="mx-auto mb-3 text-[var(--color-text-tertiary)]" />
            <p>{{ isProjectMode ? '在项目里开始一次带文件上下文的对话。' : '开始一次普通 AI 对话。' }}</p>
          </div>
        </div>
        <div
          v-for="(message, index) in messages"
          :key="index"
          class="flex w-full items-start gap-3"
          :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
        >
          <span
            v-if="message.role === 'assistant'"
            class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-[var(--color-border)] bg-[var(--color-bg-secondary)] text-[var(--color-accent)]"
            title="AI"
          >
            <Bot :size="18" />
          </span>

          <div class="min-w-0 max-w-[min(48rem,calc(100%-3.25rem))]">
            <div class="mb-1 flex items-center gap-2 text-xs text-[var(--color-text-tertiary)]" :class="message.role === 'user' ? 'justify-end' : 'justify-start'">
              <span>{{ message.role === 'user' ? userDisplayName : 'AI 助手' }}</span>
            </div>
            <div
              class="rounded-md border px-3 py-2.5 shadow-sm"
              :class="message.role === 'user'
                ? 'border-transparent bg-[var(--color-accent-bg)]'
                : 'border-[var(--color-border-light)] bg-[var(--color-bg-secondary)]'"
            >
              <div
                v-if="processingMetaLabel(message, index)"
                class="mb-3 border-b border-[var(--color-border)] pb-2 text-xs text-[var(--color-text-tertiary)]"
              >
                {{ processingMetaLabel(message, index) }}
              </div>
              <div v-if="message.references?.length" class="mb-2 flex flex-wrap gap-1">
                <span
                  v-for="sourceRef in message.references"
                  :key="`${sourceRef.source_type}:${sourceRef.source_id}`"
                  class="rounded-md bg-[var(--color-card)] px-2 py-0.5 text-xs text-[var(--color-text-secondary)]"
                >
                  @{{ sourceRef.source_type === 'note' ? '笔记' : '知识库' }}
                </span>
              </div>
              <p
                v-if="shouldShowThinkingPlaceholder(message, index)"
                class="text-sm text-[var(--color-text-tertiary)]"
                :title="thinkingMessage || '正在思考'"
              >
                正在思考
              </p>
              <MarkdownRenderer v-else :content="message.content" compact />
            </div>
          </div>

          <span
            v-if="message.role === 'user'"
            class="inline-flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[var(--color-accent)] text-sm font-medium text-white"
            :title="userDisplayName"
          >
            <img
              v-if="userAvatarUrl"
              :src="userAvatarUrl"
              :alt="userDisplayName"
              class="h-full w-full object-cover"
              @error="handleUserAvatarError"
            />
            <span v-else>{{ userAvatarText }}</span>
          </span>
        </div>
      </div>

      <div class="border-t border-[var(--color-border)] p-4">
        <p v-if="errorMessage" class="mb-2 text-sm text-[var(--color-danger)]">{{ errorMessage }}</p>

        <div v-if="selectedRefs.length" class="mb-2 flex flex-wrap gap-2">
          <button
            v-for="sourceRef in selectedRefs"
            :key="`${sourceRef.source_type}:${sourceRef.source_id}`"
            class="inline-flex items-center gap-1 rounded-md bg-[var(--color-accent-bg)] px-2 py-1 text-xs text-[var(--color-accent)]"
            type="button"
            @click="removeReference(sourceRef)"
          >
            @{{ sourceRef.title }}
            <X :size="13" />
          </button>
        </div>

        <div class="relative">
          <div
            v-if="showMention"
            class="absolute bottom-full left-0 z-20 mb-2 max-h-80 w-full overflow-auto rounded-md border border-[var(--color-border)] bg-[var(--color-card)] py-2 shadow-lg"
          >
            <div v-for="section in filteredMentionSections" :key="section.key" class="mb-2 last:mb-0">
              <div class="mb-1 flex items-center justify-between px-3 text-xs font-medium text-[var(--color-text-tertiary)]">
                <span class="inline-flex min-w-0 items-center gap-1.5">
                  <component :is="section.icon" :size="13" class="shrink-0" />
                  <span class="truncate">{{ section.title }}</span>
                </span>
                <span>{{ section.count }}</span>
              </div>
              <div
                v-for="row in section.rows"
                :key="row.key"
                class="flex min-h-8 items-center gap-2 pr-3 text-sm"
                :style="{ paddingLeft: `${0.75 + row.depth * 0.875}rem` }"
              >
                <template v-if="row.kind === 'folder'">
                  <button
                    class="flex min-w-0 flex-1 items-center gap-2 rounded-md py-1 pl-1 pr-1 text-left hover:bg-[var(--color-bg-secondary)]"
                    type="button"
                    :aria-expanded="!row.collapsed"
                    @click="toggleReferenceFolder(row)"
                  >
                    <ChevronRight :size="14" class="shrink-0 text-[var(--color-text-tertiary)] transition-transform duration-150" :class="{ 'rotate-90': !row.collapsed }" />
                    <Folder :size="15" class="shrink-0 text-[var(--color-text-tertiary)]" />
                    <span class="min-w-0 flex-1 truncate font-medium">{{ row.title }}</span>
                  </button>
                  <span class="shrink-0 text-xs text-[var(--color-text-tertiary)]">{{ row.count }}</span>
                </template>
                <button
                  v-else-if="row.kind === 'file'"
                  class="flex min-w-0 flex-1 items-start gap-2 rounded-md py-1 pl-1 pr-2 text-left hover:bg-[var(--color-bg-secondary)]"
                  type="button"
                  @click="selectMentionRow(row)"
                >
                  <component :is="getSourceIcon(row.sourceType || 'note')" :size="15" class="mt-0.5 shrink-0 text-[var(--color-text-tertiary)]" />
                  <span class="min-w-0">
                    <span class="block truncate">{{ row.title }}</span>
                    <span class="block truncate text-xs text-[var(--color-text-secondary)]">{{ row.subtitle }}</span>
                  </span>
                </button>
              </div>
            </div>
            <div v-if="!filteredMentionSections.length" class="px-3 py-3 text-sm text-[var(--color-text-secondary)]">没有可引用的文件</div>
          </div>

          <form class="flex items-end gap-3" @submit.prevent="send">
            <textarea
              v-model="query"
              class="min-h-14 flex-1 resize-none rounded-md border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm leading-6 outline-none focus:border-[var(--color-accent)]"
              rows="2"
              placeholder="输入问题，使用 @ 引用文件"
              @input="handleComposerInput"
              @keydown.enter.exact.prevent="send"
            />
            <button
              class="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-[var(--color-accent)] text-white disabled:cursor-not-allowed disabled:opacity-60"
              type="submit"
              :disabled="loading || !query.trim()"
              title="发送"
            >
              <Send :size="18" />
            </button>
          </form>
        </div>
      </div>
    </section>

    <aside v-if="isProjectMode" class="flex min-h-0 flex-col rounded-md border border-[var(--color-border)] bg-[var(--color-card)]">
      <header class="border-b border-[var(--color-border)] px-4 py-3">
        <div class="min-w-0">
          <h2 class="font-heading text-lg font-semibold">项目文件</h2>
          <p class="text-sm text-[var(--color-text-secondary)]">默认作为项目对话上下文</p>
        </div>
      </header>

      <div class="space-y-4 overflow-auto p-4">
        <div class="grid gap-2">
          <button class="inline-flex items-center justify-center gap-2 rounded-md border border-[var(--color-border)] px-3 py-2 text-sm" type="button" @click="openKnowledgePicker">
            <Upload :size="15" />
            导入知识库文件
          </button>
          <button class="inline-flex items-center justify-center gap-2 rounded-md border border-[var(--color-border)] px-3 py-2 text-sm" type="button" @click="openNotePicker">
            <FileText :size="15" />
            导入笔记
          </button>
          <input
            ref="knowledgeFileInput"
            class="sr-only"
            type="file"
            multiple
            accept=".pdf,.txt,.md,.markdown,.doc,.docx,.ppt,.pptx,application/pdf,text/plain,text/markdown,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation"
            @change="uploadKnowledgeFiles"
          />
          <input
            ref="noteFileInput"
            class="sr-only"
            type="file"
            accept=".md,.markdown,.txt,.doc,.docx,text/markdown,text/plain,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            @change="importNoteFile"
          />
        </div>

        <div v-if="uploadMessage" class="space-y-2 text-sm text-[var(--color-text-secondary)]">
          <div v-if="uploadProgress > 0" class="h-2 overflow-hidden rounded-full bg-[var(--color-bg-secondary)]">
            <div class="h-full rounded-full bg-[var(--color-accent)]" :style="{ width: `${Math.min(uploadProgress, 100)}%` }" />
          </div>
          <p>{{ uploadMessage }}</p>
        </div>

        <div class="rounded-md border border-[var(--color-border)] p-3">
          <div class="mb-2 flex items-center gap-2 text-sm font-medium">
            <Link :size="15" />
            关联已有文件
          </div>
          <div class="space-y-2">
            <select v-model="addSourceType" class="w-full rounded-md border border-[var(--color-border)] bg-transparent px-2 py-2 text-sm" @change="addSourceId = ''">
              <option value="note">笔记</option>
              <option value="knowledge">知识库</option>
            </select>
            <select v-model="addSourceId" class="w-full rounded-md border border-[var(--color-border)] bg-transparent px-2 py-2 text-sm">
              <option value="">选择文件</option>
              <option v-for="item in addSourceOptions" :key="item.id" :value="item.id">{{ item.title }}</option>
            </select>
            <button class="w-full rounded-md bg-[var(--color-accent)] px-3 py-2 text-sm text-white disabled:opacity-60" type="button" :disabled="!addSourceId" @click="addExistingSource">
              添加到项目
            </button>
          </div>
        </div>

        <div class="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
          <Search :size="15" />
          <span>{{ projectSources.length }} 个项目文件</span>
        </div>

        <section class="space-y-2">
          <div class="flex items-center justify-between text-sm font-medium">
            <span class="inline-flex items-center gap-2">
              <FileText :size="15" />
              笔记
            </span>
            <span class="text-xs text-[var(--color-text-tertiary)]">{{ projectNoteSourceCount }}</span>
          </div>
          <div class="rounded-md border border-[var(--color-border)] bg-[var(--color-card)] py-1">
            <div
              v-for="row in projectNoteReferenceRows"
              :key="row.key"
              class="flex min-h-8 items-center gap-2 pr-2 text-sm"
              :class="row.kind === 'empty' ? 'justify-center text-[var(--color-text-tertiary)]' : ''"
              :style="{ paddingLeft: row.kind === 'empty' ? '0.75rem' : `${0.5 + row.depth * 0.875}rem` }"
            >
              <template v-if="row.kind === 'folder'">
                <button
                  class="flex min-w-0 flex-1 items-center gap-2 rounded-md py-1 pl-1 pr-1 text-left hover:bg-[var(--color-bg-secondary)]"
                  type="button"
                  :aria-expanded="!row.collapsed"
                  @click="toggleReferenceFolder(row)"
                >
                  <ChevronRight :size="14" class="shrink-0 text-[var(--color-text-tertiary)] transition-transform duration-150" :class="{ 'rotate-90': !row.collapsed }" />
                  <Folder :size="15" class="shrink-0 text-[var(--color-text-tertiary)]" />
                  <span class="min-w-0 flex-1 truncate font-medium">{{ row.title }}</span>
                </button>
                <span class="shrink-0 text-xs text-[var(--color-text-tertiary)]">{{ row.count }}</span>
              </template>
              <template v-else-if="row.kind === 'file'">
                <button
                  class="flex min-w-0 flex-1 items-start gap-2 rounded-md py-1 pl-1 pr-2 text-left"
                  :class="isReferenceSelected(row) ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'hover:bg-[var(--color-bg-secondary)]'"
                  type="button"
                  title="引用该文件"
                  :aria-pressed="isReferenceSelected(row)"
                  @click="selectReferenceRow(row)"
                >
                  <FileText :size="15" class="mt-0.5 shrink-0 text-[var(--color-text-tertiary)]" />
                  <span class="min-w-0">
                    <span class="block truncate">{{ row.title }}</span>
                    <span class="block truncate text-xs text-[var(--color-text-secondary)]">{{ row.subtitle }}</span>
                  </span>
                </button>
                <button
                  class="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-[var(--color-text-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger)]"
                  type="button"
                  title="移除项目文件"
                  @click="removeTreeProjectSource(row)"
                >
                  <X :size="15" />
                </button>
              </template>
              <template v-else>
                {{ row.title }}
              </template>
            </div>
          </div>
        </section>

        <section class="space-y-2">
          <div class="flex items-center justify-between text-sm font-medium">
            <span class="inline-flex items-center gap-2">
              <Library :size="15" />
              知识库
            </span>
            <span class="text-xs text-[var(--color-text-tertiary)]">{{ projectKnowledgeSourceCount }}</span>
          </div>
          <div class="rounded-md border border-[var(--color-border)] bg-[var(--color-card)] py-1">
            <div
              v-for="row in projectKnowledgeReferenceRows"
              :key="row.key"
              class="flex min-h-8 items-center gap-2 pr-2 text-sm"
              :class="row.kind === 'empty' ? 'justify-center text-[var(--color-text-tertiary)]' : ''"
              :style="{ paddingLeft: row.kind === 'empty' ? '0.75rem' : `${0.5 + row.depth * 0.875}rem` }"
            >
              <template v-if="row.kind === 'folder'">
                <button
                  class="flex min-w-0 flex-1 items-center gap-2 rounded-md py-1 pl-1 pr-1 text-left hover:bg-[var(--color-bg-secondary)]"
                  type="button"
                  :aria-expanded="!row.collapsed"
                  @click="toggleReferenceFolder(row)"
                >
                  <ChevronRight :size="14" class="shrink-0 text-[var(--color-text-tertiary)] transition-transform duration-150" :class="{ 'rotate-90': !row.collapsed }" />
                  <Folder :size="15" class="shrink-0 text-[var(--color-text-tertiary)]" />
                  <span class="min-w-0 flex-1 truncate font-medium">{{ row.title }}</span>
                </button>
                <span class="shrink-0 text-xs text-[var(--color-text-tertiary)]">{{ row.count }}</span>
              </template>
              <template v-else-if="row.kind === 'file'">
                <button
                  class="flex min-w-0 flex-1 items-start gap-2 rounded-md py-1 pl-1 pr-2 text-left"
                  :class="isReferenceSelected(row) ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'hover:bg-[var(--color-bg-secondary)]'"
                  type="button"
                  title="引用该文件"
                  :aria-pressed="isReferenceSelected(row)"
                  @click="selectReferenceRow(row)"
                >
                  <Library :size="15" class="mt-0.5 shrink-0 text-[var(--color-text-tertiary)]" />
                  <span class="min-w-0">
                    <span class="block truncate">{{ row.title }}</span>
                    <span class="block truncate text-xs text-[var(--color-text-secondary)]">{{ row.subtitle }}</span>
                  </span>
                </button>
                <button
                  class="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-[var(--color-text-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger)]"
                  type="button"
                  title="移除项目文件"
                  @click="removeTreeProjectSource(row)"
                >
                  <X :size="15" />
                </button>
              </template>
              <template v-else>
                {{ row.title }}
              </template>
            </div>
          </div>
        </section>
      </div>
    </aside>

    <aside v-else class="flex min-h-0 flex-col rounded-md border border-[var(--color-border)] bg-[var(--color-card)]">
      <header class="border-b border-[var(--color-border)] px-4 py-3">
        <div class="min-w-0">
          <h2 class="font-heading text-lg font-semibold">参考文件</h2>
          <p class="text-sm text-[var(--color-text-secondary)]">普通对话</p>
        </div>
      </header>

      <div class="space-y-4 overflow-auto p-4">
        <div class="grid grid-cols-2 gap-2">
          <div class="rounded-md bg-[var(--color-bg-secondary)] px-3 py-3">
            <div class="flex items-center gap-2 text-xs text-[var(--color-text-secondary)]">
              <FileText :size="14" />
              笔记
            </div>
            <div class="mt-1 text-xl font-semibold">{{ notes.length }}</div>
          </div>
          <div class="rounded-md bg-[var(--color-bg-secondary)] px-3 py-3">
            <div class="flex items-center gap-2 text-xs text-[var(--color-text-secondary)]">
              <Library :size="14" />
              知识库
            </div>
            <div class="mt-1 text-xl font-semibold">{{ docs.length }}</div>
          </div>
        </div>

        <button
          class="flex w-full items-center justify-center gap-2 rounded-md border border-[var(--color-border)] px-3 py-2 text-sm hover:bg-[var(--color-bg-secondary)]"
          type="button"
          @click="openCreateProjectModal"
        >
          <Folder :size="15" />
          新建项目空间
        </button>

        <div class="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
          <Search :size="15" />
          <span>可引用文件</span>
        </div>

        <section class="space-y-2">
          <div class="flex items-center justify-between text-sm font-medium">
            <span class="inline-flex items-center gap-2">
              <FileText :size="15" />
              笔记
            </span>
            <span class="text-xs text-[var(--color-text-tertiary)]">{{ notes.length }}</span>
          </div>
          <div class="rounded-md border border-[var(--color-border)] bg-[var(--color-card)] py-1">
            <div
              v-for="row in noteReferenceRows"
              :key="row.key"
              class="flex min-h-8 items-center gap-2 pr-2 text-sm"
              :class="row.kind === 'empty' ? 'justify-center text-[var(--color-text-tertiary)]' : ''"
              :style="{ paddingLeft: row.kind === 'empty' ? '0.75rem' : `${0.5 + row.depth * 0.875}rem` }"
            >
              <template v-if="row.kind === 'folder'">
                <button
                  class="flex min-w-0 flex-1 items-center gap-2 rounded-md py-1 pl-1 pr-1 text-left hover:bg-[var(--color-bg-secondary)]"
                  type="button"
                  :aria-expanded="!row.collapsed"
                  @click="toggleReferenceFolder(row)"
                >
                  <ChevronRight :size="14" class="shrink-0 text-[var(--color-text-tertiary)] transition-transform duration-150" :class="{ 'rotate-90': !row.collapsed }" />
                  <Folder :size="15" class="shrink-0 text-[var(--color-text-tertiary)]" />
                  <span class="min-w-0 flex-1 truncate font-medium">{{ row.title }}</span>
                </button>
                <span class="shrink-0 text-xs text-[var(--color-text-tertiary)]">{{ row.count }}</span>
              </template>
              <template v-else-if="row.kind === 'file'">
                <button
                  class="flex min-w-0 flex-1 items-start gap-2 rounded-md py-1 pl-1 pr-2 text-left"
                  :class="isReferenceSelected(row) ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'hover:bg-[var(--color-bg-secondary)]'"
                  type="button"
                  title="引用该文件"
                  :aria-pressed="isReferenceSelected(row)"
                  @click="selectReferenceRow(row)"
                >
                  <FileText :size="15" class="mt-0.5 shrink-0 text-[var(--color-text-tertiary)]" />
                  <span class="min-w-0">
                    <span class="block truncate">{{ row.title }}</span>
                    <span class="block truncate text-xs text-[var(--color-text-secondary)]">{{ row.subtitle }}</span>
                  </span>
                </button>
              </template>
              <template v-else>
                {{ row.title }}
              </template>
            </div>
          </div>
        </section>

        <section class="space-y-2">
          <div class="flex items-center justify-between text-sm font-medium">
            <span class="inline-flex items-center gap-2">
              <Library :size="15" />
              知识库
            </span>
            <span class="text-xs text-[var(--color-text-tertiary)]">{{ docs.length }}</span>
          </div>
          <div class="rounded-md border border-[var(--color-border)] bg-[var(--color-card)] py-1">
            <div
              v-for="row in knowledgeReferenceRows"
              :key="row.key"
              class="flex min-h-8 items-center gap-2 pr-2 text-sm"
              :class="row.kind === 'empty' ? 'justify-center text-[var(--color-text-tertiary)]' : ''"
              :style="{ paddingLeft: row.kind === 'empty' ? '0.75rem' : `${0.5 + row.depth * 0.875}rem` }"
            >
              <template v-if="row.kind === 'folder'">
                <button
                  class="flex min-w-0 flex-1 items-center gap-2 rounded-md py-1 pl-1 pr-1 text-left hover:bg-[var(--color-bg-secondary)]"
                  type="button"
                  :aria-expanded="!row.collapsed"
                  @click="toggleReferenceFolder(row)"
                >
                  <ChevronRight :size="14" class="shrink-0 text-[var(--color-text-tertiary)] transition-transform duration-150" :class="{ 'rotate-90': !row.collapsed }" />
                  <Folder :size="15" class="shrink-0 text-[var(--color-text-tertiary)]" />
                  <span class="min-w-0 flex-1 truncate font-medium">{{ row.title }}</span>
                </button>
                <span class="shrink-0 text-xs text-[var(--color-text-tertiary)]">{{ row.count }}</span>
              </template>
              <template v-else-if="row.kind === 'file'">
                <button
                  class="flex min-w-0 flex-1 items-start gap-2 rounded-md py-1 pl-1 pr-2 text-left"
                  :class="isReferenceSelected(row) ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'hover:bg-[var(--color-bg-secondary)]'"
                  type="button"
                  title="引用该文件"
                  :aria-pressed="isReferenceSelected(row)"
                  @click="selectReferenceRow(row)"
                >
                  <Library :size="15" class="mt-0.5 shrink-0 text-[var(--color-text-tertiary)]" />
                  <span class="min-w-0">
                    <span class="block truncate">{{ row.title }}</span>
                    <span class="block truncate text-xs text-[var(--color-text-secondary)]">{{ row.subtitle }}</span>
                  </span>
                </button>
              </template>
              <template v-else>
                {{ row.title }}
              </template>
            </div>
          </div>
        </section>
      </div>
    </aside>
  </div>

  <Teleport to="body">
    <div
      v-if="createProjectModalOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/35 px-4 py-6"
      @click.self="closeCreateProjectModal"
    >
      <form
        class="w-full max-w-md overflow-hidden rounded-md border border-[var(--color-border)] bg-[var(--color-card)] shadow-2xl"
        @submit.prevent="submitCreateProject"
      >
        <header class="flex items-start justify-between gap-4 border-b border-[var(--color-border)] px-5 py-4">
          <div class="flex min-w-0 items-start gap-3">
            <span class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-[var(--color-accent-bg)] text-[var(--color-accent)]">
              <Folder :size="18" />
            </span>
            <div class="min-w-0">
              <h2 class="font-heading text-lg font-semibold">新建项目</h2>
              <p class="mt-0.5 text-sm text-[var(--color-text-secondary)]">把相关对话、笔记和知识库文件放在一起。</p>
            </div>
          </div>
          <button
            class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)] disabled:cursor-not-allowed disabled:opacity-50"
            type="button"
            title="关闭"
            :disabled="createProjectLoading"
            @click="closeCreateProjectModal"
          >
            <X :size="16" />
          </button>
        </header>

        <div class="space-y-4 px-5 py-4">
          <label class="block text-sm">
            <span class="font-medium">名称</span>
            <input
              ref="projectNameInput"
              v-model="newProjectName"
              class="mt-1 h-10 w-full rounded-md border border-[var(--color-border)] bg-transparent px-3 outline-none focus:border-[var(--color-accent)]"
              maxlength="120"
              placeholder="例如：论文阅读、产品资料、课程学习"
            />
          </label>
          <label class="block text-sm">
            <span class="font-medium">描述</span>
            <textarea
              v-model="newProjectDescription"
              class="mt-1 min-h-20 w-full resize-none rounded-md border border-[var(--color-border)] bg-transparent px-3 py-2 outline-none focus:border-[var(--color-accent)]"
              maxlength="300"
              placeholder="可选"
            />
          </label>
          <p v-if="createProjectError" class="text-sm text-[var(--color-danger)]">{{ createProjectError }}</p>
        </div>

        <footer class="flex justify-end gap-2 border-t border-[var(--color-border)] bg-[var(--color-bg)] px-5 py-4">
          <button
            class="rounded-md border border-[var(--color-border)] px-4 py-2 text-sm hover:bg-[var(--color-bg-secondary)] disabled:cursor-not-allowed disabled:opacity-50"
            type="button"
            :disabled="createProjectLoading"
            @click="closeCreateProjectModal"
          >
            取消
          </button>
          <button
            class="rounded-md bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
            type="submit"
            :disabled="createProjectLoading"
          >
            {{ createProjectLoading ? '创建中' : '创建项目' }}
          </button>
        </footer>
      </form>
    </div>
  </Teleport>
</template>
