<!--
模块职责：前端源码模块，封装 RAGNotebook 客户端的可维护逻辑。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppDialogHost from './components/AppDialogHost.vue'
</script>

<template>
  <RouterView />
  <AppDialogHost />
</template>
