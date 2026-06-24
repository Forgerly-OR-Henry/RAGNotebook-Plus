<!--
模块职责：生成过程展示组件，负责为 AI 生成类任务提供统一的动态等待反馈。
主要协作：由思维导图、快速测试等页面传入标题和阶段文案复用。
-->
<script setup lang="ts">
import { Brain, FileText, ListChecks, Network, Sparkles } from '@lucide/vue'

defineProps<{
  title: string
  message: string
}>()
</script>

<template>
  <div class="generation-progress" role="status" aria-live="polite">
    <div class="generation-stage" aria-hidden="true">
      <div class="link-line line-a" />
      <div class="link-line line-b" />
      <div class="link-line line-c" />

      <div class="source-tile tile-a">
        <FileText :size="18" />
      </div>
      <div class="source-tile tile-b">
        <Network :size="18" />
      </div>
      <div class="source-tile tile-c">
        <ListChecks :size="18" />
      </div>

      <div class="processor">
        <div class="processor-scan" />
        <Sparkles :size="18" class="processor-spark" />
        <Brain :size="30" />
      </div>

      <div class="data-strip strip-a" />
      <div class="data-strip strip-b" />
      <div class="data-strip strip-c" />
    </div>

    <div class="generation-copy">
      <h2>{{ title }}</h2>
      <p>{{ message }}</p>
    </div>

    <div class="generation-meter" aria-hidden="true">
      <span />
      <span />
      <span />
    </div>
  </div>
</template>

<style scoped>
.generation-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.25rem;
  color: var(--color-text);
}

.generation-stage {
  position: relative;
  width: min(19rem, 78vw);
  height: 11rem;
}

.processor {
  position: absolute;
  left: 50%;
  top: 50%;
  display: flex;
  width: 5.5rem;
  height: 5.5rem;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 1px solid var(--color-accent);
  border-radius: 0.5rem;
  background: var(--color-accent);
  color: #fff;
  box-shadow: 0 1rem 2.5rem rgb(37 99 235 / 18%);
  transform: translate(-50%, -50%);
}

.processor::before,
.processor::after {
  position: absolute;
  inset: 0.7rem;
  border: 1px solid rgb(255 255 255 / 32%);
  border-radius: 0.4rem;
  content: "";
}

.processor::after {
  inset: 1.15rem;
  opacity: 0.6;
  animation: processor-breathe 2.4s ease-in-out infinite;
}

.processor-scan {
  position: absolute;
  top: -25%;
  bottom: -25%;
  width: 1.25rem;
  background: rgb(255 255 255 / 28%);
  transform: rotate(18deg) translateX(-4.8rem);
  animation: processor-scan 2.6s ease-in-out infinite;
}

.processor-spark {
  position: absolute;
  right: 0.75rem;
  top: 0.75rem;
  opacity: 0.88;
  animation: spark-pop 2.2s ease-in-out infinite;
}

.source-tile {
  position: absolute;
  display: flex;
  width: 3.5rem;
  height: 2.75rem;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  background: var(--color-card);
  color: var(--color-accent);
  box-shadow: 0 0.75rem 1.75rem rgb(15 23 42 / 8%);
  animation: tile-work 3.2s ease-in-out infinite;
}

.tile-a {
  left: 0.4rem;
  top: 1.15rem;
}

.tile-b {
  right: 0.3rem;
  top: 1.45rem;
  animation-delay: 0.35s;
}

.tile-c {
  bottom: 1.05rem;
  left: 1.8rem;
  animation-delay: 0.7s;
}

.link-line {
  position: absolute;
  height: 1px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--color-border);
  transform-origin: left center;
}

.link-line::after {
  display: block;
  width: 42%;
  height: 100%;
  background: var(--color-accent);
  content: "";
  opacity: 0;
  transform: translateX(-120%);
  animation: line-pulse 2.4s ease-in-out infinite;
}

.line-a {
  left: 4rem;
  top: 3.1rem;
  width: 5.4rem;
  transform: rotate(12deg);
}

.line-b {
  right: 4rem;
  top: 3.45rem;
  width: 5.1rem;
  transform: rotate(168deg);
}

.line-b::after {
  animation-delay: 0.35s;
}

.line-c {
  bottom: 3.65rem;
  left: 5rem;
  width: 4.5rem;
  transform: rotate(-24deg);
}

.line-c::after {
  animation-delay: 0.7s;
}

.data-strip {
  position: absolute;
  width: 2.25rem;
  height: 0.4rem;
  border-radius: 999px;
  background: var(--color-accent-bg);
  opacity: 0.78;
  animation: strip-flow 2.8s ease-in-out infinite;
}

.strip-a {
  left: 4.75rem;
  top: 4.85rem;
}

.strip-b {
  right: 4.75rem;
  top: 5.85rem;
  animation-delay: 0.4s;
}

.strip-c {
  bottom: 2.15rem;
  left: 7rem;
  animation-delay: 0.8s;
}

.generation-copy {
  max-width: 28rem;
  text-align: center;
}

.generation-copy h2 {
  font-family: var(--font-heading);
  font-size: 1.125rem;
  font-weight: 600;
}

.generation-copy p {
  margin-top: 0.5rem;
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}

.generation-meter {
  display: grid;
  width: min(18rem, 72vw);
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.45rem;
}

.generation-meter span {
  height: 0.25rem;
  overflow: hidden;
  border-radius: 999px;
  background: var(--color-bg-secondary);
}

.generation-meter span::after {
  display: block;
  width: 48%;
  height: 100%;
  border-radius: inherit;
  background: var(--color-accent);
  content: "";
  transform: translateX(-110%);
  animation: meter-pass 1.8s ease-in-out infinite;
}

.generation-meter span:nth-child(2)::after {
  animation-delay: 0.18s;
}

.generation-meter span:nth-child(3)::after {
  animation-delay: 0.36s;
}

@keyframes tile-work {
  0%,
  100% {
    transform: translateY(0) scale(1);
  }
  45% {
    transform: translateY(-0.55rem) scale(1.04);
  }
  70% {
    transform: translateY(0.15rem) scale(0.98);
  }
}

@keyframes line-pulse {
  0% {
    opacity: 0;
    transform: translateX(-120%);
  }
  35% {
    opacity: 1;
  }
  75%,
  100% {
    opacity: 0;
    transform: translateX(260%);
  }
}

@keyframes processor-breathe {
  0%,
  100% {
    transform: scale(0.94);
  }
  50% {
    transform: scale(1.08);
  }
}

@keyframes processor-scan {
  0%,
  18% {
    transform: rotate(18deg) translateX(-4.8rem);
  }
  72%,
  100% {
    transform: rotate(18deg) translateX(5.4rem);
  }
}

@keyframes spark-pop {
  0%,
  100% {
    opacity: 0.45;
    transform: scale(0.86) rotate(0deg);
  }
  45% {
    opacity: 1;
    transform: scale(1.12) rotate(12deg);
  }
}

@keyframes strip-flow {
  0%,
  100% {
    opacity: 0.28;
    transform: translateX(-0.35rem);
  }
  50% {
    opacity: 0.9;
    transform: translateX(0.35rem);
  }
}

@keyframes meter-pass {
  0% {
    transform: translateX(-110%);
  }
  70%,
  100% {
    transform: translateX(240%);
  }
}

@media (prefers-reduced-motion: reduce) {
  .processor::after,
  .processor-scan,
  .processor-spark,
  .source-tile,
  .link-line::after,
  .data-strip,
  .generation-meter span::after {
    animation: none;
  }
}
</style>
