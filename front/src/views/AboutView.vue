<!--
模块职责：Vue 页面组件，负责组合业务 API、页面状态和用户交互。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
<script setup lang="ts">
import { GitFork } from '@lucide/vue'
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-6">
    <h1 class="font-heading text-xl font-semibold">关于我们</h1>
    <div class="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] space-y-6 p-6">
      <p class="text-sm leading-7 text-[var(--color-text-secondary)]">
        云笺集是一个智能笔记与知识管理平台，结合 AI 大模型能力，帮助你更好地记录、整理和复盘知识。
      </p>

      <div>
        <h2 class="mb-3 text-sm font-medium text-[var(--color-text)]">技术栈</h2>
        <div class="flex flex-wrap gap-2">
          <span class="rounded-full bg-[var(--color-accent-bg)] px-2.5 py-1 text-xs text-[var(--color-accent)]">Vue</span>
          <span class="rounded-full bg-[var(--color-accent-bg)] px-2.5 py-1 text-xs text-[var(--color-accent)]">FastAPI</span>
          <span class="rounded-full bg-[var(--color-accent-bg)] px-2.5 py-1 text-xs text-[var(--color-accent)]">PostgreSQL</span>
          <span class="rounded-full bg-[var(--color-accent-bg)] px-2.5 py-1 text-xs text-[var(--color-accent)]">pgvector</span>
          <span class="rounded-full bg-[var(--color-accent-bg)] px-2.5 py-1 text-xs text-[var(--color-accent)]">LangChain</span>
        </div>
      </div>

      <div>
        <h2 class="mb-3 text-sm font-medium text-[var(--color-text)]">功能特性</h2>
        <ul class="space-y-2">
          <li class="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
            <span class="h-1.5 w-1.5 rounded-full bg-[var(--color-accent)]" />
            AI 智能对话
          </li>
          <li class="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
            <span class="h-1.5 w-1.5 rounded-full bg-[var(--color-accent)]" />
            笔记管理
          </li>
          <li class="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
            <span class="h-1.5 w-1.5 rounded-full bg-[var(--color-accent)]" />
            知识库管理
          </li>
          <li class="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
            <span class="h-1.5 w-1.5 rounded-full bg-[var(--color-accent)]" />
            间隔复习
          </li>
        </ul>
      </div>

      <a
        href="https://github.com/RMA-MUN/LangChain-RAG-FastAPI-Service"
        target="_blank"
        rel="noopener noreferrer"
        class="inline-flex items-center gap-2 text-sm text-[var(--color-accent)] transition-colors hover:underline"
      >
        <GitFork :size="16" />
        GitHub 仓库
      </a>
    </div>
  </div>
</template>
