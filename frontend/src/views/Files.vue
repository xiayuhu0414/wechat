<template>
  <section class="panel">
    <div class="panel-title">
      <h2>发送文件</h2>
      <el-upload :show-file-list="false" :http-request="upload">
        <el-button :icon="Upload">上传文件</el-button>
      </el-upload>
    </div>
    <el-form label-width="96px" :model="form">
      <el-form-item label="目标">
        <el-select v-model="form.targets" multiple filterable allow-create default-first-option placeholder="好友或群聊名称">
          <el-option v-for="item in form.targets" :key="item" :label="item" :value="item" />
        </el-select>
      </el-form-item>
      <el-form-item label="文件">
        <el-table :data="files" empty-text="先上传文件或填写本地绝对路径">
          <el-table-column prop="filename" label="文件名" />
          <el-table-column prop="path" label="路径" show-overflow-tooltip />
          <el-table-column width="80">
            <template #default="{ $index }"><el-button link type="danger" @click="files.splice($index, 1)">移除</el-button></template>
          </el-table-column>
        </el-table>
      </el-form-item>
      <el-form-item label="本地路径">
        <el-input v-model="manualPath" placeholder="D:\path\file.txt">
          <template #append><el-button @click="addManual">添加</el-button></template>
        </el-input>
      </el-form-item>
      <el-form-item label="附带消息">
        <el-input v-model="messageText" type="textarea" :rows="4" placeholder="一行一条消息，可为空" />
      </el-form-item>
      <el-form-item label="消息先发">
        <el-switch v-model="form.messages_first" />
      </el-form-item>
      <div class="form-actions">
        <el-button type="primary" :icon="Files" @click="submit">创建任务</el-button>
      </div>
    </el-form>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Files, Upload } from '@element-plus/icons-vue'
import { api } from '../api/client'

const emit = defineEmits(['task-created'])
const files = ref([])
const manualPath = ref('')
const messageText = ref('')
const form = reactive({ targets: [], messages_first: false })

async function upload(options) {
  const data = new FormData()
  data.append('file', options.file)
  const result = await api.upload('/api/files/upload', data)
  files.value.push(result)
  ElMessage.success('文件已上传')
}

function addManual() {
  if (!manualPath.value) return
  files.value.push({ filename: manualPath.value.split(/[\\/]/).pop(), path: manualPath.value })
  manualPath.value = ''
}

async function submit() {
  if (!form.targets.length || !files.value.length) {
    ElMessage.warning('请填写目标并选择文件')
    return
  }
  const messages = messageText.value.split('\n').map((line) => line.trim()).filter(Boolean)
  await api.post('/api/files/send', {
    ...form,
    files: files.value.map((file) => file.path),
    messages,
  })
  ElMessage.success('文件任务已创建')
  emit('task-created')
}
</script>

