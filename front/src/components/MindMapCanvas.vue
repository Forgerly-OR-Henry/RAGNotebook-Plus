<!--
模块职责：Vue 可复用组件，负责封装局部界面、交互状态和事件输出。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { Copy, Download, RotateCcw, ZoomIn, ZoomOut } from '@lucide/vue'
import MindMapTreeNode from './MindMapTreeNode.vue'
import type { MindMapNode, MindMapResponse } from '../types/api'

/**
 * 接口：`MindMapTreeNodeData` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface MindMapTreeNodeData {
  id: string
  label: string
  summary?: string | null
  children: MindMapTreeNodeData[]
}

const props = withDefaults(defineProps<{
  mindmap: MindMapResponse | null
  loading?: boolean
  emptyText?: string
}>(), {
  loading: false,
  emptyText: '请选择来源后生成导图。',
})

// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const scale = ref(1)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const offset = ref({ x: 0, y: 0 })
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const dragging = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const dragStart = ref({ x: 0, y: 0 })
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const copyMessage = ref('')
let copyTimer: number | undefined

/**
 * 接口：`ExportNodeMetrics` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface ExportNodeMetrics {
  width: number
  height: number
  labelLines: string[]
  summaryLines: string[]
}

/**
 * 接口：`ExportNodeLayout` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface ExportNodeLayout {
  node: MindMapTreeNodeData
  depth: number
  x: number
  y: number
  width: number
  height: number
  metrics: ExportNodeMetrics
  children: ExportNodeLayout[]
}

const EXPORT_PADDING_X = 72
const EXPORT_PADDING_Y = 96
const EXPORT_COLUMN_GAP = 342
const EXPORT_VERTICAL_GAP = 26

const exportTones = [
  { fill: '#1F6C9F', stroke: '#1F6C9F', text: '#FFFFFF', muted: '#DDF0FF', line: '#82B8D8' },
  { fill: '#EAF8F1', stroke: '#39A66C', text: '#14583A', muted: '#4C7B62', line: '#79C79D' },
  { fill: '#EAF5FF', stroke: '#3B8FC4', text: '#195273', muted: '#527B94', line: '#8CC4E6' },
  { fill: '#FFF5E3', stroke: '#D98B18', text: '#754A0B', muted: '#927246', line: '#E7B66C' },
  { fill: '#FDF0F3', stroke: '#C75A72', text: '#7A2638', muted: '#96616D', line: '#DC9AAC' },
]

/**
 * 用途：执行tree相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const tree = computed(() => buildTree(props.mindmap))
/**
 * 用途：执行scaleLabel相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const scaleLabel = computed(() => `${Math.round(scale.value * 100)}%`)

// 状态监听：在关键输入变化后同步副作用或刷新页面数据。
watch(() => props.mindmap?.mindmap_id, () => resetView())

onBeforeUnmount(() => {
  if (copyTimer) window.clearTimeout(copyTimer)
})

/**
 * 用途：执行buildTree相关业务逻辑。
 * @param mindmap 调用方传入的mindmap参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function buildTree(mindmap: MindMapResponse | null): MindMapTreeNodeData | null {
  if (!mindmap?.nodes.length) return null

  const nodeMap = new Map<string, MindMapTreeNodeData>()
  const targets = new Set<string>()

  mindmap.nodes.forEach((node) => {
    nodeMap.set(node.id, {
      id: node.id,
      label: node.label,
      summary: node.summary,
      children: [],
    })
  })

  mindmap.edges.forEach((edge) => {
    const source = nodeMap.get(edge.source)
    const target = nodeMap.get(edge.target)
    if (!source || !target || source.children.some((child) => child.id === target.id)) return
    source.children.push(target)
    targets.add(target.id)
  })

  const rootNode = pickRoot(mindmap.nodes, targets, nodeMap)
  const attached = new Set<string>()
  collectTreeIds(rootNode, attached)

  mindmap.nodes.forEach((node) => {
    const candidate = nodeMap.get(node.id)
    if (candidate && !attached.has(candidate.id)) {
      rootNode.children.push(candidate)
    }
  })

  return rootNode
}

/**
 * 用途：执行pickRoot相关业务逻辑。
 * @param nodes 调用方传入的nodes参数，用于驱动当前前端逻辑。
 * @param targets 调用方传入的targets参数，用于驱动当前前端逻辑。
 * @param nodeMap 调用方传入的nodeMap参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function pickRoot(nodes: MindMapNode[], targets: Set<string>, nodeMap: Map<string, MindMapTreeNodeData>) {
  /**
   * 用途：执行root相关业务逻辑。
   * 参数：无显式业务参数。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const root = nodes.find((node) => node.level === 0 && !targets.has(node.id))
    || nodes.find((node) => !targets.has(node.id))
    || nodes[0]
  return nodeMap.get(root.id) || {
    id: root.id,
    label: root.label,
    summary: root.summary,
    children: [],
  }
}

/**
 * 用途：执行collectTreeIds相关业务逻辑。
 * @param node 调用方传入的node参数，用于驱动当前前端逻辑。
 * @param ids 调用方传入的ids参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function collectTreeIds(node: MindMapTreeNodeData, ids: Set<string>) {
  if (ids.has(node.id)) return
  ids.add(node.id)
  node.children.forEach((child) => collectTreeIds(child, ids))
}

/**
 * 用途：执行startPan相关业务逻辑。
 * @param event 调用方传入的event参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function startPan(event: PointerEvent) {
  if (!tree.value || event.button !== 0) return
  dragging.value = true
  dragStart.value = {
    x: event.clientX - offset.value.x,
    y: event.clientY - offset.value.y,
  }
  const target = event.currentTarget as HTMLElement
  target.setPointerCapture?.(event.pointerId)
}

/**
 * 用途：执行movePan相关业务逻辑。
 * @param event 调用方传入的event参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function movePan(event: PointerEvent) {
  if (!dragging.value) return
  offset.value = {
    x: event.clientX - dragStart.value.x,
    y: event.clientY - dragStart.value.y,
  }
}

/**
 * 用途：执行endPan相关业务逻辑。
 * @param event 调用方传入的event参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function endPan(event: PointerEvent) {
  dragging.value = false
  const target = event.currentTarget as HTMLElement
  try {
    target.releasePointerCapture?.(event.pointerId)
  } catch {
    // Pointer capture may already be released when the pointer leaves the canvas.
  }
}

/**
 * 用途：执行zoomBy相关业务逻辑。
 * @param delta 调用方传入的delta参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function zoomBy(delta: number) {
  scale.value = Math.min(2.5, Math.max(0.5, Number((scale.value + delta).toFixed(2))))
}

/**
 * 用途：执行handleWheel相关业务逻辑。
 * @param event 调用方传入的event参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function handleWheel(event: WheelEvent) {
  if (!tree.value) return
  zoomBy(event.deltaY < 0 ? 0.1 : -0.1)
}

/**
 * 用途：执行resetView相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function resetView() {
  scale.value = 1
  offset.value = { x: 0, y: 0 }
}

/**
 * 用途：执行outlineText相关业务逻辑。
 * @param node 调用方传入的node参数，用于驱动当前前端逻辑。
 * @param indent 调用方传入的indent参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function outlineText(node: MindMapTreeNodeData, indent = ''): string {
  return `${indent}- ${node.label}\n${node.children.map((child) => outlineText(child, `${indent}  `)).join('')}`
}

/**
 * 用途：执行copyOutline相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function copyOutline() {
  if (!tree.value) return
  const text = outlineText(tree.value)
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      fallbackCopy(text)
    }
    showCopyMessage('大纲已复制')
  } catch {
    try {
      fallbackCopy(text)
      showCopyMessage('大纲已复制')
    } catch {
      showCopyMessage('复制失败')
    }
  }
}

/**
 * 用途：执行fallbackCopy相关业务逻辑。
 * @param text 调用方传入的text参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function fallbackCopy(text: string) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', 'true')
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  document.body.removeChild(textarea)
}

/**
 * 用途：执行downloadSvg相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function downloadSvg() {
  if (!tree.value || !props.mindmap) return

  const svg = buildMindMapSvg(tree.value, props.mindmap.title)
  const blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${sanitizeFilename(props.mindmap.title || 'mindmap')}.svg`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.setTimeout(() => URL.revokeObjectURL(url), 0)
  showCopyMessage('SVG 已下载')
}

/**
 * 用途：执行buildMindMapSvg相关业务逻辑。
 * @param root 调用方传入的root参数，用于驱动当前前端逻辑。
 * @param title 调用方传入的title参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function buildMindMapSvg(root: MindMapTreeNodeData, title: string) {
  const layout = buildExportLayout(root)
  const nodes = flattenExportLayout(layout)
  /**
   * 用途：执行minTop相关业务逻辑。
   * 参数：无显式业务参数。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const minTop = Math.min(...nodes.map((node) => node.y - node.height / 2))
  /**
   * 用途：执行maxBottom相关业务逻辑。
   * 参数：无显式业务参数。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const maxBottom = Math.max(...nodes.map((node) => node.y + node.height / 2))
  /**
   * 用途：执行maxRight相关业务逻辑。
   * 参数：无显式业务参数。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const maxRight = Math.max(...nodes.map((node) => node.x + node.width))
  const yShift = EXPORT_PADDING_Y - minTop

  nodes.forEach((node) => {
    node.y += yShift
  })

  const width = Math.ceil(maxRight + EXPORT_PADDING_X)
  const height = Math.ceil(maxBottom + yShift + EXPORT_PADDING_Y)
  const safeTitle = escapeXml(title || '思维导图')

  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${safeTitle}">`,
    '<defs>',
    '<pattern id="mindmap-dot-grid" width="28" height="28" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r="1.2" fill="#C8DDEB" opacity="0.45"/></pattern>',
    '<filter id="mindmap-node-shadow" x="-20%" y="-30%" width="140%" height="170%"><feDropShadow dx="0" dy="10" stdDeviation="12" flood-color="#1F2937" flood-opacity="0.12"/></filter>',
    '</defs>',
    `<rect width="${width}" height="${height}" fill="#F7F6F3"/>`,
    `<rect width="${width}" height="${height}" fill="url(#mindmap-dot-grid)"/>`,
    `<text x="${EXPORT_PADDING_X}" y="46" fill="#111111" font-family="'Noto Sans SC', 'PingFang SC', sans-serif" font-size="22" font-weight="700">${safeTitle}</text>`,
    `<text x="${EXPORT_PADDING_X}" y="70" fill="#787774" font-family="'Noto Sans SC', 'PingFang SC', sans-serif" font-size="12">${nodes.length} 个节点</text>`,
    renderExportConnectors(layout),
    nodes.map((node) => renderExportNode(node)).join(''),
    '</svg>',
  ].join('')
}

/**
 * 用途：执行buildExportLayout相关业务逻辑。
 * @param root 调用方传入的root参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function buildExportLayout(root: MindMapTreeNodeData) {
  let cursor = 0

  /**
   * 用途：执行place相关业务逻辑。
   * @param node 调用方传入的node参数，用于驱动当前前端逻辑。
   * @param depth 调用方传入的depth参数，用于驱动当前前端逻辑。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  function place(node: MindMapTreeNodeData, depth: number): ExportNodeLayout {
    const metrics = getExportNodeMetrics(node, depth)
    /**
     * 用途：执行children相关业务逻辑。
     * 参数：无显式业务参数。
     * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
     */
    const children = node.children.map((child) => place(child, depth + 1))
    let y = 0

    if (children.length === 0) {
      y = cursor + metrics.height / 2
      cursor += metrics.height + EXPORT_VERTICAL_GAP
    } else {
      y = (children[0].y + children[children.length - 1].y) / 2
      const top = y - metrics.height / 2
      if (top < cursor) {
        const shift = cursor - top
        children.forEach((child) => shiftExportLayout(child, shift))
        y += shift
      }
      cursor = Math.max(cursor, y + metrics.height / 2 + EXPORT_VERTICAL_GAP)
    }

    return {
      node,
      depth,
      x: EXPORT_PADDING_X + depth * EXPORT_COLUMN_GAP,
      y,
      width: metrics.width,
      height: metrics.height,
      metrics,
      children,
    }
  }

  return place(root, 0)
}

