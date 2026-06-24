import DOMPurify from 'dompurify'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import { Marked, type TokenizerAndRendererExtension, type Tokens } from 'marked'
import { common, createLowlight } from 'lowlight'
import type { Element, Root, RootContent } from 'hast'

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

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function normalizeLanguage(value?: string) {
  const raw = (value || '').match(/^\S+/)?.[0].toLowerCase() || ''
  if (!raw) return ''
  const normalized = languageAliases[raw] || raw
  return supportedLanguages.has(normalized) ? normalized : ''
}

function renderProperty(name: string, value: unknown) {
  if (value === null || value === undefined || value === false) return ''
  const attrName = name === 'className' ? 'class' : name
  if (value === true) return ` ${escapeHtml(attrName)}`
  const attrValue = Array.isArray(value) ? value.join(' ') : String(value)
  return ` ${escapeHtml(attrName)}="${escapeHtml(attrValue)}"`
}

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
  const children = element.children.map((child) => hastToHtml(child)).join('')
  return `<${element.tagName}${attrs}>${children}</${element.tagName}>`
}

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

function renderMath(text: string, displayMode: boolean) {
  return katex.renderToString(text.trim(), {
    displayMode,
    output: 'html',
    throwOnError: false,
    strict: 'ignore',
    trust: false,
  })
}

function firstExistingIndex(...items: number[]) {
  const positive = items.filter((item) => item >= 0)
  return positive.length ? Math.min(...positive) : undefined
}

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

export function renderMarkdownHtml(content: string) {
  const rawHtml = markdown.parse(content || '', { async: false }) as string
  return DOMPurify.sanitize(rawHtml, {
    USE_PROFILES: { html: true },
    ADD_ATTR: sanitizeAttrs,
  })
}
