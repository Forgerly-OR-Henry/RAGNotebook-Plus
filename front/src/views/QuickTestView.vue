<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { knowledgeApi } from '../api/knowledge'
import { notesApi } from '../api/notes'
import { quickTestApi } from '../api/quickTest'
import type { Difficulty, KnowledgeDocument, Note, QuickTestAnswerResponse, QuickTestStartResponse, SourceType } from '../types/api'

const notes = ref<Note[]>([])
const docs = ref<KnowledgeDocument[]>([])
const sourceType = ref<SourceType>('note')
const selected = ref<string[]>([])
const difficulty = ref<Difficulty>('normal')
const questionCount = ref(5)
const focus = ref('')
const session = ref<QuickTestStartResponse | null>(null)
const answer = ref('')
const currentQuestion = ref('')
const feedbacks = ref<QuickTestAnswerResponse[]>([])
const loading = ref(false)

const sourceOptions = computed(() => {
  if (sourceType.value === 'note') return notes.value.map((note) => ({ id: note.id, title: note.title }))
  if (sourceType.value === 'knowledge') return docs.value.map((doc) => ({ id: doc.id, title: doc.original_filename || doc.filename }))
  return [
    ...notes.value.map((note) => ({ id: note.id, title: `笔记：${note.title}` })),
    ...docs.value.map((doc) => ({ id: doc.id, title: `知识库：${doc.original_filename || doc.filename}` })),
  ]
})

async function loadSources() {
  const [noteRes, docRes] = await Promise.all([notesApi.list({ page: 1, page_size: 50 }), knowledgeApi.list()])
  notes.value = noteRes.data.notes
  docs.value = docRes.data.documents
}

async function start() {
  loading.value = true
  feedbacks.value = []
  try {
    const data = await quickTestApi.create({
      source_type: sourceType.value,
      source_ids: selected.value,
      question_count: questionCount.value,
      difficulty: difficulty.value,
      focus: focus.value || undefined,
    })
    session.value = data
    currentQuestion.value = data.first_question
  } finally {
    loading.value = false
  }
}

async function submitAnswer() {
  if (!session.value || !answer.value.trim()) return
  loading.value = true
  try {
    const data = await quickTestApi.answer(session.value.session_id, answer.value)
    feedbacks.value.unshift(data)
    answer.value = ''
    currentQuestion.value = data.next_question || ''
  } finally {
    loading.value = false
  }
}

onMounted(loadSources)
</script>

<template>
  <div class="grid gap-6 lg:grid-cols-[320px_1fr]">
    <aside class="rounded-md border border-[var(--color-border)] bg-[var(--color-card)] p-4">
      <div class="space-y-4">
        <label class="block text-sm">
          <span class="text-[var(--color-text-secondary)]">来源</span>
          <select v-model="sourceType" class="mt-1 w-full rounded-md border border-[var(--color-border)] bg-transparent px-3 py-2" @change="selected = []">
            <option value="note">笔记</option>
            <option value="knowledge">知识库</option>
            <option value="mixed">混合</option>
          </select>
        </label>
        <label class="block text-sm">
          <span class="text-[var(--color-text-secondary)]">难度</span>
          <select v-model="difficulty" class="mt-1 w-full rounded-md border border-[var(--color-border)] bg-transparent px-3 py-2">
            <option value="easy">简单</option>
            <option value="normal">普通</option>
            <option value="hard">困难</option>
          </select>
        </label>
        <label class="block text-sm">
          <span class="text-[var(--color-text-secondary)]">题数</span>
          <input v-model.number="questionCount" type="number" min="1" max="20" class="mt-1 w-full rounded-md border border-[var(--color-border)] bg-transparent px-3 py-2" />
        </label>
        <input v-model="focus" class="w-full rounded-md border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm" placeholder="关注点" />
        <div class="max-h-64 space-y-2 overflow-auto rounded-md border border-[var(--color-border)] p-2">
          <label v-for="item in sourceOptions" :key="item.id" class="flex items-start gap-2 text-sm">
            <input v-model="selected" type="checkbox" :value="item.id" class="mt-1" />
            <span>{{ item.title }}</span>
          </label>
        </div>
        <button class="w-full rounded-md bg-[var(--color-accent)] px-4 py-2 text-white disabled:opacity-60" :disabled="loading || selected.length === 0" @click="start">开始测试</button>
      </div>
    </aside>

    <section class="rounded-md border border-[var(--color-border)] bg-[var(--color-card)] p-5">
      <div v-if="currentQuestion" class="space-y-4">
        <h2 class="font-heading text-xl font-semibold">{{ currentQuestion }}</h2>
        <textarea v-model="answer" class="min-h-32 w-full rounded-md border border-[var(--color-border)] bg-transparent p-3" placeholder="输入回答"></textarea>
        <button class="rounded-md bg-[var(--color-accent)] px-4 py-2 text-white disabled:opacity-60" :disabled="loading" @click="submitAnswer">提交回答</button>
      </div>
      <p v-else class="text-sm text-[var(--color-text-secondary)]">请选择来源后开始测试。</p>

      <div class="mt-6 space-y-3">
        <article v-for="(item, index) in feedbacks" :key="index" class="rounded-md bg-[var(--color-bg-secondary)] p-4">
          <div class="text-sm font-medium">得分 {{ item.score }}</div>
          <p class="mt-2 text-sm">{{ item.feedback }}</p>
        </article>
      </div>
    </section>
  </div>
</template>
