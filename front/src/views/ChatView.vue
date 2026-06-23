<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
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
import { knowledgeApi } from '../api/knowledge'
import { notesApi } from '../api/notes'
import { projectsApi } from '../api/projects'
import { sessionsApi } from '../api/sessions'
import { useUserStore } from '../stores/useUserStore'
import type {
  ChatProject,
  ChatQueryRequest,
  ChatSession,
  ChatSourceRef,
  KnowledgeDocument,
  KnowledgeUploadProgress,
  Note,
  ProjectSource,
  SSEMessage,
  SourceRefType,
} from '../types/api'

type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  references?: ChatSourceRef[]
}

type MentionOption = ChatSourceRef & {
  title: string
  subtitle: string
}

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const RAG_STORAGE_KEY = 'ragnotebook.chat.rag_enabled'

const projects = ref<ChatProject[]>([])
const normalSessions = ref<ChatSession[]>([])
const projectSessions = ref<ChatSession[]>([])
const projectSources = ref<ProjectSource[]>([])
const notes = ref<Note[]>([])
const docs = ref<KnowledgeDocument[]>([])
const messages = ref<ChatMessage[]>([])
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
const createProjectModalOpen = ref(false)
const newProjectName = ref('')
const newProjectDescription = ref('')
const createProjectLoading = ref(false)
const createProjectError = ref('')
const ragEnabled = ref(localStorage.getItem(RAG_STORAGE_KEY) !== 'false')

const activeProjectId = computed(() => String(route.params.projectId || ''))
const activeSessionId = computed(() => String(route.params.sessionId || ''))
const isProjectMode = computed(() => Boolean(activeProjectId.value))
const activeProject = computed(() => projects.value.find((project) => project.id === activeProjectId.value) || null)
const effectiveRagEnabled = computed(() => ragEnabled.value || selectedRefs.value.length > 0)

const userId = computed(() => userStore.userInfo?.id || userStore.userInfo?.uuid || userStore.userInfo?.user_id || '')

const globalMentionOptions = computed<MentionOption[]>(() => [
  ...notes.value.map((note) => ({
    source_type: 'note' as const,
    source_id: note.id,
    title: note.title || '未命名笔记',
    subtitle: `笔记 · ${note.category || '未分类'}`,
  })),
  ...docs.value.map((doc) => ({
    source_type: 'knowledge' as const,
    source_id: doc.id,
    title: doc.original_filename || doc.title || doc.filename,
    subtitle: `知识库 · ${doc.status || 'ready'}`,
  })),
])

const projectMentionOptions = computed<MentionOption[]>(() => projectSources.value.map((source) => ({
  source_type: source.source_type,
  source_id: source.source_id,
  title: source.title,
  subtitle: source.source_type === 'note' ? '项目笔记' : `项目知识库 · ${source.status || 'ready'}`,
})))

const mentionOptions = computed(() => isProjectMode.value ? projectMentionOptions.value : globalMentionOptions.value)

const filteredMentionOptions = computed(() => {
  const keyword = mentionSearch.value.trim().toLowerCase()
  const selectedKeys = new Set(selectedRefs.value.map((ref) => `${ref.source_type}:${ref.source_id}`))
  return mentionOptions.value
    .filter((item) => !selectedKeys.has(`${item.source_type}:${item.source_id}`))
    .filter((item) => !keyword || item.title.toLowerCase().includes(keyword) || item.subtitle.toLowerCase().includes(keyword))
    .slice(0, 8)
})

const projectSourceKeys = computed(() => new Set(projectSources.value.map((source) => `${source.source_type}:${source.source_id}`)))

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

