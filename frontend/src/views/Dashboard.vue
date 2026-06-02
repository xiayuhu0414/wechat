<template>
  <div class="dashboard-page">
    <section class="panel dashboard-hero">
      <div>
        <span class="muted">本地控制台</span>
        <h2>微信自动化运行概览</h2>
        <p>当前所有微信操作都会进入串行任务队列，适合先检查状态、联系人缓存和最近失败原因。</p>
      </div>
      <div class="dashboard-status">
        <el-tag :type="status.running ? 'success' : 'danger'" size="large">
          {{ status.running ? '微信运行中' : '微信未运行' }}
        </el-tag>
        <el-tag :type="status.available ? 'success' : 'warning'" size="large">
          {{ status.adapter || 'pyweixin' }}
        </el-tag>
        <span>{{ status.version || '版本未检测' }}</span>
      </div>
    </section>

    <div class="dashboard-metrics">
      <section class="panel metric dashboard-metric">
        <span>好友缓存</span>
        <strong>{{ friends.length }}</strong>
        <el-button link type="primary" @click="$emit('open-view', 'contacts')">查看通讯录</el-button>
      </section>
      <section class="panel metric dashboard-metric">
        <span>群聊缓存</span>
        <strong>{{ groups.length }}</strong>
        <el-button link type="primary" @click="$emit('open-view', 'contacts')">查看群聊</el-button>
      </section>
      <section class="panel metric dashboard-metric">
        <span>队列中</span>
        <strong>{{ activeTaskCount }}</strong>
        <el-button link type="primary" @click="$emit('open-tasks')">打开任务中心</el-button>
      </section>
      <section class="panel metric dashboard-metric">
        <span>最近失败</span>
        <strong>{{ failedTaskCount }}</strong>
        <span>{{ failedTaskCount ? '请查看失败原因' : '暂无失败任务' }}</span>
      </section>
    </div>

    <div class="grid two dashboard-main">
      <section class="panel">
        <div class="panel-title">
          <h2>运营统计</h2>
          <el-tag>最近 {{ tasks.length }} 条任务</el-tag>
        </div>
        <div class="stat-grid">
          <div class="stat-cell">
            <span>今日任务</span>
            <strong>{{ todayTaskCount }}</strong>
          </div>
          <div class="stat-cell">
            <span>成功率</span>
            <strong>{{ taskSuccessRate }}%</strong>
          </div>
          <div class="stat-cell">
            <span>消息任务</span>
            <strong>{{ messageTaskCount }}</strong>
          </div>
          <div class="stat-cell">
            <span>附件任务</span>
            <strong>{{ fileTaskCount }}</strong>
          </div>
          <div class="stat-cell">
            <span>好友标签</span>
            <strong>{{ friendTagCount }}</strong>
          </div>
          <div class="stat-cell">
            <span>群聊标签</span>
            <strong>{{ groupTagCount }}</strong>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-title">
          <h2>扩展预览</h2>
          <el-tag type="warning">规划中</el-tag>
        </div>
        <div class="ability-preview">
          <div v-for="item in abilityPreview" :key="item.title" class="ability-item">
            <div>
              <strong>{{ item.title }}</strong>
              <span>{{ item.description }}</span>
            </div>
            <el-tag :type="item.type" size="small">{{ item.status }}</el-tag>
          </div>
        </div>
      </section>
    </div>

    <div class="grid two dashboard-main">
      <section class="panel">
        <div class="panel-title">
          <h2>快速操作</h2>
          <el-button :icon="Refresh" @click="refresh">刷新</el-button>
        </div>
        <div class="quick-actions">
          <el-button type="primary" :icon="ChatDotRound" @click="$emit('open-view', 'messages')">发送消息</el-button>
          <el-button :icon="User" @click="$emit('open-view', 'contacts')">同步好友</el-button>
          <el-button :icon="UserFilled" @click="$emit('open-view', 'contacts')">同步群聊</el-button>
          <el-button :icon="Tickets" @click="$emit('open-tasks')">查看任务</el-button>
        </div>
      </section>

      <section class="panel">
        <div class="panel-title">
          <h2>最近异常</h2>
          <el-tag :type="recentErrors.length ? 'danger' : 'success'">{{ recentErrors.length }}</el-tag>
        </div>
        <div class="error-list">
          <div v-for="task in recentErrors" :key="task.id" class="error-item">
            <strong>{{ task.type }}</strong>
            <span>{{ task.error }}</span>
          </div>
          <span v-if="!recentErrors.length" class="muted">最近任务没有错误。</span>
        </div>
      </section>
    </div>

    <section class="panel">
      <div class="panel-title">
        <h2>最近任务</h2>
        <el-button :icon="Tickets" @click="$emit('open-tasks')">打开任务中心</el-button>
      </div>
      <el-table :data="tasks" height="320" empty-text="暂无任务">
        <el-table-column prop="type" label="类型" min-width="150" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }"><el-tag :type="tagType(row.status)">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="170" />
        <el-table-column prop="error" label="错误" min-width="260" show-overflow-tooltip />
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Refresh, Tickets, User, UserFilled } from '@element-plus/icons-vue'
import { api } from '../api/client'

