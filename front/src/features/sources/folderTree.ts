export interface FolderTreeFolder {
  id: string
  name: string
  children?: FolderTreeFolder[]
}

export interface FolderTreeFile {
  id: string
  folderId?: string | null
  title: string
  subtitle?: string
  searchText?: string
}

export type FolderTreeRow = {
  key: string
  kind: 'folder' | 'file' | 'empty'
  title: string
  depth: number
  subtitle?: string
  count?: number
  sourceId?: string
  collapsed?: boolean
}

export function buildFolderTreeRows(
  folders: FolderTreeFolder[],
  files: FolderTreeFile[],
  emptyTitle: string,
  query = '',
  folderStateKeys: ReadonlySet<string> = new Set<string>(),
  defaultCollapsed = false,
): FolderTreeRow[] {
  const keyword = query.trim().toLowerCase()
  const knownFolderIds = collectFolderIds(folders)
  const filteredFiles = keyword
    ? files.filter((file) => {
      const haystack = [file.title, file.subtitle, file.searchText].filter(Boolean).join(' ').toLowerCase()
      return haystack.includes(keyword)
    })
    : files

  const rows: FolderTreeRow[] = []
  const filesByFolder = new Map<string, FolderTreeFile[]>()

  for (const file of filteredFiles) {
    const folderKey = file.folderId && knownFolderIds.has(file.folderId) ? file.folderId : ''
    const group = filesByFolder.get(folderKey) || []
    group.push(file)
    filesByFolder.set(folderKey, group)
  }

  const folderFileCount = (folder: FolderTreeFolder): number => {
    const directCount = filesByFolder.get(folder.id)?.length || 0
    return directCount + (folder.children || []).reduce((sum, child) => sum + folderFileCount(child), 0)
  }

  const pushFileRows = (group: FolderTreeFile[] | undefined, depth: number) => {
    for (const file of group || []) {
      rows.push({
        key: `file:${file.id}`,
        kind: 'file',
        title: file.title,
        subtitle: file.subtitle,
        depth,
        sourceId: file.id,
      })
    }
  }

  const walk = (items: FolderTreeFolder[], depth: number) => {
    for (const folder of items) {
      const count = folderFileCount(folder)
      if (!count) continue
      const folderKey = `folder:${folder.id}`
      const collapsed = keyword ? false : defaultCollapsed ? !folderStateKeys.has(folderKey) : folderStateKeys.has(folderKey)
      rows.push({
        key: folderKey,
        kind: 'folder',
        title: folder.name,
        depth,
        count,
        collapsed,
      })
      if (collapsed) continue
      walk(folder.children || [], depth + 1)
      pushFileRows(filesByFolder.get(folder.id), depth + 1)
    }
  }

  walk(folders, 0)

  const unfiledFiles = filesByFolder.get('')
  if (unfiledFiles?.length) {
    const unfiledKey = 'folder:unfiled'
    const collapsed = keyword ? false : defaultCollapsed ? !folderStateKeys.has(unfiledKey) : folderStateKeys.has(unfiledKey)
    rows.push({
      key: unfiledKey,
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

function collectFolderIds(folders: FolderTreeFolder[]) {
  const ids = new Set<string>()
  const walk = (items: FolderTreeFolder[]) => {
    for (const folder of items) {
      ids.add(folder.id)
      walk(folder.children || [])
    }
  }
  walk(folders)
  return ids
}
