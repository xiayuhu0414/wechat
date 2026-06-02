<template>
  <div class="grid">
    <section class="panel">
      <div class="panel-title">
        <h2>通讯录同步</h2>
        <div class="table-actions">
          <el-button-group>
            <el-button :icon="User" @click="syncFriends(false)">同步好友</el-button>
            <el-button :icon="User" @click="syncFriends(true)">同步好友详情</el-button>
            <el-button :icon="UserFilled" @click="syncGroups">同步群聊</el-button>
            <el-button :icon="Connection" @click="syncSelectedGroupMembers">同步群成员</el-button>
          </el-button-group>
          <el-button-group>
            <el-button type="danger" plain :icon="Delete" @click="clearFriends">清空好友库</el-button>
            <el-button type="danger" plain :icon="Delete" @click="clearGroups">清空群聊库</el-button>
          </el-button-group>
        </div>
      </div>
    </section>

    <section class="panel">
      <el-tabs v-model="activeContactTab" class="contact-tabs">
        <el-tab-pane name="friends">
          <template #label>
            <span>好友</span>
            <el-tag size="small" type="success">{{ friendCount }}</el-tag>
          </template>

          <div class="tab-toolbar">
            <el-form inline>
              <el-form-item label="搜索">
                <el-input v-model="friendKeyword" clearable placeholder="昵称 / 通讯录名 / 微信号 / 电话" @keyup.enter="loadFriends" />
              </el-form-item>
              <el-form-item>
                <el-button :icon="Search" @click="loadFriends">查询好友</el-button>
              </el-form-item>
            </el-form>
            <el-button :icon="Refresh" @click="loadFriends">刷新</el-button>
          </div>

          <el-table
            v-loading="friendsLoading"
            :data="friends"
            height="560"
            empty-text="暂无好友缓存，请先同步好友"
          >
            <el-table-column prop="display_name" label="昵称" min-width="160" show-overflow-tooltip />
            <el-table-column prop="name" label="通讯录名" min-width="180" show-overflow-tooltip />
            <el-table-column prop="wx_number" label="微信号" min-width="150" show-overflow-tooltip />
            <el-table-column prop="phone" label="电话" min-width="130" show-overflow-tooltip />
            <el-table-column prop="region" label="地区" min-width="120" show-overflow-tooltip />
            <el-table-column label="来源" min-width="130" show-overflow-tooltip>
              <template #default="{ row }">{{ field(row, '来源') }}</template>
            </el-table-column>
            <el-table-column label="共同群聊" width="110">
              <template #default="{ row }">{{ field(row, '共同群聊') }}</template>
            </el-table-column>
            <el-table-column label="个性签名" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">{{ field(row, '个性签名') }}</template>
            </el-table-column>
            <el-table-column label="标签" min-width="220">
              <template #default="{ row }">
                <div class="table-tags">
                  <el-tag v-for="tag in row.tags" :key="tag" size="small">{{ tag }}</el-tag>
                  <span v-if="!row.tags?.length" class="muted">未打标签</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="last_synced_at" label="最后同步" min-width="170" />
            <el-table-column label="操作" fixed="right" width="190">
              <template #default="{ row }">
                <el-button size="small" :icon="CollectionTag" @click="openTagDialog(row)">标签</el-button>
                <el-button size="small" :icon="Refresh" @click="updateFriendDetail(row)">更新详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane name="groups">
          <template #label>
            <span>群聊</span>
            <el-tag size="small" type="warning">{{ groupCount }}</el-tag>
          </template>

          <div class="tab-toolbar">
            <el-form inline>
              <el-form-item label="搜索">
                <el-input v-model="groupKeyword" clearable placeholder="群名称" @keyup.enter="loadGroups" />
              </el-form-item>
              <el-form-item>
                <el-button :icon="Search" @click="loadGroups">查询群聊</el-button>
              </el-form-item>
            </el-form>
            <el-button :icon="Refresh" @click="loadGroups">刷新</el-button>
          </div>

          <el-table
            v-loading="groupsLoading"
            :data="groups"
            height="560"
            highlight-current-row
            empty-text="暂无群聊缓存，请先同步群聊"
            @current-change="selectedGroup = $event"
          >
            <el-table-column prop="name" label="群名称" min-width="260" show-overflow-tooltip />
            <el-table-column prop="member_count" label="人数" width="90" />
            <el-table-column label="标签" min-width="240">
              <template #default="{ row }">
                <div class="table-tags">
                  <el-tag v-for="tag in row.tags" :key="tag" size="small">{{ tag }}</el-tag>
                  <span v-if="!row.tags?.length" class="muted">未打标签</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="last_synced_at" label="最后同步" min-width="170" />
            <el-table-column label="操作" fixed="right" width="270">
              <template #default="{ row }">
                <el-button size="small" :icon="CollectionTag" @click="openTagDialog(row)">标签</el-button>
                <el-button size="small" :icon="Connection" @click="updateGroupMembers(row)">更新成员</el-button>
                <el-button size="small" :icon="View" @click="viewGroupMembers(row)">查看成员</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </section>

    <el-dialog v-model="tagDialogVisible" title="编辑标签" width="520px">
      <el-form label-width="72px">
        <el-form-item label="对象">
          <el-input :model-value="currentContact?.name || ''" disabled />
        </el-form-item>
        <el-form-item label="类型">
          <el-tag :type="currentContact?.type === 'friend' ? 'success' : 'warning'">
            {{ currentContact?.type === 'friend' ? '好友' : '群聊' }}
          </el-tag>
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="tagDraft"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入标签后回车"
            style="width: 100%"
          >
            <el-option v-for="tag in allTags" :key="tag" :label="tag" :value="tag" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="tagDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingTags" @click="saveTags">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="membersDialogVisible" :title="`${membersGroupName} 群成员`" width="760px">
      <el-table v-loading="membersLoading" :data="groupMembers" height="480" empty-text="暂无群成员缓存">
        <el-table-column type="index" width="60" />
        <el-table-column prop="display_name" label="成员名" min-width="220" show-overflow-tooltip />
        <el-table-column prop="name" label="缓存标识" min-width="220" show-overflow-tooltip />
        <el-table-column prop="last_synced_at" label="最后同步" min-width="170" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CollectionTag, Connection, Delete, Refresh, Search, User, UserFilled, View } from '@element-plus/icons-vue'