defineEmits(['open-tasks', 'open-view'])

const status = ref({})
const tasks = ref([])
const friends = ref([])
const groups = ref([])

const activeTaskCount = computed(() => tasks.value.filter((task) => ['pending', 'running'].includes(task.status)).length)
const failedTaskCount = computed(() => tasks.value.filter((task) => task.status === 'failed').length)
const recentErrors = computed(() => tasks.value.filter((task) => task.error).slice(0, 4))
const todayTaskCount = computed(() => {
  const now = new Date()
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  return tasks.value.filter((task) => String(task.created_at || '').slice(0, 10) === today).length
})
const completedTasks = computed(() => tasks.value.filter((task) => ['success', 'failed', 'cancelled'].includes(task.status)))
const taskSuccessRate = computed(() => {
  if (!completedTasks.value.length) return 0
  const successCount = completedTasks.value.filter((task) => task.status === 'success').length
  return Math.round((successCount / completedTasks.value.length) * 100)
})
const messageTaskCount = computed(() => tasks.value.filter((task) => task.type === 'message.send').length)
const fileTaskCount = computed(() => tasks.value.filter((task) => task.type === 'file.send').length)
const friendTagCount = computed(() => new Set(friends.value.flatMap((friend) => friend.tags || [])).size)
const groupTagCount = computed(() => new Set(groups.value.flatMap((group) => group.tags || [])).size)
const abilityPreview = computed(() => [
  {
    title: '客户资源',
    description: `可扩展为客户分层、表格导入、号码添加和跟进记录；当前已缓存 ${friends.value.length} 个好友。`,
    status: '开发中',
    type: 'warning',
  },
  {
    title: '自动应答',
    description: '后续统计规则命中、应答次数、人工接管和异常会话。',
    status: '规划统计',
    type: 'info',
  },
  {
    title: '群管理',
    description: `后续统计群成员增长、活跃群和群标签；当前已缓存 ${groups.value.length} 个群聊。`,
    status: '开发中',
    type: 'warning',
  },
  {
    title: '朋友圈',
    description: '后续统计发布次数、素材数量、导出记录和互动数据。',
    status: '规划统计',
    type: 'info',
  },
])

function tagType(status) {
  return { success: 'success', failed: 'danger', running: 'warning', cancelled: 'info' }[status] || ''
}

async function refresh() {
  try {
    const [wechatStatus, taskRows, friendRows, groupRows] = await Promise.all([
      api.get('/api/wechat/status'),
      api.get('/api/tasks?limit=100'),
      api.get('/api/contacts/friends/cache'),
      api.get('/api/contacts/groups/cache'),
    ])
    status.value = wechatStatus
    tasks.value = taskRows
    friends.value = friendRows
    groups.value = groupRows
  } catch (error) {
    ElMessage.error(error.message)
  }
}

defineExpose({ refresh })
onMounted(refresh)
</script>
