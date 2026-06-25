import { useLanguageStore } from '../stores/useLanguageStore'
import { enUSMessages, type I18nKey, type Lang } from './messages'

type Params = Record<string, string | number>

export function translate(lang: Lang, key: I18nKey | string, params?: Params): string {
  const translated = lang === 'en-US'
    ? translateEnglish(String(key))
    : String(key)

  if (!params) return translated
  return Object.entries(params).reduce(
    (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
    translated,
  )
}

export function translateEnglish(value: string): string {
  const direct = enUSMessages[value as I18nKey]
  if (direct) return direct

  const selected = value.match(/^已选择\s+(\d+)\s+项$/)
  if (selected) return `${selected[1]} selected`

  const selectedFiles = value.match(/^已选择\s+(\d+)\s+个：(.+)$/)
  if (selectedFiles) return `${selectedFiles[1]} selected: ${selectedFiles[2]}`

  const selectedNotes = value.match(/^已选择\s+(\d+)\s+篇$/)
  if (selectedNotes) return `${selectedNotes[1]} selected`

  const folderTotal = value.match(/^(.+)\s+·\s+共\s+(\d+)\s+篇$/)
  if (folderTotal) {
    const title = translateEnglish(folderTotal[1])
    const noun = title.toLowerCase().includes('document') ? 'documents' : title.toLowerCase().includes('note') ? 'notes' : 'items'
    return `${title} · ${folderTotal[2]} ${noun}`
  }

  const unlinked = value.match(/^未关联：笔记\s+(\d+)\s+·\s+知识库\s+(\d+)$/)
  if (unlinked) return `Unlinked: Notes ${unlinked[1]} · Knowledge Base ${unlinked[2]}`

  const projectFiles = value.match(/^(\d+)\s+个项目文件$/)
  if (projectFiles) return `${projectFiles[1]} project files`

  const addFiles = value.match(/^添加\s+(\d+)\s+个文件$/)
  if (addFiles) return `Add ${addFiles[1]} files`

  const uploadedDocs = value.match(/^已上传\s+(\d+)\s+个文档$/)
  if (uploadedDocs) return `${uploadedDocs[1]} documents uploaded`

  const uploadSummary = value.match(/^已完成\s+(\d+)\s+个文档，失败\s+(\d+)\s+个$/)
  if (uploadSummary) return `${uploadSummary[1]} documents done, ${uploadSummary[2]} failed`

  const requestStatus = value.match(/^请求失败：(\d+)$/)
  if (requestStatus) return `Request failed: ${requestStatus[1]}`

  const rawPreviewError = value.match(/^(.+)\s+原样预览不可用：(.+)$/)
  if (rawPreviewError) return `${translateEnglish(rawPreviewError[1])} preview is unavailable: ${rawPreviewError[2]}`

  const originalReadError = value.match(/^原文件读取失败：(.+)$/)
  if (originalReadError) return `Failed to read original file: ${originalReadError[1]}`

  const deleteKnowledge = value.match(/^确认删除「(.+)」？删除后会从知识库检索中移除。$/)
  if (deleteKnowledge) return `Delete "${deleteKnowledge[1]}"? It will be removed from knowledge retrieval.`

  const deleteProject = value.match(/^确认删除项目「(.+)」？项目内对话会删除，原笔记和知识库文件会保留。$/)
  if (deleteProject) return `Delete project "${deleteProject[1]}"? Project chats will be deleted, while the original notes and knowledge files will be kept.`

  const deleteNamed = value.match(/^确认删除「(.+)」？删除后无法恢复。$/)
  if (deleteNamed) return `Delete "${deleteNamed[1]}"? This cannot be undone.`

  const deleteChat = value.match(/^确认删除「(.+)」？$/)
  if (deleteChat) return `Delete "${deleteChat[1]}"?`

  const deleteSelectedNotes = value.match(/^确认删除选中的\s+(\d+)\s+篇笔记？删除后无法恢复。$/)
  if (deleteSelectedNotes) return `Delete ${deleteSelectedNotes[1]} selected notes? This cannot be undone.`

  const deleteCategory = value.match(/^确定要删除分类「(.+)」吗？这将同步删除该分类下的\s+(\d+)\s+篇(.+)。$/)
  if (deleteCategory) return `Delete category "${deleteCategory[1]}"? This will also remove it from ${deleteCategory[2]} ${translateEnglish(deleteCategory[3]).toLowerCase()}.`

  const deleteNoteFolder = value.match(/^删除「(.+)」时，可以将其中笔记移回未归档，或同时删除该文件夹内的笔记。$/)
  if (deleteNoteFolder) return `When deleting "${deleteNoteFolder[1]}", you can move its notes back to Unfiled or delete the notes in this folder too.`

  const deleteKnowledgeFolder = value.match(/^删除「(.+)」时，可以将其中文档移回未归档，或同时删除该文件夹内的文档。$/)
  if (deleteKnowledgeFolder) return `When deleting "${deleteKnowledgeFolder[1]}", you can move its documents back to Unfiled or delete the documents in this folder too.`

  const similarity = value.match(/^相似度:\s+(.+)$/)
  if (similarity) return `Similarity: ${similarity[1]}`

  const folderFallback = value.match(/^文件夹（(.+)）$/)
  if (folderFallback) return `Folder (${folderFallback[1]})`

  const noScopedContent = value.match(/^(.+)暂无内容$/)
  if (noScopedContent) return `${translateEnglish(noScopedContent[1])}: no content`

  const monthDay = value.match(/^(\d{1,2})月(\d{1,2})日$/)
  if (monthDay) {
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    const monthIndex = Number(monthDay[1]) - 1
    const monthName = monthNames[monthIndex] || monthDay[1]
    return `${monthName} ${Number(monthDay[2])}`
  }

  const sourceCount = value.match(/^(\d+)\s+个来源\s+·\s+(\d+)\s+个节点$/)
  if (sourceCount) return `${sourceCount[1]} sources · ${sourceCount[2]} nodes`

  const noteCount = value.match(/^笔记\s+(\d+)\/(\d+)$/)
  if (noteCount) return `Notes ${noteCount[1]}/${noteCount[2]}`

  const docCount = value.match(/^知识库\s+(\d+)\/(\d+)$/)
  if (docCount) return `Knowledge ${docCount[1]}/${docCount[2]}`

  const processed = value.match(/^已处理\s+(.+)$/)
  if (processed) return `Processed ${processed[1]}`

  const minute = value.match(/^(\d+)\s+分$/)
  if (minute) return `${minute[1]} min`

  const hour = value.match(/^(\d+)\s+小时$/)
  if (hour) return `${hour[1]} hr`

  const day = value.match(/^(\d+)\s+天$/)
  if (day) return `${day[1]} d`

  const page = value.match(/^第\s+(\d+)\s+页$/)
  if (page) return `Page ${page[1]}`

  const chunk = value.match(/^片段\s+(\d+)$/)
  if (chunk) return `Chunk ${chunk[1]}`

  const chunkWithPage = value.match(/^片段\s+(\d+)\s+\|\s+第\s+(\d+)\s+页$/)
  if (chunkWithPage) return `Chunk ${chunkWithPage[1]} | Page ${chunkWithPage[2]}`

  const questionType = value.match(/^问题\s+(\d+)\s+\/\s+(\d+)\s+·\s+(.+)$/)
  if (questionType) return `Question ${questionType[1]} / ${questionType[2]} · ${translateEnglish(questionType[3])}`

  const questionNo = value.match(/^问题\s+(\d+)$/)
  if (questionNo) return `Question ${questionNo[1]}`

  const score = value.match(/^得分\s+(\d+)\s+\/\s+(\d+)$/)
  if (score) return `Score ${score[1]} / ${score[2]}`

  const unanswered = value.match(/^还有\s+(\d+)\s+道题未回答$/)
  if (unanswered) return `${unanswered[1]} unanswered questions`

  return value
}

export function useI18n() {
  const languageStore = useLanguageStore()

  return {
    t: (key: I18nKey | string, params?: Params) => translate(languageStore.lang, key, params),
    languageStore,
  }
}