import { api } from '../api/client'

const emit = defineEmits(['task-created'])
const friends = ref([])
const groups = ref([])
const selectedGroup = ref(null)
const activeContactTab = ref('friends')
const friendKeyword = ref('')
const groupKeyword = ref('')
const friendsLoading = ref(false)
const groupsLoading = ref(false)
const tagDialogVisible = ref(false)
const savingTags = ref(false)
const currentContact = ref(null)
const tagDraft = ref([])
const membersDialogVisible = ref(false)
const membersLoading = ref(false)
const membersGroupName = ref('')
const groupMembers = ref([])

const friendCount = computed(() => friends.value.length)
const groupCount = computed(() => groups.value.length)
const allTags = computed(() => {
  const tags = new Set()
  ;[...friends.value, ...groups.value].forEach((item) => (item.tags || []).forEach((tag) => tags.add(tag)))
  return [...tags].sort()
})

function field(row, key) {
  const value = row.raw?.[key]
  return value && value !== '无' ? value : ''
}

async function loadCache() {
  await Promise.all([loadFriends(), loadGroups()])
}

async function loadFriends() {
  friendsLoading.value = true
  try {
    const query = friendKeyword.value ? `?keyword=${encodeURIComponent(friendKeyword.value)}` : ''
    friends.value = await api.get(`/api/contacts/friends/cache${query}`)
  } finally {
    friendsLoading.value = false
  }
}

async function loadGroups() {
  groupsLoading.value = true
  try {
    const query = groupKeyword.value ? `?keyword=${encodeURIComponent(groupKeyword.value)}` : ''
    groups.value = await api.get(`/api/contacts/groups/cache${query}`)
  } finally {
    groupsLoading.value = false
  }
}

async function syncFriends(detail) {
  await api.get(`/api/contacts/friends?detail=${detail}`)
  ElMessage.success(detail ? '好友详情同步任务已创建' : '好友同步任务已创建')
  emit('task-created')
}

async function syncGroups() {
  await api.get('/api/contacts/groups')
  ElMessage.success('群聊同步任务已创建')
  emit('task-created')
}

async function syncSelectedGroupMembers() {
  if (!selectedGroup.value) return ElMessage.warning('请先选择一个群聊')
  await updateGroupMembers(selectedGroup.value)
}

async function clearFriends() {
  try {
    await ElMessageBox.confirm('确认清空 SQLite 中的好友缓存和好友标签？该操作不会删除微信好友。', '清空好友库', {
      type: 'warning',
      confirmButtonText: '确认清空',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  const result = await api.delete('/api/contacts/friends/cache')
  friends.value = []
  ElMessage.success(`已清空 ${result.deleted} 条好友缓存`)
}

async function clearGroups() {
  try {
    await ElMessageBox.confirm('确认清空 SQLite 中的群聊缓存、群标签和群成员缓存？该操作不会退出微信群。', '清空群聊库', {
      type: 'warning',
      confirmButtonText: '确认清空',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  const result = await api.delete('/api/contacts/groups/cache')
  groups.value = []
  selectedGroup.value = null
  groupMembers.value = []
  ElMessage.success(`已清空 ${result.deleted} 条群聊缓存，${result.members_deleted} 条群成员缓存`)
}

async function updateFriendDetail(row) {
  await api.post(`/api/contacts/friends/${encodeURIComponent(row.name)}/detail`, {})
  ElMessage.success('好友详情更新任务已创建')
  emit('task-created')
}

async function updateGroupMembers(row) {
  await api.get(`/api/contacts/groups/${encodeURIComponent(row.name)}/members`)
  ElMessage.success('群成员更新任务已创建')
  emit('task-created')
}

async function viewGroupMembers(row) {
  membersGroupName.value = row.name
  membersDialogVisible.value = true
  membersLoading.value = true
  try {
    groupMembers.value = await api.get(`/api/contacts/groups/${encodeURIComponent(row.name)}/members/cache`)
  } finally {
    membersLoading.value = false
  }
}

function openTagDialog(row) {
  currentContact.value = row
  tagDraft.value = [...(row.tags || [])]
  tagDialogVisible.value = true
}

async function saveTags() {
  if (!currentContact.value) return
  savingTags.value = true
  try {
    const row = currentContact.value
    const segment = row.type === 'friend' ? 'friends' : 'groups'
    const result = await api.put(`/api/contacts/${segment}/${encodeURIComponent(row.name)}/tags`, {
      tags: tagDraft.value,
    })
    row.tags = result.tags
    ElMessage.success('标签已保存')
    tagDialogVisible.value = false
  } finally {
    savingTags.value = false
  }
}

onMounted(loadCache)
</script>
