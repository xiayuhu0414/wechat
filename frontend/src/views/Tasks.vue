<template>
  <div class="task-center">
    <section class="panel task-overview">
      <div class="panel-title">
        <div>
          <h2>任务审计</h2>
          <span class="muted">所有微信自动化操作均记录在 SQLite，可按类型、状态和时间追溯。</span>
        </div>
        <div class="table-actions">
          <el-tag :type="summary.active ? 'warning' : 'success'">队列中 {{ summary.active || 0 }}</el-tag>
          <el-button :icon="Refresh" @click="refresh">刷新</el-button>
        </div>
      </div>

      <div class="task-stat-strip">
        <div class="task-stat-card">
          <span>任务总数</span>
          <strong>{{ summary.total || 0 }}</strong>
        </div>
        <div class="task-stat-card">
          <span>成功率</span>
          <strong>{{ summary.success_rate || 0 }}%</strong>
        </div>
        <div class="task-stat-card">
          <span>成功</span>
          <strong>{{ summary.success || 0 }}</strong>
        </div>
        <div class="task-stat-card">
          <span>失败</span>
          <strong>{{ summary.failed || 0 }}</strong>
        </div>
        <div class="task-stat-card">
          <span>平均耗时</span>
          <strong>{{ formatDuration(summary.avg_duration_seconds) }}</strong>
        </div>
      </div>
    </section>

    <div class="grid two task-analytics">
      <section class="panel">
        <div class="panel-title">
          <h2>分类统计</h2>
          <el-tag>按能力域</el-tag>
        </div>
        <el-table :data="stats.categories || []" height="300" empty-text="暂无分类统计">
          <el-table-column prop="label" label="分类" min-width="130" />
          <el-table-column prop="total" label="总数" width="76" />
          <el-table-column prop="active" label="队列" width="76" />
          <el-table-column prop="success" label="成功" width="76" />
          <el-table-column prop="failed" label="失败" width="76" />
          <el-table-column prop="success_rate" label="成功率" width="92">
            <template #default="{ row }">{{ row.success_rate }}%</template>
          </el-table-column>
        </el-table>
      </section>

      <section class="panel">
        <div class="panel-title">
          <h2>类型分布</h2>
          <el-tag>按任务类型</el-tag>
        </div>
        <el-table :data="stats.types || []" height="300" empty-text="暂无类型统计">
          <el-table-column prop="label" label="任务" min-width="150" show-overflow-tooltip />
          <el-table-column prop="category_label" label="分类" min-width="110" show-overflow-tooltip />
          <el-table-column prop="total" label="总数" width="76" />
          <el-table-column prop="success" label="成功" width="76" />
          <el-table-column prop="failed" label="失败" width="76" />
        </el-table>
      </section>
    </div>

    <div class="task-workspace">
      <section class="panel task-list-panel">
        <div class="panel-title">
          <h2>任务列表</h2>
          <el-tag>{{ filteredTasks.length }} 条</el-tag>
        </div>
        <div class="task-filters">
          <el-input v-model="filters.keyword" clearable placeholder="搜索类型、ID、错误、参数" />
          <el-select v-model="filters.status" clearable placeholder="状态">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-select v-model="filters.category" clearable placeholder="分类">
            <el-option v-for="item in categoryOptions" :key="item.key" :label="item.label" :value="item.key" />
          </el-select>
        </div>

        <el-table :data="filteredTasks" height="560" highlight-current-row empty-text="暂无任务" @current-change="selectTask">
          <el-table-column label="任务" min-width="210" show-overflow-tooltip>
            <template #default="{ row }">
              <div class="task-name-cell">
                <strong>{{ taskLabel(row.type) }}</strong>
                <span>{{ row.type }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="110">
            <template #default="{ row }"><el-tag :type="tagType(row.status)">{{ statusLabel(row.status) }}</el-tag></template>
          </el-table-column>
          <el-table-column label="分类" width="110">
            <template #default="{ row }">{{ categoryLabel(row.type) }}</template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" min-width="170" />
          <el-table-column width="84" fixed="right">
            <template #default="{ row }">
              <el-button link type="danger" :disabled="row.status !== 'pending'" @click.stop="cancel(row)">取消</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section class="panel task-detail-panel">
        <div class="panel-title">
          <h2>追溯详情</h2>
          <el-tag v-if="selected" :type="tagType(selected.status)">{{ selected.id.slice(0, 8) }}</el-tag>
        </div>

        <template v-if="selected">
          <div class="trace-meta">
            <div><span>任务 ID</span><strong>{{ selected.id }}</strong></div>
            <div><span>任务类型</span><strong>{{ taskLabel(selected.type) }}</strong></div>
            <div><span>创建时间</span><strong>{{ selected.created_at || '-' }}</strong></div>
            <div><span>开始时间</span><strong>{{ selected.started_at || '-' }}</strong></div>
            <div><span>完成时间</span><strong>{{ selected.finished_at || '-' }}</strong></div>
            <div><span>执行耗时</span><strong>{{ selectedDuration }}</strong></div>
          </div>

          <el-tabs v-model="detailTab" class="trace-tabs">
            <el-tab-pane label="参数" name="payload">
              <pre class="pre">{{ JSON.stringify(selected.payload, null, 2) }}</pre>
            </el-tab-pane>
            <el-tab-pane label="结果" name="result">
              <pre class="pre">{{ JSON.stringify(selected.result, null, 2) }}</pre>
            </el-tab-pane>
            <el-tab-pane label="错误" name="error">
              <el-alert v-if="selected.error" :title="selected.error" type="error" :closable="false" show-icon />
              <el-empty v-else description="该任务没有错误" />
            </el-tab-pane>
            <el-tab-pane label="日志" name="logs">
              <div class="log-list trace-log-list">
                <div v-for="(log, index) in selected.logs || []" :key="index" class="log-line">
                  <span>{{ log.created_at }}</span>
                  <el-tag size="small" :type="log.level === 'error' ? 'danger' : log.level === 'warning' ? 'warning' : 'info'">{{ log.level }}</el-tag>
                  <span>{{ log.message }}</span>
                </div>
                <el-empty v-if="!selected.logs?.length" description="暂无日志" />
              </div>
            </el-tab-pane>
          </el-tabs>
        </template>
        <el-empty v-else description="选择左侧任务查看追溯详情" />
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { api, taskSocketUrl } from '../api/client'

const tasks = ref([])
const stats = ref({ summary: {}, categories: [], types: [], daily: [] })
const selected = ref(null)
const detailTab = ref('payload')
const filters = reactive({ keyword: '', status: '', category: '' })
let socket

const statusOptions = [
  { value: 'pending', label: '待执行' },
  { value: 'running', label: '执行中' },
  { value: 'success', label: '成功' },
  { value: 'failed', label: '失败' },
  { value: 'cancelled', label: '已取消' },
]

const typeLabels = {
  'message.send': '发送消息',
  'file.send': '发送附件',
  'contacts.friends': '同步好友',
  'contacts.friend_detail': '同步好友详情',
  'contacts.groups': '同步群聊',
  'contacts.group_members': '同步群成员',
  'autoreply.start': '启动自动应答',
  'autoreply.stop': '停止自动应答',
  'moments.export': '朋友圈历史任务',
  'moments.post': '发布朋友圈',
  'settings.wechat': '更新微信设置',
}

const categoryNames = {
  message: '消息发送',
  file: '附件发送',
  contacts: '通讯录',
  autoreply: '自动应答',
  moments: '朋友圈',
  settings: '系统配置',
  other: '其他任务',
}

const summary = computed(() => stats.value.summary || {})
const categoryOptions = computed(() => stats.value.categories || [])
const filteredTasks = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  return tasks.value.filter((task) => {
    if (filters.status && task.status !== filters.status) return false
    if (filters.category && categoryKey(task.type) !== filters.category) return false
    if (!keyword) return true
    const text = [
      task.id,
      task.type,
      task.status,
      task.error,
      JSON.stringify(task.payload || {}),
      JSON.stringify(task.result || {}),
    ].join(' ').toLowerCase()
    return text.includes(keyword)
  })
})
const selectedDuration = computed(() => {
  if (!selected.value?.started_at || !selected.value?.finished_at) return '-'
  return formatDuration(secondsBetween(selected.value.started_at, selected.value.finished_at))
})

