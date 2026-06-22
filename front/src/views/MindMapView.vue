<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import { knowledgeApi } from '../api/knowledge'
import { mindmapApi } from '../api/mindmaps'
import { notesApi } from '../api/notes'
import type { KnowledgeDocument, MindMapResponse, Note, SourceType } from '../types/api'

const notes = ref<Note[]>([])
const docs = ref<KnowledgeDocument[]>([])
const sourceType = ref<SourceType>('note')
const selected = ref<string[]>([])
const focus = ref('')
const mindmap = ref<MindMapResponse | null>(null)
const loading = ref(false)

const sourceOptions = computed(() => {
  if (sourceType.value === 'note') return notes.value.map((note) => ({ id: note.id, title: note.title }))
  if (sourceType.value === 'knowledge') return docs.value.map((doc) => ({ id: doc.id, title: doc.original_filename || doc.filename }))
  return [
    ...notes.value.map((note) => ({ id: note.id, title: `笔记：${note.title}` })),
    ...docs.value.map((doc) => ({ id: doc.id, title: `知识库：${doc.original_filename || doc.filename}` })),
  ]
})

const flowNodes = computed(() =>
  (mindmap.value?.nodes || []).map((node, index) => ({
    id: node.id,
    label: node.label,
    position: { x: (node.level || 0) * 260, y: index * 86 },
    data: node,
  }))
)

const flowEdges = computed(() =>
  (mindmap.value?.edges || []).map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.label || '',
  }))
)

async function loadSources() {
  const [noteRes, docRes] = await Promise.all([notesApi.list({ page: 1, page_size: 50 }), knowledgeApi.list()])
  notes.value = noteRes.data.notes
  docs.value = docRes.data.documents
}

async function generate() {
  loading.value = true
  try {
    mindmap.value = await mindmapApi.generate({
      source_type: sourceType.value,
      source_ids: selected.value,
      max_nodes: 40,
      max_depth: 4,
      focus: focus.value || undefined,
    })
  } finally {
    loading.value = false
  }
}

onMounted(loadSources)
</script>

<template>
  <div class="grid gap-6 xl:grid-cols-[320px_1fr]">
    <aside class="rounded-md border border-[var(--color-border)] bg-[var(--color-card)] p-4">
      <div class="space-y-4">
        <select v-model="sourceType" class="w-full rounded-md border border-[var(--color-border)] bg-transparent px-3 py-2" @change="selected = []">
          <option value="note">笔记</option>
          <option value="knowledge">知识库</option>
          <option value="mixed">混合</option>
        </select>
        <input v-model="focus" class="w-full rounded-md border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm" placeholder="导图关注点" />
        <div class="max-h-72 space-y-2 overflow-auto rounded-md border border-[var(--color-border)] p-2">
          <label v-for="item in sourceOptions" :key="item.id" class="flex items-start gap-2 text-sm">
            <input v-model="selected" type="checkbox" :value="item.id" class="mt-1" />
            <span>{{ item.title }}</span>
          </label>
        </div>
        <button class="w-full rounded-md bg-[var(--color-accent)] px-4 py-2 text-white disabled:opacity-60" :disabled="loading || selected.length === 0" @click="generate">
          {{ loading ? '生成中' : '生成导图' }}
        </button>
      </div>
    </aside>

    <section class="min-h-[680px] rounded-md border border-[var(--color-border)] bg-[var(--color-card)]">
      <div v-if="mindmap" class="flex h-full flex-col">
        <div class="flex items-center justify-between border-b border-[var(--color-border)] px-5 py-3">
          <h2 class="font-heading text-lg font-semibold">{{ mindmap.title }}</h2>
          <span class="text-xs text-[var(--color-text-secondary)]">v{{ mindmap.version }}</span>
        </div>
        <VueFlow class="flex-1" :nodes="flowNodes" :edges="flowEdges" fit-view-on-init>
          <Background />
          <Controls />
        </VueFlow>
      </div>
      <div v-else class="flex h-[680px] items-center justify-center text-sm text-[var(--color-text-secondary)]">请选择来源后生成导图。</div>
    </section>
  </div>
</template>
