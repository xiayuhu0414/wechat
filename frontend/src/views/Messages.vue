<template>
  <div class="message-console">
    <section class="panel message-targets">
      <div class="panel-title">
        <h2>发送目标</h2>
        <div class="table-actions">
          <el-tag>串行任务</el-tag>
          <el-button :icon="Refresh" @click="loadContacts">刷新缓存</el-button>
        </div>
      </div>

      <el-tabs v-model="mode" class="contact-tabs">
        <el-tab-pane name="friends">
          <template #label>
            <span>好友发送</span>
            <el-tag size="small" type="success">{{ selectedFriends.length }}</el-tag>
          </template>

          <div class="tab-toolbar">
            <el-form inline>
              <el-form-item label="搜索">
                <el-input v-model="friendKeyword" clearable placeholder="昵称 / 通讯录名 / 微信号 / 标签" />
              </el-form-item>
            </el-form>
          </div>

          <el-table
            v-loading="loading"
            :data="filteredFriends"
            height="420"
            empty-text="暂无好友缓存，请先到通讯录同步好友"
            @selection-change="selectedFriends = $event"
          >
            <el-table-column type="selection" width="48" />
            <el-table-column prop="display_name" label="昵称" min-width="150" show-overflow-tooltip />
            <el-table-column prop="name" label="通讯录名" min-width="170" show-overflow-tooltip />
            <el-table-column prop="wx_number" label="微信号" min-width="140" show-overflow-tooltip />
            <el-table-column label="标签" min-width="220">
              <template #default="{ row }">
                <div class="table-tags">
                  <el-tag v-for="tag in row.tags" :key="tag" size="small">{{ tag }}</el-tag>
                  <span v-if="!row.tags?.length" class="muted">未打标签</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="last_synced_at" label="最后同步" min-width="170" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane name="tags">
          <template #label>
            <span>标签好友发送</span>
            <el-tag size="small" type="primary">{{ tagTargets.length }}</el-tag>
          </template>

          <div class="tag-send-layout">
            <el-form label-width="88px">
              <el-form-item label="好友标签">
                <el-select v-model="selectedTags" multiple filterable placeholder="自动提取标签候选，可搜索选择">
                  <el-option v-for="tag in extractedFriendTags" :key="tag" :label="tag" :value="tag" />
                </el-select>
              </el-form-item>
              <el-form-item label="匹配方式">
                <el-radio-group v-model="tagMatchMode">
                  <el-radio-button label="any">任一标签</el-radio-button>
                  <el-radio-button label="all">全部标签</el-radio-button>
                </el-radio-group>
              </el-form-item>
            </el-form>
            <div class="preview-box compact">
              <strong>匹配好友 {{ tagTargets.length }} 人</strong>
              <p class="muted">标签群发基于本地 SQLite 标签，不会修改微信内置标签。</p>
            </div>
          </div>

          <div class="tag-candidates">
            <span class="muted">标签候选</span>
            <el-tag
              v-for="tag in extractedFriendTags"
              :key="tag"
              class="clickable-tag"
              :effect="selectedTags.includes(tag) ? 'dark' : 'plain'"
              :type="selectedTags.includes(tag) ? 'primary' : 'info'"
              size="small"
              @click="toggleTag(tag)"
            >
              {{ tag }}
            </el-tag>
            <span v-if="!extractedFriendTags.length" class="muted">暂无标签，请先在通讯录给好友打标签</span>
          </div>

          <el-table :data="tagTargets" height="360" empty-text="请选择好友标签">
            <el-table-column prop="display_name" label="昵称" min-width="150" show-overflow-tooltip />
            <el-table-column prop="name" label="通讯录名" min-width="170" show-overflow-tooltip />
            <el-table-column label="命中标签" min-width="220">
              <template #default="{ row }">
                <div class="table-tags">
                  <el-tag v-for="tag in matchedTags(row)" :key="tag" size="small">{{ tag }}</el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="last_synced_at" label="最后同步" min-width="170" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane name="groups">
          <template #label>
            <span>群聊发送</span>
            <el-tag size="small" type="warning">{{ selectedGroups.length }}</el-tag>
          </template>

          <div class="tab-toolbar">
            <el-form inline>
              <el-form-item label="搜索">
                <el-input v-model="groupKeyword" clearable placeholder="群名称 / 标签" />
              </el-form-item>
              <el-form-item label="@成员">
                <el-select v-model="form.at_members" multiple filterable allow-create default-first-option placeholder="群成员昵称，可为空">
                  <el-option v-for="item in form.at_members" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
            </el-form>
          </div>

          <el-table
            v-loading="loading"
            :data="filteredGroups"
            height="420"
            empty-text="暂无群聊缓存，请先到通讯录同步群聊"
            @selection-change="selectedGroups = $event"
          >
            <el-table-column type="selection" width="48" />
            <el-table-column prop="name" label="群名称" min-width="240" show-overflow-tooltip />
            <el-table-column prop="member_count" label="人数" width="90" />
            <el-table-column label="标签" min-width="220">
              <template #default="{ row }">
                <div class="table-tags">
                  <el-tag v-for="tag in row.tags" :key="tag" size="small">{{ tag }}</el-tag>
                  <span v-if="!row.tags?.length" class="muted">未打标签</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="last_synced_at" label="最后同步" min-width="170" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </section>

    <section class="panel message-composer">
      <div class="panel-title">
        <h2>发送内容</h2>
        <el-tag :type="targetCount ? 'success' : 'info'">目标 {{ targetCount }}</el-tag>
      </div>

      <el-form label-width="96px" :model="form">
        <el-form-item label="文本消息">
          <el-input v-model="messageText" type="textarea" :rows="8" placeholder="一行一条消息，会按顺序发送" />
        </el-form-item>

        <el-form-item label="图片">
          <div class="attachment-block">
            <el-upload :show-file-list="false" accept="image/*" :http-request="uploadImage">
              <el-button :icon="Picture">上传图片</el-button>
            </el-upload>
            <span class="muted">可多张，按附件发送</span>
          </div>
        </el-form-item>

        <el-form-item label="文件">
          <div class="attachment-block">
            <el-upload :show-file-list="false" :http-request="uploadFile">
              <el-button :icon="FolderAdd">上传文件</el-button>
            </el-upload>
            <el-input v-model="manualPath" placeholder="D:\path\file.txt">
              <template #append><el-button @click="addManualPath">添加路径</el-button></template>
            </el-input>
          </div>
        </el-form-item>

        <el-form-item label="附件列表">
          <div class="attachment-list">
            <div v-for="(file, index) in attachments" :key="`${file.path}-${index}`" class="attachment-item">
              <el-icon><component :is="file.kind === 'image' ? Picture : FolderAdd" /></el-icon>
              <div>
                <strong>{{ file.filename }}</strong>
                <span>{{ file.kind === 'image' ? '图片' : '文件' }}</span>
              </div>
              <el-button link type="danger" :icon="Delete" @click="attachments.splice(index, 1)">移除</el-button>
            </div>
            <span v-if="!attachments.length" class="muted">暂无附件</span>
          </div>
        </el-form-item>

        <div class="grid three">
          <el-form-item label="发送间隔">
            <el-input-number v-model="form.send_delay" :min="0" :step="0.1" />
          </el-form-item>
          <el-form-item label="搜索页数">
            <el-input-number v-model="form.search_pages" :min="0" :step="1" />
          </el-form-item>
          <el-form-item label="关闭微信">
            <el-switch v-model="form.close_weixin" />
          </el-form-item>
          <el-form-item label="文本先发">
            <el-switch v-model="form.messages_first" />
          </el-form-item>
        </div>
      </el-form>

      <div class="preview-box send-preview">
        <strong>发送预览</strong>
        <p class="muted">{{ previewText }}</p>
        <div class="content-stats">
          <el-tag size="small">文本 {{ messages.length }}</el-tag>
          <el-tag size="small" type="success">图片 {{ imageCount }}</el-tag>
          <el-tag size="small" type="warning">文件 {{ fileCount }}</el-tag>
        </div>
        <div class="target-chips scroll-thin">
          <el-tag v-for="target in previewTargets" :key="target" size="small">{{ target }}</el-tag>
          <el-tag v-if="targetCount > previewTargets.length" size="small" type="info">
            还有 {{ targetCount - previewTargets.length }} 个
          </el-tag>
        </div>
      </div>

      <div class="form-actions">
        <el-button @click="reset">清空</el-button>
        <el-button type="primary" :icon="Promotion" :disabled="!canSubmit" @click="submit">创建发送任务</el-button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, FolderAdd, Picture, Promotion, Refresh } from '@element-plus/icons-vue'