function getSourceIcon(type: SourceRefType) {
  return type === 'note' ? FileText : Library
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

function formatDate(value?: string | null) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

async function scrollToBottom() {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

async function loadSourceLibrary() {
  const [noteRes, docRes] = await Promise.all([
    notesApi.list({ page: 1, page_size: 100 }),
    knowledgeApi.list(),
  ])
  notes.value = noteRes.data.notes
  docs.value = docRes.data.documents
}

async function loadProjects() {
  const res = await projectsApi.list()
  projects.value = res.data.projects
}

async function loadSessions() {
  if (!userId.value) return
  const normalRes = await sessionsApi.list(userId.value, null)
  normalSessions.value = normalRes.data.sessions

  if (!activeProjectId.value) {
    projectSessions.value = []
    return
  }

  const projectRes = await sessionsApi.list(userId.value, activeProjectId.value)
  projectSessions.value = projectRes.data.sessions
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
  messages.value = res.data.history.flatMap(([user, assistant]) => [
    { role: 'user' as const, content: user },
    { role: 'assistant' as const, content: assistant },
  ])
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
  const confirmed = window.confirm(`确认删除项目「${project.name}」？项目内对话会删除，原笔记和知识库文件会保留。`)
  if (!confirmed) return
  await projectsApi.delete(project.id)
  await router.push('/chat')
  await refreshWorkspace()
}

async function deleteSession(session: ChatSession) {
  const confirmed = window.confirm(`确认删除「${session.title || '新的对话'}」？`)
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
  if (!selectedRefs.value.some((ref) => ref.source_type === option.source_type && ref.source_id === option.source_id)) {
    selectedRefs.value.push(option)
  }
  ragEnabled.value = true
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
  messages.value.push({ role: 'assistant', content: '' })
  await scrollToBottom()

  loading.value = true
  let returnedSessionId = activeSessionId.value
  let buffer = ''
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
          messages.value[messages.value.length - 1].content += data.content
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
    messages.value[messages.value.length - 1].content = message
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

watch(ragEnabled, (value) => {
  localStorage.setItem(RAG_STORAGE_KEY, value ? 'true' : 'false')
})
</script>

<template>
  <div class="grid h-[calc(100vh-8rem)] gap-4 xl:grid-cols-[270px_minmax(0,1fr)_320px]">
    <aside class="flex min-h-0 flex-col rounded-md border border-[var(--color-border)] bg-[var(--color-card)]">
      <div class="border-b border-[var(--color-border)] p-3">
        <button
          class="flex w-full items-center justify-center gap-2 rounded-md bg-[var(--color-accent)] px-3 py-2 text-sm font-medium text-white"
          type="button"
          @click="newChat"
        >
          <Plus :size="16" />
          新对话
        </button>
      </div>

      <div class="min-h-0 flex-1 overflow-auto p-3">
        <button
          class="mb-3 flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm"
          :class="!isProjectMode ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]'"
          type="button"
          @click="openNormalChat"
        >
          <MessageSquare :size="16" />
          普通对话
        </button>

        <div class="mb-2 flex items-center justify-between px-1 text-xs font-medium uppercase text-[var(--color-text-tertiary)]">
          <span>项目</span>
          <button class="inline-flex h-7 w-7 items-center justify-center rounded-md hover:bg-[var(--color-bg-secondary)]" type="button" title="新建项目" @click="openCreateProjectModal">
            <Plus :size="15" />
          </button>
        </div>
        <div class="space-y-1">
          <div
            v-for="project in projects"
            :key="project.id"
            class="group flex items-center gap-1 rounded-md"
            :class="activeProjectId === project.id ? 'bg-[var(--color-accent-bg)]' : 'hover:bg-[var(--color-bg-secondary)]'"
          >
            <button
              class="flex min-w-0 flex-1 items-center gap-2 px-3 py-2 text-left text-sm"
              :class="activeProjectId === project.id ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-secondary)]'"
              type="button"
              @click="openProject(project.id)"
            >
              <Folder :size="16" class="shrink-0" />
              <span class="truncate">{{ project.name }}</span>
            </button>
            <button
              class="mr-1 hidden h-7 w-7 shrink-0 items-center justify-center rounded-md text-[var(--color-text-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger)] group-hover:inline-flex"
              type="button"
              title="删除项目"
              @click.stop="deleteProject(project)"
            >
              <Trash2 :size="14" />
            </button>
          </div>
        </div>

        <div class="mt-5 mb-2 flex items-center justify-between px-1 text-xs font-medium uppercase text-[var(--color-text-tertiary)]">
          <span>普通对话</span>
          <span>{{ normalSessions.length }}</span>
        </div>
        <div v-if="contextLoading" class="px-2 py-3 text-sm text-[var(--color-text-secondary)]">加载中</div>
        <div v-else-if="!normalSessions.length" class="px-2 py-3 text-sm text-[var(--color-text-secondary)]">暂无对话</div>
        <div v-else class="space-y-1">
          <div
            v-for="session in normalSessions"
            :key="session.id"
            class="group flex items-center gap-1 rounded-md"
            :class="activeSessionId === session.id ? 'bg-[var(--color-bg-secondary)]' : 'hover:bg-[var(--color-bg-secondary)]'"
          >
            <button class="min-w-0 flex-1 px-3 py-2 text-left" type="button" @click="openSession(session)">
              <div class="truncate text-sm">{{ session.title || '新的对话' }}</div>
              <div class="text-xs text-[var(--color-text-tertiary)]">{{ formatDate(session.updated_at) }}</div>
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

        <template v-if="isProjectMode">
          <div class="mt-5 mb-2 flex items-center justify-between px-1 text-xs font-medium uppercase text-[var(--color-text-tertiary)]">
            <span>项目对话</span>
            <span>{{ projectSessions.length }}</span>
          </div>
          <div v-if="contextLoading" class="px-2 py-3 text-sm text-[var(--color-text-secondary)]">加载中</div>
          <div v-else-if="!projectSessions.length" class="px-2 py-3 text-sm text-[var(--color-text-secondary)]">暂无对话</div>
          <div v-else class="space-y-1">
            <div
              v-for="session in projectSessions"
              :key="session.id"
              class="group flex items-center gap-1 rounded-md"
              :class="activeSessionId === session.id ? 'bg-[var(--color-bg-secondary)]' : 'hover:bg-[var(--color-bg-secondary)]'"
            >
              <button class="min-w-0 flex-1 px-3 py-2 text-left" type="button" @click="openSession(session)">
                <div class="truncate text-sm">{{ session.title || '新的对话' }}</div>
                <div class="text-xs text-[var(--color-text-tertiary)]">{{ formatDate(session.updated_at) }}</div>
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
        </template>
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
          <button class="inline-flex items-center gap-2 rounded-md border border-[var(--color-border)] px-3 py-2 text-sm" type="button" @click="newChat">
            <Plus :size="15" />
            新对话
          </button>
        </div>
      </header>

      <div ref="messagesContainer" class="min-h-0 flex-1 space-y-4 overflow-auto p-5">
        <div v-if="!messages.length" class="flex h-full items-center justify-center text-center text-sm text-[var(--color-text-secondary)]">
          <div>
            <MessageSquare :size="30" class="mx-auto mb-3 text-[var(--color-text-tertiary)]" />
            <p>{{ isProjectMode ? '在项目里开始一次带文件上下文的对话。' : '开始一次普通 AI 对话。' }}</p>
          </div>
        </div>
        <div
          v-for="(message, index) in messages"
          :key="index"
          class="max-w-3xl rounded-md p-3"
          :class="message.role === 'user' ? 'ml-auto bg-[var(--color-accent-bg)]' : 'bg-[var(--color-bg-secondary)]'"
        >
          <div v-if="message.references?.length" class="mb-2 flex flex-wrap gap-1">
            <span
              v-for="ref in message.references"
              :key="`${ref.source_type}:${ref.source_id}`"
              class="rounded-md bg-[var(--color-card)] px-2 py-0.5 text-xs text-[var(--color-text-secondary)]"
            >
              @{{ ref.source_type === 'note' ? '笔记' : '知识库' }}
            </span>
          </div>
          <p class="whitespace-pre-wrap text-sm leading-6">{{ message.content }}</p>
        </div>
      </div>

      <div class="border-t border-[var(--color-border)] p-4">
        <p v-if="thinkingMessage" class="mb-2 text-xs text-[var(--color-text-secondary)]">{{ thinkingMessage }}</p>
        <p v-if="errorMessage" class="mb-2 text-sm text-[var(--color-danger)]">{{ errorMessage }}</p>

        <div v-if="selectedRefs.length" class="mb-2 flex flex-wrap gap-2">
          <button
            v-for="ref in selectedRefs"
            :key="`${ref.source_type}:${ref.source_id}`"
            class="inline-flex items-center gap-1 rounded-md bg-[var(--color-accent-bg)] px-2 py-1 text-xs text-[var(--color-accent)]"
            type="button"
            @click="removeReference(ref)"
          >
            @{{ ref.title }}
            <X :size="13" />
          </button>
        </div>

        <div class="relative">
          <div
            v-if="showMention"
            class="absolute bottom-full left-0 z-20 mb-2 max-h-72 w-full overflow-auto rounded-md border border-[var(--color-border)] bg-[var(--color-card)] shadow-lg"
          >
            <button
              v-for="option in filteredMentionOptions"
              :key="`${option.source_type}:${option.source_id}`"
              class="flex w-full items-start gap-2 px-3 py-2 text-left hover:bg-[var(--color-bg-secondary)]"
              type="button"
              @click="selectMention(option)"
            >
              <component :is="getSourceIcon(option.source_type)" :size="16" class="mt-0.5 shrink-0 text-[var(--color-text-tertiary)]" />
              <span class="min-w-0">
                <span class="block truncate text-sm">{{ option.title }}</span>
                <span class="block truncate text-xs text-[var(--color-text-secondary)]">{{ option.subtitle }}</span>
              </span>
            </button>
            <div v-if="!filteredMentionOptions.length" class="px-3 py-3 text-sm text-[var(--color-text-secondary)]">没有可引用的文件</div>
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
        <h2 class="font-heading text-lg font-semibold">项目文件</h2>
        <p class="text-sm text-[var(--color-text-secondary)]">默认作为项目对话上下文</p>
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

        <div v-if="!projectSources.length" class="rounded-md border border-dashed border-[var(--color-border)] px-4 py-8 text-center text-sm text-[var(--color-text-secondary)]">
          暂无项目文件
        </div>
        <div v-else class="space-y-2">
          <article v-for="source in projectSources" :key="source.id" class="rounded-md border border-[var(--color-border)] p-3">
            <div class="flex items-start gap-2">
              <component :is="getSourceIcon(source.source_type)" :size="17" class="mt-0.5 shrink-0 text-[var(--color-text-tertiary)]" />
              <div class="min-w-0 flex-1">
                <h3 class="truncate text-sm font-medium">{{ source.title }}</h3>
                <p class="text-xs text-[var(--color-text-secondary)]">
                  {{ source.source_type === 'note' ? '笔记' : `知识库 · ${source.status || 'ready'}` }}
                </p>
              </div>
              <button
                class="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-[var(--color-text-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger)]"
                type="button"
                title="移除项目文件"
                @click="removeProjectSource(source)"
              >
                <X :size="15" />
              </button>
            </div>
          </article>
        </div>
      </div>
    </aside>

    <aside v-else class="flex min-h-0 flex-col rounded-md border border-[var(--color-border)] bg-[var(--color-card)]">
      <header class="border-b border-[var(--color-border)] px-4 py-3">
        <h2 class="font-heading text-lg font-semibold">参考文件</h2>
        <p class="text-sm text-[var(--color-text-secondary)]">普通对话</p>
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

        <div v-if="globalMentionOptions.length" class="space-y-2">
          <article
            v-for="source in globalMentionOptions.slice(0, 5)"
            :key="`${source.source_type}:${source.source_id}`"
            class="rounded-md border border-[var(--color-border)] p-3"
          >
            <div class="flex items-start gap-2">
              <component :is="getSourceIcon(source.source_type)" :size="17" class="mt-0.5 shrink-0 text-[var(--color-text-tertiary)]" />
              <div class="min-w-0 flex-1">
                <h3 class="truncate text-sm font-medium">{{ source.title }}</h3>
                <p class="truncate text-xs text-[var(--color-text-secondary)]">{{ source.subtitle }}</p>
              </div>
            </div>
          </article>
        </div>

        <div v-else class="rounded-md border border-dashed border-[var(--color-border)] px-4 py-8 text-center text-sm text-[var(--color-text-secondary)]">
          暂无可引用文件
        </div>
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
