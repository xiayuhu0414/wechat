<template>
  <div class="grid two">
    <section class="panel">
      <div class="panel-title"><h2>规则</h2><el-button :icon="Refresh" @click="loadRules">刷新</el-button></div>
      <el-form label-width="86px" :model="rule">
        <el-form-item label="名称"><el-input v-model="rule.name" /></el-form-item>
        <el-form-item label="目标"><el-input v-model="rule.target" /></el-form-item>
        <el-form-item label="关键词"><el-input v-model="rule.keyword" /></el-form-item>
        <el-form-item label="回复"><el-input v-model="rule.reply" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="仅 @"><el-switch v-model="rule.at_only" /></el-form-item>
        <div class="form-actions"><el-button type="primary" @click="saveRule">保存规则</el-button></div>
      </el-form>
      <el-table :data="rules" height="280">
        <el-table-column prop="target" label="目标" />
        <el-table-column prop="keyword" label="关键词" />
        <el-table-column prop="reply" label="回复" show-overflow-tooltip />
      </el-table>
    </section>

    <section class="panel">
      <div class="panel-title"><h2>启动监听</h2><el-tag>运行中不可强制中断</el-tag></div>
      <el-form label-width="86px" :model="run">
        <el-form-item label="目标"><el-input v-model="run.target" /></el-form-item>
        <el-form-item label="时长"><el-input v-model="run.duration" placeholder="1min / 30s / 1h" /></el-form-item>
        <el-form-item label="仅 @"><el-switch v-model="run.at_only" /></el-form-item>
        <div class="form-actions"><el-button type="primary" :icon="VideoPlay" @click="start">创建监听任务</el-button></div>
      </el-form>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, VideoPlay } from '@element-plus/icons-vue'
import { api } from '../api/client'

const emit = defineEmits(['task-created'])
const rules = ref([])
const rule = reactive({ name: '', target: '', target_type: 'friend', keyword: '', reply: '', at_only: false, enabled: true })
const run = reactive({ target: '', duration: '1min', at_only: false })

async function loadRules() {
  rules.value = await api.get('/api/autoreply/rules')
}

async function saveRule() {
  await api.post('/api/autoreply/rules', rule)
  ElMessage.success('规则已保存')
  await loadRules()
}

async function start() {
  await api.post('/api/autoreply/start', run)
  ElMessage.success('监听任务已创建')
  emit('task-created')
}

onMounted(loadRules)
</script>