/**
 * 用途：执行shiftExportLayout相关业务逻辑。
 * @param layout 调用方传入的layout参数，用于驱动当前前端逻辑。
 * @param shift 调用方传入的shift参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function shiftExportLayout(layout: ExportNodeLayout, shift: number) {
  layout.y += shift
  layout.children.forEach((child) => shiftExportLayout(child, shift))
}

/**
 * 用途：执行flattenExportLayout相关业务逻辑。
 * @param layout 调用方传入的layout参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function flattenExportLayout(layout: ExportNodeLayout): ExportNodeLayout[] {
  return [layout, ...layout.children.flatMap((child) => flattenExportLayout(child))]
}

/**
 * 用途：执行getExportNodeMetrics相关业务逻辑。
 * @param node 调用方传入的node参数，用于驱动当前前端逻辑。
 * @param depth 调用方传入的depth参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function getExportNodeMetrics(node: MindMapTreeNodeData, depth: number): ExportNodeMetrics {
  const width = getExportNodeWidth(depth)
  const labelUnits = Math.max(10, Math.floor((width - 42) / 13))
  const summaryUnits = Math.max(12, Math.floor((width - 42) / 10))
  const labelLines = wrapSvgText(node.label || '未命名主题', labelUnits, depth === 0 ? 2 : 2)
  const summaryLines = node.summary ? wrapSvgText(node.summary, summaryUnits, 1) : []
  const height = Math.max(depth === 0 ? 74 : 60, 30 + labelLines.length * 18 + summaryLines.length * 15 + (summaryLines.length ? 6 : 0))

  return {
    width,
    height,
    labelLines,
    summaryLines,
  }
}

/**
 * 用途：执行getExportNodeWidth相关业务逻辑。
 * @param depth 调用方传入的depth参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function getExportNodeWidth(depth: number) {
  if (depth === 0) return 280
  if (depth === 1) return 252
  if (depth === 2) return 232
  return 214
}

/**
 * 用途：执行renderExportConnectors相关业务逻辑。
 * @param layout 调用方传入的layout参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function renderExportConnectors(layout: ExportNodeLayout): string {
  /**
   * 用途：执行currentConnectors相关业务逻辑。
   * 参数：无显式业务参数。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const currentConnectors = layout.children.map((child) => {
    const tone = getExportTone(child.depth)
    const startX = layout.x + layout.width
    const startY = layout.y
    const endX = child.x
    const endY = child.y
    const control = Math.max(44, (endX - startX) * 0.44)
    const path = `M ${formatSvgNumber(startX)} ${formatSvgNumber(startY)} C ${formatSvgNumber(startX + control)} ${formatSvgNumber(startY)}, ${formatSvgNumber(endX - control)} ${formatSvgNumber(endY)}, ${formatSvgNumber(endX)} ${formatSvgNumber(endY)}`
    return `<path d="${path}" fill="none" stroke="${tone.line}" stroke-width="2.4" stroke-linecap="round" opacity="0.86"/>`
  }).join('')

  return currentConnectors + layout.children.map((child) => renderExportConnectors(child)).join('')
}

/**
 * 用途：执行renderExportNode相关业务逻辑。
 * @param layout 调用方传入的layout参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function renderExportNode(layout: ExportNodeLayout): string {
  const tone = getExportTone(layout.depth)
  const radius = layout.depth === 0 ? 24 : 18
  const x = layout.x
  const y = layout.y - layout.height / 2
  const textX = layout.x + layout.width / 2
  const labelSize = layout.depth === 0 ? 15 : 12.5
  const summarySize = 10.5
  const labelLineHeight = 18
  const summaryLineHeight = 15
  const contentHeight = layout.metrics.labelLines.length * labelLineHeight
    + (layout.metrics.summaryLines.length ? 6 + layout.metrics.summaryLines.length * summaryLineHeight : 0)
  let textY = layout.y - contentHeight / 2 + labelLineHeight * 0.78

  /**
   * 用途：执行label相关业务逻辑。
   * 参数：无显式业务参数。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const label = layout.metrics.labelLines.map((line) => {
    const text = `<tspan x="${formatSvgNumber(textX)}" y="${formatSvgNumber(textY)}">${escapeXml(line)}</tspan>`
    textY += labelLineHeight
    return text
  }).join('')

  textY += layout.metrics.summaryLines.length ? 4 : 0
  /**
   * 用途：执行summary相关业务逻辑。
   * 参数：无显式业务参数。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const summary = layout.metrics.summaryLines.map((line) => {
    const text = `<tspan x="${formatSvgNumber(textX)}" y="${formatSvgNumber(textY)}">${escapeXml(line)}</tspan>`
    textY += summaryLineHeight
    return text
  }).join('')

  return [
    `<g filter="url(#mindmap-node-shadow)">`,
    `<rect x="${formatSvgNumber(x)}" y="${formatSvgNumber(y)}" width="${layout.width}" height="${layout.height}" rx="${radius}" fill="${tone.fill}" stroke="${tone.stroke}" stroke-width="1.4"/>`,
    `<text text-anchor="middle" font-family="'Noto Sans SC', 'PingFang SC', sans-serif" font-size="${labelSize}" font-weight="${layout.depth === 0 ? 700 : 600}" fill="${tone.text}">${label}</text>`,
    summary ? `<text text-anchor="middle" font-family="'Noto Sans SC', 'PingFang SC', sans-serif" font-size="${summarySize}" fill="${tone.muted}">${summary}</text>` : '',
    '</g>',
  ].join('')
}

/**
 * 用途：执行getExportTone相关业务逻辑。
 * @param depth 调用方传入的depth参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function getExportTone(depth: number) {
  return exportTones[Math.min(depth, exportTones.length - 1)]
}

/**
 * 用途：执行wrapSvgText相关业务逻辑。
 * @param value 调用方传入的value参数，用于驱动当前前端逻辑。
 * @param maxUnits 调用方传入的maxUnits参数，用于驱动当前前端逻辑。
 * @param maxLines 调用方传入的maxLines参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function wrapSvgText(value: string, maxUnits: number, maxLines: number) {
  const normalized = value.trim().replace(/\s+/g, ' ')
  if (!normalized) return []

  const lines: string[] = []
  let current = ''
  let currentUnits = 0
  let truncated = false

  for (const char of Array.from(normalized)) {
    const charUnits = getTextUnit(char)
    if (current && currentUnits + charUnits > maxUnits) {
      lines.push(current.trim())
      if (lines.length === maxLines) {
        truncated = true
        break
      }
      current = char
      currentUnits = charUnits
    } else {
      current += char
      currentUnits += charUnits
    }
  }

  if (!truncated && current.trim()) {
    lines.push(current.trim())
  }

  if (lines.length > maxLines) {
    lines.length = maxLines
    truncated = true
  }

  if (truncated && lines.length > 0) {
    lines[lines.length - 1] = withEllipsis(lines[lines.length - 1])
  }

  return lines
}

/**
 * 用途：执行getTextUnit相关业务逻辑。
 * @param char 调用方传入的char参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function getTextUnit(char: string) {
  return /[\x00-\x7F]/.test(char) ? 0.55 : 1
}

/**
 * 用途：执行withEllipsis相关业务逻辑。
 * @param value 调用方传入的value参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function withEllipsis(value: string) {
  const trimmed = value.replace(/[，。；、,.!?;:\s]+$/g, '')
  if (trimmed.length <= 1) return `${trimmed}...`
  return `${trimmed.slice(0, trimmed.length - 1)}...`
}

/**
 * 用途：执行escapeXml相关业务逻辑。
 * @param value 调用方传入的value参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function escapeXml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

/**
 * 用途：执行sanitizeFilename相关业务逻辑。
 * @param value 调用方传入的value参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function sanitizeFilename(value: string) {
  return value.trim().replace(/[\\/:*?"<>|]+/g, '-').replace(/\s+/g, ' ').slice(0, 80) || 'mindmap'
}

/**
 * 用途：执行formatSvgNumber相关业务逻辑。
 * @param value 调用方传入的value参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function formatSvgNumber(value: number) {
  return Number(value.toFixed(2))
}

/**
 * 用途：执行showCopyMessage相关业务逻辑。
 * @param message 调用方传入的message参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function showCopyMessage(message: string) {
  copyMessage.value = message
  if (copyTimer) window.clearTimeout(copyTimer)
  copyTimer = window.setTimeout(() => {
    copyMessage.value = ''
  }, 1800)
}
</script>

<template>
  <section class="mindmap-canvas relative flex h-full min-h-[560px] flex-1 flex-col overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-card)]">
    <div v-if="mindmap" class="absolute left-4 right-4 top-4 z-20 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)]/95 px-4 py-3 shadow-sm backdrop-blur">
      <div class="min-w-0">
        <div class="flex items-center gap-2">
          <h2 class="truncate font-heading text-base font-semibold text-[var(--color-text)]">{{ mindmap.title }}</h2>
          <span class="rounded bg-[var(--color-bg-secondary)] px-1.5 py-0.5 text-[10px] text-[var(--color-text-tertiary)]">v{{ mindmap.version }}</span>
        </div>
        <p class="mt-0.5 text-xs text-[var(--color-text-tertiary)]">{{ mindmap.source_ids.length }} 个来源 · {{ mindmap.nodes.length }} 个节点</p>
      </div>

      <div class="flex items-center gap-2">
        <span v-if="copyMessage" class="text-xs text-[var(--color-success)]">{{ copyMessage }}</span>
        <button class="inline-flex items-center gap-1.5 rounded-full border border-[var(--color-border)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]" type="button" @click="copyOutline">
          <Copy :size="14" />
          复制大纲
        </button>
        <button class="inline-flex items-center gap-1.5 rounded-full border border-[var(--color-border)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-accent-bg)] hover:text-[var(--color-accent)]" type="button" @click="downloadSvg">
          <Download :size="14" />
          下载 SVG
        </button>
        <div class="h-4 w-px bg-[var(--color-border)]" />
        <button class="rounded-full border border-[var(--color-border)] p-1.5 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]" type="button" title="放大" @click="zoomBy(0.1)">
          <ZoomIn :size="14" />
        </button>
        <button class="rounded-full border border-[var(--color-border)] p-1.5 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]" type="button" title="缩小" @click="zoomBy(-0.1)">
          <ZoomOut :size="14" />
        </button>
        <button class="rounded-full border border-[var(--color-border)] p-1.5 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]" type="button" title="重置视图" @click="resetView">
          <RotateCcw :size="14" />
        </button>
        <span class="w-10 text-right text-[10px] text-[var(--color-text-tertiary)]">{{ scaleLabel }}</span>
      </div>
    </div>

    <div v-if="loading" class="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-[var(--color-card)]/90">
      <div class="h-9 w-9 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-accent)]" />
      <p class="text-sm font-medium text-[var(--color-text)]">AI 正在整理知识脉络</p>
      <p class="text-xs text-[var(--color-text-tertiary)]">正在生成层级导图，请稍后...</p>
    </div>

    <div
      v-else-if="tree"
      class="relative min-h-0 flex-1 cursor-grab overflow-hidden active:cursor-grabbing"
      @pointerdown="startPan"
      @pointermove="movePan"
      @pointerup="endPan"
      @pointercancel="endPan"
      @pointerleave="endPan"
      @wheel.prevent="handleWheel"
    >
      <div
        class="absolute origin-left select-none transition-transform duration-75"
        :style="{ left: '8%', top: '50%', transform: `translate(${offset.x}px, ${offset.y}px) translateY(-50%) scale(${scale})` }"
      >
        <div class="flex items-center">
          <MindMapTreeNode :node="tree" />
        </div>
      </div>
    </div>

    <div v-else class="flex min-h-[560px] flex-1 items-center justify-center px-6 text-center text-sm text-[var(--color-text-secondary)]">
      {{ emptyText }}
    </div>
  </section>
</template>

<style scoped>
.mindmap-canvas {
  background:
    radial-gradient(circle at 18px 18px, rgba(31, 108, 159, 0.08) 1.2px, transparent 1.3px) 0 0 / 28px 28px,
    linear-gradient(135deg, color-mix(in srgb, var(--color-card) 88%, var(--color-accent-bg)), var(--color-card));
}

.dark .mindmap-canvas {
  background:
    radial-gradient(circle at 18px 18px, rgba(74, 158, 214, 0.13) 1.2px, transparent 1.3px) 0 0 / 28px 28px,
    linear-gradient(135deg, color-mix(in srgb, var(--color-card) 90%, var(--color-accent-bg)), var(--color-card));
}
</style>
