<template>
  <div class="moments-workbench">
    <section class="panel moments-publisher">
      <div class="panel-title">
        <div>
          <h2>朋友圈发布</h2>
          <span class="muted">文案确认后再创建发布任务</span>
        </div>
        <el-tag :type="mediaItems.length ? 'success' : 'info'">素材 {{ mediaItems.length }}/9</el-tag>
      </div>

      <div class="wechat-compose">
        <el-input
          v-model="postForm.text"
          type="textarea"
          :rows="8"
          maxlength="1200"
          show-word-limit
          placeholder="这一刻的想法..."
        />

        <div class="media-grid" aria-label="朋友圈九宫格素材">
          <div v-for="(item, index) in mediaItems" :key="item.path" class="media-cell">
            <el-icon class="media-icon"><component :is="item.kind === 'video' ? VideoCamera : Picture" /></el-icon>
            <strong>{{ item.filename }}</strong>
            <span>{{ item.kind === 'video' ? '视频' : '图片' }}</span>
            <el-button class="media-remove" :icon="Close" circle text @click="removeMedia(index)" />
          </div>

          <el-upload
            v-if="mediaItems.length < 9"
            class="media-upload"
            multiple
            accept="image/*,video/*"
            :show-file-list="false"
            :http-request="uploadMedia"
          >
            <div class="media-add">
              <el-icon><Plus /></el-icon>
              <span>上传</span>
            </div>
          </el-upload>
        </div>

        <div class="media-path-row">
          <el-input v-model="mediaPath" clearable placeholder="也可以粘贴本地图片或视频绝对路径" />
          <el-button :icon="Plus" @click="addMediaPath">添加路径</el-button>
        </div>
      </div>

      <div class="publisher-actions">
        <el-button @click="clearPost">清空</el-button>
        <el-button type="primary" :disabled="!canPost" @click="postMoments">创建发布任务</el-button>
      </div>
    </section>

    <section class="panel moments-ai">
      <div class="panel-title">
        <div>
          <h2>AI 文案助手</h2>
          <span class="muted">根据描述生成候选文案</span>
        </div>
        <el-button :icon="MagicStick" type="primary" :loading="copyLoading" @click="generateCopy">生成</el-button>
      </div>

      <el-form label-width="76px" :model="copyForm">
        <el-form-item label="描述">
          <el-input
            v-model="copyForm.description"
            type="textarea"
            :rows="5"
            placeholder="例如：周末团建，氛围轻松，不要太广告，适合客户看到"
          />
        </el-form-item>
        <el-form-item label="语气">
          <el-select v-model="copyForm.tone" filterable allow-create>
            <el-option label="自然真诚" value="自然真诚" />
            <el-option label="轻松幽默" value="轻松幽默" />
            <el-option label="专业可信" value="专业可信" />
            <el-option label="温暖生活感" value="温暖生活感" />
          </el-select>
        </el-form-item>
        <div class="ai-options">
          <el-form-item label="长度">
            <el-segmented v-model="copyForm.length" :options="['短', '中等', '长']" />
          </el-form-item>
          <el-form-item label="条数">
            <el-input-number v-model="copyForm.count" :min="1" :max="5" />
          </el-form-item>
          <el-form-item label="表情">
            <el-switch v-model="copyForm.include_emoji" />
          </el-form-item>
          <el-form-item label="营销">
            <el-switch v-model="copyForm.marketing" />
          </el-form-item>
        </div>
      </el-form>

      <div class="copy-result-list">
        <div v-for="(item, index) in copies" :key="index" class="copy-result-item">
          <p>{{ item }}</p>
          <div class="form-actions">
            <el-button @click="appendCopy(item)">追加</el-button>
            <el-button type="primary" @click="useCopy(item)">使用</el-button>
          </div>
        </div>
        <el-empty v-if="!copies.length" description="暂无文案" />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Close, MagicStick, Picture, Plus, VideoCamera } from '@element-plus/icons-vue'
import { api } from '../api/client'

const emit = defineEmits(['task-created'])
const copyLoading = ref(false)
const copies = ref([])
const mediaItems = ref([])
const mediaPath = ref('')

const postForm = reactive({ text: '' })
const copyForm = reactive({
  description: '',
  tone: '自然真诚',
  length: '中等',
  count: 3,
  include_emoji: false,
  marketing: false,
})

const canPost = computed(() => Boolean(postForm.text.trim() || mediaItems.value.length))

function mediaKind(path) {
  return /\.(mp4|mov|avi|mkv|webm)$/i.test(path) ? 'video' : 'image'
}

function filenameFromPath(path) {
  return path.split(/[\\/]/).pop() || path
}

function pushMedia(path, filename = filenameFromPath(path)) {
  if (!path || mediaItems.value.length >= 9 || mediaItems.value.some((item) => item.path === path)) return
  mediaItems.value.push({ path, filename, kind: mediaKind(path) })
}

async function uploadMedia(fileRequest) {
  const formData = new FormData()
  formData.append('file', fileRequest.file)
  const uploaded = await api.upload('/api/files/upload', formData)
  pushMedia(uploaded.path, uploaded.filename)
  ElMessage.success('素材已上传')
}

function addMediaPath() {
  pushMedia(mediaPath.value.trim())
  mediaPath.value = ''
}

function removeMedia(index) {
  mediaItems.value.splice(index, 1)
}

function clearPost() {
  postForm.text = ''
  mediaItems.value = []
  mediaPath.value = ''
}

async function postMoments() {
  await api.post('/api/moments/post', {
    text: postForm.text,
    medias: mediaItems.value.map((item) => item.path),
  })
  ElMessage.success('朋友圈发布任务已创建')
  emit('task-created')
}

async function generateCopy() {
  copyLoading.value = true
  try {
    const data = await api.post('/api/moments/copy', copyForm)
    copies.value = data.copies || []
    ElMessage.success('文案已生成')
  } finally {
    copyLoading.value = false
  }
}

function useCopy(item) {
  postForm.text = item
}

function appendCopy(item) {
  postForm.text = postForm.text ? `${postForm.text}\n${item}` : item
}
</script>
