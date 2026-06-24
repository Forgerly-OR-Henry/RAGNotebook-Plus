<!--
模块职责：Vue 可复用组件，负责封装局部界面、交互状态和事件输出。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
<script setup lang="ts">
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

defineOptions({ name: 'MindMapTreeNode' })

withDefaults(defineProps<{
  node: MindMapTreeNodeData
  depth?: number
}>(), {
  depth: 0,
})

/**
 * 用途：执行nodeClass相关业务逻辑。
 * @param depth 调用方传入的depth参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function nodeClass(depth: number) {
  if (depth === 0) {
    return 'mindmap-node--root'
  }
  if (depth === 1) {
    return 'mindmap-node--depth-1'
  }
  if (depth === 2) {
    return 'mindmap-node--depth-2'
  }
  if (depth === 3) {
    return 'mindmap-node--depth-3'
  }
  return 'mindmap-node--leaf'
}
</script>

<template>
  <div class="mindmap-tree-row relative flex select-none items-center">
    <div v-if="depth > 0" class="mindmap-connector mindmap-connector--incoming" />

    <div
      class="mindmap-node-card z-10 shrink-0 text-center transition-transform duration-150 hover:-translate-y-0.5"
      :class="nodeClass(depth)"
      :title="node.summary || node.label"
    >
      <span class="mindmap-node-label block break-words">{{ node.label }}</span>
      <span v-if="node.summary" class="mindmap-node-summary">{{ node.summary }}</span>
    </div>

    <div v-if="node.children.length > 0" class="mindmap-connector mindmap-connector--outgoing" />

    <div v-if="node.children.length > 0" class="mindmap-children relative flex flex-col gap-4 py-3">
      <MindMapTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :depth="depth + 1"
      />
    </div>
  </div>
</template>

<style scoped>
.mindmap-tree-row {
  --mindmap-line: rgba(31, 108, 159, 0.24);
  --mindmap-line-strong: rgba(31, 108, 159, 0.42);
  isolation: isolate;
}

.mindmap-node-card {
  position: relative;
  min-width: 150px;
  max-width: 260px;
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: 18px;
  padding: 10px 16px;
  line-height: 1.35;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08), 0 1px 0 rgba(255, 255, 255, 0.65) inset;
}

.mindmap-node-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.4), transparent 44%);
  pointer-events: none;
}

.mindmap-node-label,
.mindmap-node-summary {
  position: relative;
  z-index: 1;
}

.mindmap-node-label {
  font-weight: 650;
}

.mindmap-node-summary {
  display: -webkit-box;
  margin-top: 4px;
  overflow: hidden;
  font-size: 10px;
  font-weight: 400;
  line-height: 1.45;
  opacity: 0.78;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.mindmap-node--root {
  min-width: 220px;
  border-radius: 24px;
  border-color: rgba(31, 108, 159, 0.2);
  background: linear-gradient(135deg, #1f6c9f, #2d87b5);
  color: #fff;
  font-size: 14px;
  box-shadow: 0 18px 38px rgba(31, 108, 159, 0.24), 0 1px 0 rgba(255, 255, 255, 0.32) inset;
}

.mindmap-node--root .mindmap-node-summary {
  color: #dcefff;
}

.mindmap-node--depth-1 {
  border-color: rgba(57, 166, 108, 0.32);
  background: linear-gradient(135deg, rgba(234, 248, 241, 0.98), rgba(216, 243, 228, 0.94));
  color: #14583a;
  font-size: 12px;
}

.mindmap-node--depth-2 {
  border-color: rgba(59, 143, 196, 0.3);
  background: linear-gradient(135deg, rgba(234, 245, 255, 0.98), rgba(218, 237, 250, 0.94));
  color: #195273;
  font-size: 11px;
}

.mindmap-node--depth-3 {
  border-color: rgba(217, 139, 24, 0.28);
  background: linear-gradient(135deg, rgba(255, 245, 227, 0.98), rgba(252, 234, 201, 0.94));
  color: #754a0b;
  font-size: 10.5px;
}

.mindmap-node--leaf {
  border-color: rgba(199, 90, 114, 0.24);
  background: linear-gradient(135deg, rgba(253, 240, 243, 0.98), rgba(248, 230, 234, 0.94));
  color: #7a2638;
  font-size: 10px;
}

.mindmap-connector {
  height: 2px;
  width: 34px;
  flex: 0 0 34px;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--mindmap-line), var(--mindmap-line-strong));
}

.mindmap-connector--incoming {
  background: linear-gradient(90deg, var(--mindmap-line-strong), var(--mindmap-line));
}

.mindmap-children::before {
  content: '';
  position: absolute;
  bottom: 22px;
  left: 0;
  top: 22px;
  width: 2px;
  border-radius: 999px;
  background: linear-gradient(180deg, transparent, var(--mindmap-line-strong) 12%, var(--mindmap-line-strong) 88%, transparent);
}

.dark .mindmap-tree-row {
  --mindmap-line: rgba(74, 158, 214, 0.26);
  --mindmap-line-strong: rgba(74, 158, 214, 0.46);
}

.dark .mindmap-node-card {
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.22), 0 1px 0 rgba(255, 255, 255, 0.06) inset;
}

.dark .mindmap-node-card::before {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.08), transparent 46%);
}

.dark .mindmap-node--depth-1 {
  border-color: rgba(102, 204, 147, 0.34);
  background: linear-gradient(135deg, rgba(23, 62, 43, 0.98), rgba(25, 78, 52, 0.94));
  color: #9be0b9;
}

.dark .mindmap-node--depth-2 {
  border-color: rgba(96, 181, 231, 0.32);
  background: linear-gradient(135deg, rgba(24, 55, 76, 0.98), rgba(25, 68, 94, 0.94));
  color: #a7d9f5;
}

.dark .mindmap-node--depth-3 {
  border-color: rgba(231, 182, 108, 0.32);
  background: linear-gradient(135deg, rgba(75, 54, 22, 0.98), rgba(92, 65, 25, 0.94));
  color: #f1d19e;
}

.dark .mindmap-node--leaf {
  border-color: rgba(220, 154, 172, 0.3);
  background: linear-gradient(135deg, rgba(76, 35, 45, 0.98), rgba(92, 41, 53, 0.94));
  color: #efb1c0;
}
</style>