import { api } from '../api/client'

const emit = defineEmits(['task-created'])
const mode = ref('friends')
const loading = ref(false)
const friends = ref([])
const groups = ref([])
const friendTags = ref([])
const selectedFriends = ref([])
const selectedGroups = ref([])
const selectedTags = ref([])
const tagMatchMode = ref('any')
const friendKeyword = ref('')
const groupKeyword = ref('')
const messageText = ref('')
const manualPath = ref('')
const attachments = ref([])
const form = reactive({
  at_members: [],
  send_delay: 0.2,
  search_pages: 5,
  close_weixin: false,
  messages_first: true,
})

const filteredFriends = computed(() => {
  const keyword = friendKeyword.value.trim().toLowerCase()
  if (!keyword) return friends.value
  return friends.value.filter((friend) => {
    const values = [friend.display_name, friend.name, friend.wx_number, friend.phone, ...(friend.tags || [])]
    return values.some((value) => String(value || '').toLowerCase().includes(keyword))
  })
})

const filteredGroups = computed(() => {
  const keyword = groupKeyword.value.trim().toLowerCase()
  if (!keyword) return groups.value
  return groups.value.filter((group) => {
    const values = [group.name, group.display_name, ...(group.tags || [])]
    return values.some((value) => String(value || '').toLowerCase().includes(keyword))
  })
})

