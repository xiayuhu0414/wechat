<template>
  <section class="panel">
    <div class="panel-title"><h2>群管理入口</h2><el-tag type="warning">4.x 首版基础入口</el-tag></div>
    <el-alert
      title="当前 pyweixin 首版主要开放群成员与群聊信息读取；群名、公告、邀请、移除等写操作将通过后续能力注册接入。"
      type="info"
      :closable="false"
      show-icon
    />
    <div style="height: 16px" />
    <el-form inline>
      <el-form-item label="群名称"><el-input v-model="groupName" /></el-form-item>
      <el-form-item><el-button :icon="UserFilled" @click="loadMembers">拉取群成员</el-button></el-form-item>
    </el-form>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UserFilled } from '@element-plus/icons-vue'
import { api } from '../api/client'

const emit = defineEmits(['task-created'])
const groupName = ref('')

async function loadMembers() {
  if (!groupName.value) return ElMessage.warning('请填写群名称')
  await api.get(`/api/contacts/groups/${encodeURIComponent(groupName.value)}/members`)
  ElMessage.success('群成员任务已创建')
  emit('task-created')
}
</script>

