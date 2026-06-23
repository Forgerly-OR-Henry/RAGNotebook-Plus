<script setup lang="ts">
import { useLanguageStore } from '../stores/useLanguageStore'
import { useThemeStore } from '../stores/useThemeStore'
import { Languages, Moon, Sun } from '@lucide/vue'

const themeStore = useThemeStore()
const languageStore = useLanguageStore()
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-6">
    <h1 class="mb-2 font-heading text-xl font-semibold">设置</h1>

    <div class="space-y-6">
      <section class="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <Moon v-if="themeStore.theme === 'dark'" :size="18" class="text-[var(--color-text-secondary)]" />
            <Sun v-else :size="18" class="text-[var(--color-text-secondary)]" />
            <div>
              <p class="text-sm font-medium text-[var(--color-text)]">主题</p>
              <p class="text-xs text-[var(--color-text-tertiary)]">
                {{ themeStore.theme === 'light' ? '浅色模式' : '深色模式' }}
              </p>
            </div>
          </div>
          <button
            type="button"
            class="relative h-6 w-12 rounded-full transition-colors duration-300"
            :class="themeStore.theme === 'dark' ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-bg-tertiary)]'"
            @click="themeStore.toggleTheme()"
          >
            <span
              class="absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-all duration-300"
              :class="themeStore.theme === 'dark' ? 'right-0.5' : 'left-0.5'"
            />
          </button>
        </div>
      </section>

      <section class="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <Languages :size="18" class="text-[var(--color-text-secondary)]" />
            <div>
              <p class="text-sm font-medium text-[var(--color-text)]">语言</p>
              <p class="text-xs text-[var(--color-text-tertiary)]">
                {{ languageStore.lang === 'zh-CN' ? '中文' : 'English' }}
              </p>
            </div>
          </div>
          <div class="flex gap-2">
            <button
              type="button"
              class="rounded-md px-3 py-1.5 text-xs transition-colors"
              :class="languageStore.lang === 'zh-CN'
                ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]'
                : 'bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'"
              @click="languageStore.setLang('zh-CN')"
            >
              中文
            </button>
            <button
              type="button"
              class="rounded-md px-3 py-1.5 text-xs transition-colors"
              :class="languageStore.lang === 'en-US'
                ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]'
                : 'bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'"
              @click="languageStore.setLang('en-US')"
            >
              English
            </button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