function tagType(status) {
  return { success: 'success', failed: 'danger', running: 'warning', cancelled: 'info', pending: '' }[status] || ''
}

function statusLabel(status) {
  return statusOptions.find((item) => item.value === status)?.label || status
}

function taskLabel(type) {
  return typeLabels[type] || type
}

function categoryKey(type) {
  if (type.startsWith('message.')) return 'message'
  if (type.startsWith('file.')) return 'file'
  if (type.startsWith('contacts.')) return 'contacts'
  if (type.startsWith('autoreply.')) return 'autoreply'
  if (type.startsWith('moments.')) return 'moments'
  if (type.startsWith('settings.')) return 'settings'
  return 'other'
}

function categoryLabel(type) {
  return categoryNames[categoryKey(type)] || '其他任务'
}

function formatDuration(value) {
  const seconds = Number(value || 0)
  if (!seconds) return '0s'
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)}s`
  const minutes = Math.floor(seconds / 60)
  const rest = Math.round(seconds % 60)
  return `${minutes}m ${rest}s`
}

function secondsBetween(startedAt, finishedAt) {
  const start = new Date(startedAt).getTime()
  const finish = new Date(finishedAt).getTime()
  if (Number.isNaN(start) || Number.isNaN(finish)) return 0
  return Math.max((finish - start) / 1000, 0)
}

async function refresh() {
  const [taskRows, statRows] = await Promise.all([
    api.get('/api/tasks?limit=500'),
    api.get('/api/tasks/stats'),
  ])
  tasks.value = taskRows
  stats.value = statRows
  if (selected.value) {
    selected.value = await api.get(`/api/tasks/${selected.value.id}`)
  }
}

async function selectTask(task) {
  if (!task) return
  selected.value = await api.get(`/api/tasks/${task.id}`)
}

async function cancel(task) {
  await api.post(`/api/tasks/${task.id}/cancel`, {})
  ElMessage.success('已提交取消请求')
  await refresh()
}

function connectSocket() {
  socket = new WebSocket(taskSocketUrl())
  socket.onmessage = async (message) => {
    const event = JSON.parse(message.data)
    if (event.event === 'task.updated') await refresh()
    if (event.task_id && selected.value?.id === event.task_id) {
      selected.value = await api.get(`/api/tasks/${event.task_id}`)
    }
  }
}

defineExpose({ refresh })
onMounted(() => {
  refresh()
  connectSocket()
})
onUnmounted(() => socket?.close())
</script>
