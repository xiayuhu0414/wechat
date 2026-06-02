<template>
  <section class="panel development-panel">
    <div class="development-empty">
      <el-icon><Tools /></el-icon>
      <h2>{{ title }}</h2>
      <p>{{ description }}</p>
      <el-tag type="warning">开发中</el-tag>
    </div>
  </section>
</template>

<script setup>
import { Tools } from '@element-plus/icons-vue'

defineProps({
  title: {
    type: String,
    default: '模块开发中',
  },
  description: {
    type: String,
    default: '该能力入口已保留，后续会在这里接入可视化操作。',
  },
})
</script>

