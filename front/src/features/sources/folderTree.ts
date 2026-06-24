/**
 * 模块职责：前端 feature 模块，负责按业务域封装 API、类型或局部工具。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
export interface FolderTreeFolder {
  id: string
  name: string
  children?: FolderTreeFolder[]
}

/**
 * 接口：`FolderTreeFile` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface FolderTreeFile {
  id: string
  folderId?: string | null
  title: string
  subtitle?: string
  searchText?: string
}

/**
 * 类型：`FolderTreeRow` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
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

/**
 * 用途：执行buildFolderTreeRows相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
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

  /**
   * 用途：执行folderFileCount相关业务逻辑。
   * @param folder 调用方传入的folder参数，用于驱动当前前端逻辑。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const folderFileCount = (folder: FolderTreeFolder): number => {
    const directCount = filesByFolder.get(folder.id)?.length || 0
    return directCount + (folder.children || []).reduce((sum, child) => sum + folderFileCount(child), 0)
  }

  /**
   * 用途：执行pushFileRows相关业务逻辑。
   * @param group 调用方传入的group参数，用于驱动当前前端逻辑。
   * @param depth 调用方传入的depth参数，用于驱动当前前端逻辑。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
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

  /**
   * 用途：执行walk相关业务逻辑。
   * @param items 调用方传入的items参数，用于驱动当前前端逻辑。
   * @param depth 调用方传入的depth参数，用于驱动当前前端逻辑。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
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

/**
 * 用途：执行collectFolderIds相关业务逻辑。
 * @param folders 调用方传入的folders参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function collectFolderIds(folders: FolderTreeFolder[]) {
  const ids = new Set<string>()
  /**
   * 用途：执行walk相关业务逻辑。
   * @param items 调用方传入的items参数，用于驱动当前前端逻辑。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const walk = (items: FolderTreeFolder[]) => {
    for (const folder of items) {
      ids.add(folder.id)
      walk(folder.children || [])
    }
  }
  walk(folders)
  return ids
}
