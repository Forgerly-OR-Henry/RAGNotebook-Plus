/**
 * 模块职责：前端源码模块，封装 RAGNotebook 客户端的可维护逻辑。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
import DOMPurify from 'dompurify'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import { Marked, type TokenizerAndRendererExtension, type Tokens } from 'marked'
import { common, createLowlight } from 'lowlight'
import type { Element, Root, RootContent } from 'hast'

/**
 * 类型：`MathToken` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
type MathToken = Tokens.Generic & {
  text: string
}

const lowlight = createLowlight(common)
const supportedLanguages = new Set(lowlight.listLanguages())
const languageAliases: Record<string, string> = {
  csharp: 'csharp',
  cs: 'csharp',
  html: 'xml',
  js: 'javascript',
  md: 'markdown',
  mjs: 'javascript',
  py: 'python',
  sh: 'bash',
  shell: 'bash',
  ts: 'typescript',
  vue: 'xml',
  yml: 'yaml',
}

const sanitizeAttrs = [
  'aria-hidden',
  'checked',
  'class',
  'disabled',
  'rel',
  'style',
  'target',
]

/**
 * 用途：执行escapeHtml相关业务逻辑。
 * @param value 调用方传入的value参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

/**
 * 用途：执行normalizeLanguage相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function normalizeLanguage(value?: string) {
  const raw = (value || '').match(/^\S+/)?.[0].toLowerCase() || ''
  if (!raw) return ''
  const normalized = languageAliases[raw] || raw
  return supportedLanguages.has(normalized) ? normalized : ''
}

/**
 * 用途：执行renderProperty相关业务逻辑。
 * @param name 调用方传入的name参数，用于驱动当前前端逻辑。
 * @param value 调用方传入的value参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function renderProperty(name: string, value: unknown) {
  if (value === null || value === undefined || value === false) return ''
  const attrName = name === 'className' ? 'class' : name
  if (value === true) return ` ${escapeHtml(attrName)}`
  const attrValue = Array.isArray(value) ? value.join(' ') : String(value)
  return ` ${escapeHtml(attrName)}="${escapeHtml(attrValue)}"`
}

/**
 * 用途：执行hastToHtml相关业务逻辑。
 * @param node 调用方传入的node参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function hastToHtml(node: Root | RootContent): string {
  if (node.type === 'root') {
    return node.children.map((child) => hastToHtml(child)).join('')
  }
  if (node.type === 'text') {
    return escapeHtml(String(node.value))
  }
  if (node.type !== 'element') {
    return ''
  }

  const element = node as Element
  const attrs = Object.entries(element.properties || {})
    .map(([name, value]) => renderProperty(name, value))
    .join('')
  /**
   * 用途：执行children相关业务逻辑。
   * 参数：无显式业务参数。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const children = element.children.map((child) => hastToHtml(child)).join('')
  return `<${element.tagName}${attrs}>${children}</${element.tagName}>`
}

/**
 * 用途：执行renderCodeBlock相关业务逻辑。
 * @param text 调用方传入的text参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function renderCodeBlock(text: string, lang?: string) {
  const language = normalizeLanguage(lang)

  try {
    const tree = language ? lowlight.highlight(language, text) : lowlight.highlightAuto(text)
    const detectedLanguage = language || tree.data?.language || 'text'
    const languageClass = `language-${escapeHtml(detectedLanguage)}`
    return `<pre><code class="hljs ${languageClass}">${hastToHtml(tree)}</code></pre>`
  } catch {
    const fallbackLanguage = language ? ` language-${escapeHtml(language)}` : ''
    return `<pre><code class="hljs${fallbackLanguage}">${escapeHtml(text)}</code></pre>`
  }
}

/**
 * 用途：执行renderMath相关业务逻辑。
 * @param text 调用方传入的text参数，用于驱动当前前端逻辑。
 * @param displayMode 调用方传入的displayMode参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function renderMath(text: string, displayMode: boolean) {
  return katex.renderToString(text.trim(), {
    displayMode,
    output: 'html',
    throwOnError: false,
    strict: 'ignore',
    trust: false,
  })
}

/**
 * 用途：执行firstExistingIndex相关业务逻辑。
 * @param items 调用方传入的items参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function firstExistingIndex(...items: number[]) {
  /**
   * 用途：执行positive相关业务逻辑。
   * 参数：无显式业务参数。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const positive = items.filter((item) => item >= 0)
  return positive.length ? Math.min(...positive) : undefined
}

/**
 * 用途：执行findClosingDollar相关业务逻辑。
 * @param src 调用方传入的src参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function findClosingDollar(src: string) {
  for (let index = 1; index < src.length; index += 1) {
    if (src[index] === '$' && src[index - 1] !== '\\') {
      return index
    }
  }
  return -1
}

const blockMathExtension: TokenizerAndRendererExtension = {
  name: 'mathBlock',
  level: 'block',
  start(src) {
    return firstExistingIndex(src.indexOf('$$'), src.indexOf('\\['))
  },
  tokenizer(src) {
    const dollarMatch = /^\$\$\s*\n?([\s\S]+?)\n?\$\$(?=\s*(?:\n|$))/.exec(src)
    if (dollarMatch) {
      return {
        type: 'mathBlock',
        raw: dollarMatch[0],
        text: dollarMatch[1],
      }
    }

    const bracketMatch = /^\\\[\s*\n?([\s\S]+?)\n?\\\](?=\s*(?:\n|$))/.exec(src)
    if (bracketMatch) {
      return {
        type: 'mathBlock',
        raw: bracketMatch[0],
        text: bracketMatch[1],
      }
    }

    return undefined
  },
  renderer(token) {
    return `<div class="math math-display">${renderMath((token as MathToken).text, true)}</div>`
  },
}

const inlineMathExtension: TokenizerAndRendererExtension = {
  name: 'mathInline',
  level: 'inline',
  start(src) {
    return firstExistingIndex(src.indexOf('$'), src.indexOf('\\('))
  },
  tokenizer(src) {
    const parenMatch = /^\\\(([\s\S]+?)\\\)/.exec(src)
    if (parenMatch && !parenMatch[1].includes('\n')) {
      return {
        type: 'mathInline',
        raw: parenMatch[0],
        text: parenMatch[1],
      }
    }

    if (!src.startsWith('$') || src.startsWith('$$')) {
      return undefined
    }

    const closingIndex = findClosingDollar(src)
    if (closingIndex <= 1) {
      return undefined
    }

    const text = src.slice(1, closingIndex)
    if (!text.trim() || text.includes('\n')) {
      return undefined
    }

    return {
      type: 'mathInline',
      raw: src.slice(0, closingIndex + 1),
      text,
    }
  },
  renderer(token) {
    return `<span class="math math-inline">${renderMath((token as MathToken).text, false)}</span>`
  },
}

const markdown = new Marked({
  async: false,
  breaks: true,
  gfm: true,
  extensions: [blockMathExtension, inlineMathExtension],
  renderer: {
    code({ text, lang }: Tokens.Code) {
      return renderCodeBlock(text, lang)
    },
  },
})

/**
 * 用途：执行renderMarkdownHtml相关业务逻辑。
 * @param content 调用方传入的content参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
export function renderMarkdownHtml(content: string) {
  const rawHtml = markdown.parse(content || '', { async: false }) as string
  return DOMPurify.sanitize(rawHtml, {
    USE_PROFILES: { html: true },
    ADD_ATTR: sanitizeAttrs,
  })
}