const extractedFriendTags = computed(() => {
  const tags = new Set(friendTags.value)
  friends.value.forEach((friend) => (friend.tags || []).forEach((tag) => tags.add(tag)))
  return [...tags].filter(Boolean).sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'))
})

const tagTargets = computed(() => {
  if (!selectedTags.value.length) return []
  return friends.value.filter((friend) => {
    const tags = friend.tags || []
    if (tagMatchMode.value === 'all') return selectedTags.value.every((tag) => tags.includes(tag))
    return selectedTags.value.some((tag) => tags.includes(tag))
  })
})

const activeTargets = computed(() => {
  if (mode.value === 'friends') return selectedFriends.value
  if (mode.value === 'tags') return tagTargets.value
  return selectedGroups.value
})
const targetNames = computed(() => [...new Set(activeTargets.value.map((item) => item.name).filter(Boolean))])
const messages = computed(() => messageText.value.split('\n').map((line) => line.trim()).filter(Boolean))
const imageCount = computed(() => attachments.value.filter((file) => file.kind === 'image').length)
const fileCount = computed(() => attachments.value.filter((file) => file.kind !== 'image').length)
const targetCount = computed(() => targetNames.value.length)
const previewTargets = computed(() => targetNames.value.slice(0, 12))
const canSubmit = computed(() => targetNames.value.length > 0 && (messages.value.length > 0 || attachments.value.length > 0))
const previewText = computed(() => {
  const modeText = mode.value === 'friends' ? '好友发送' : mode.value === 'tags' ? '标签好友发送' : '群聊发送'
  const taskType = attachments.value.length ? '附件任务' : '文本任务'
  return `${modeText}，目标 ${targetCount.value} 个，消息 ${messages.value.length} 条，附件 ${attachments.value.length} 个，将创建${taskType}并进入串行任务队列。`
})

function matchedTags(row) {
  return (row.tags || []).filter((tag) => selectedTags.value.includes(tag))
}

function toggleTag(tag) {
  if (selectedTags.value.includes(tag)) {
    selectedTags.value = selectedTags.value.filter((item) => item !== tag)
  } else {
    selectedTags.value = [...selectedTags.value, tag]
  }
}

async function loadContacts() {
  loading.value = true
  try {
    const [friendRows, groupRows, tags] = await Promise.all([
      api.get('/api/contacts/friends/cache'),
      api.get('/api/contacts/groups/cache'),
      api.get('/api/contacts/tags?type=friend'),
    ])
    friends.value = friendRows
    groups.value = groupRows
    friendTags.value = tags
  } finally {
    loading.value = false
  }
}

async function uploadAttachment(options, kind) {
  const data = new FormData()
  data.append('file', options.file)
  const result = await api.upload('/api/files/upload', data)
  attachments.value.push({ ...result, kind })
  ElMessage.success(kind === 'image' ? '图片已上传' : '文件已上传')
}

async function uploadImage(options) {
  await uploadAttachment(options, 'image')
}

async function uploadFile(options) {
  await uploadAttachment(options, 'file')
}

function fileNameFromPath(path) {
  return path.split(/[\\/]/).pop() || path
}

function guessAttachmentKind(path) {
  return /\.(png|jpe?g|gif|bmp|webp)$/i.test(path) ? 'image' : 'file'
}

function addAttachmentPath(path, kind) {
  if (!path) return
  if (attachments.value.some((file) => file.path === path)) return
  attachments.value.push({
    filename: fileNameFromPath(path),
    path,
    kind: kind || guessAttachmentKind(path),
  })
}

function addManualPath() {
  const path = manualPath.value.trim()
  addAttachmentPath(path)
  manualPath.value = ''
}

function reset() {
  selectedFriends.value = []
  selectedGroups.value = []
  selectedTags.value = []
  form.at_members = []
  attachments.value = []
  manualPath.value = ''
  messageText.value = ''
}

async function submit() {
  if (!canSubmit.value) {
    ElMessage.warning('请选择发送目标，并填写文本或添加附件')
    return
  }
  if (attachments.value.length) {
    await api.post('/api/files/send', {
      targets: targetNames.value,
      files: attachments.value.map((file) => file.path),
      messages: messages.value,
      messages_first: form.messages_first,
      at_members: mode.value === 'groups' ? form.at_members : [],
      send_delay: form.send_delay,
      search_pages: form.search_pages,
      close_weixin: form.close_weixin,
    })
    ElMessage.success('附件发送任务已创建')
  } else {
    await api.post('/api/messages/send', {
      targets: targetNames.value,
      messages: messages.value,
      at_members: mode.value === 'groups' ? form.at_members : [],
      send_delay: form.send_delay,
      search_pages: form.search_pages,
      close_weixin: form.close_weixin,
    })
    ElMessage.success('消息任务已创建')
  }
  emit('task-created')
}

onMounted(loadContacts)
</script>
