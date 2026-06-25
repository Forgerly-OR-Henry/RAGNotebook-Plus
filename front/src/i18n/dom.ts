import { nextTick, watch } from 'vue'
import type { useLanguageStore } from '../stores/useLanguageStore'
import { translateEnglish } from './index'

type LanguageStore = ReturnType<typeof useLanguageStore>

const TEXT_ATTRS = ['placeholder', 'title', 'aria-label', 'alt'] as const

const textOriginals = new WeakMap<Text, { original: string, translated: string }>()
const attrOriginals = new WeakMap<Element, Map<string, { original: string, translated: string }>>()

let observer: MutationObserver | null = null
let observedStore: LanguageStore | null = null
let translateScheduled = false
let translatedEnglishOnce = false

const OBSERVER_CONFIG: MutationObserverInit = {
  childList: true,
  subtree: true,
  characterData: true,
  attributes: true,
  attributeFilter: [...TEXT_ATTRS],
}

export function installDomI18n(languageStore: LanguageStore) {
  if (typeof window === 'undefined' || typeof document === 'undefined') return

  languageStore.initLanguage()
  observedStore = languageStore

  watch(
    () => languageStore.lang,
    async (lang) => {
      await nextTick()
      if (lang === 'en-US') {
        scheduleTranslate(languageStore)
        startObserver(languageStore)
      } else {
        stopObserver()
        if (translatedEnglishOnce) scheduleTranslate(languageStore)
      }
    },
    { immediate: true },
  )

  if (languageStore.lang === 'en-US') startObserver(languageStore)
}

function startObserver(languageStore: LanguageStore) {
  if (!document.body) {
    window.addEventListener('DOMContentLoaded', () => startObserver(languageStore), { once: true })
    return
  }

  observer?.disconnect()
  observer = new MutationObserver(() => {
    if (languageStore.lang !== 'en-US') return
    scheduleTranslate(languageStore)
  })
  observer.observe(document.body, OBSERVER_CONFIG)
}

function stopObserver() {
  observer?.disconnect()
  observer = null
}

function scheduleTranslate(languageStore: LanguageStore) {
  if (translateScheduled) return
  translateScheduled = true

  window.requestAnimationFrame(() => {
    translateScheduled = false
    const shouldResumeObserver = observer !== null && languageStore.lang === 'en-US'
    observer?.disconnect()
    translateRoot(languageStore)
    if (languageStore.lang === 'en-US') translatedEnglishOnce = true
    if (shouldResumeObserver && document.body && observedStore === languageStore) {
      observer?.observe(document.body, OBSERVER_CONFIG)
    }
  })
}

function translateRoot(languageStore: LanguageStore) {
  if (!document.body) return
  translateNode(document.body, languageStore.lang)
}

function translateNode(node: Node, lang: string) {
  if (node.nodeType === Node.TEXT_NODE) {
    translateTextNode(node as Text, lang)
    return
  }

  if (!(node instanceof Element)) return
  if (node.closest('[data-i18n-skip]')) return

  translateAttributes(node, lang)
  if (shouldSkipChildren(node)) return

  node.childNodes.forEach((child) => translateNode(child, lang))
}

function translateTextNode(node: Text, lang: string) {
  let state = textOriginals.get(node)
  if (!state || (node.data !== state.original && node.data !== state.translated)) {
    state = { original: node.data, translated: node.data }
    textOriginals.set(node, state)
  }

  if (lang !== 'en-US') {
    node.data = state.original
    state.translated = state.original
    return
  }

  const leading = state.original.match(/^\s*/)?.[0] ?? ''
  const trailing = state.original.match(/\s*$/)?.[0] ?? ''
  const body = state.original.trim()
  if (!body) return

  const translated = translateEnglish(body)
  state.translated = translated === body ? state.original : `${leading}${translated}${trailing}`
  if (node.data !== state.translated) node.data = state.translated
}

function translateAttributes(element: Element, lang: string) {
  for (const attr of TEXT_ATTRS) {
    const current = element.getAttribute(attr)
    if (!current) continue

    let originals = attrOriginals.get(element)
    if (!originals) {
      originals = new Map()
      attrOriginals.set(element, originals)
    }
    const state = originals.get(attr)
    if (!state || (current !== state.original && current !== state.translated)) {
      originals.set(attr, { original: current, translated: current })
    }

    const nextState = originals.get(attr)
    if (!nextState) continue

    nextState.translated = lang === 'en-US' ? translateEnglish(nextState.original) : nextState.original
    if (current !== nextState.translated) element.setAttribute(attr, nextState.translated)
  }
}

function shouldSkipChildren(element: Element) {
  const tag = element.tagName.toLowerCase()
  if (['script', 'style', 'textarea', 'input'].includes(tag)) return true
  if ((element as HTMLElement).isContentEditable) return true
  return false
}
