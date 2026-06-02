<template>
  <el-container class="shell">
    <el-aside class="sidebar" :class="{ 'is-collapsed': sidebarCollapsed }" :style="{ '--sidebar-width': sidebarWidth }" :width="sidebarWidth">
      <div class="brand">
        <div class="brand-mark">aW</div>
        <div>
          <strong>autoWechat</strong>
          <span>Local Console</span>
        </div>
        <el-tooltip :content="sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'" placement="right">
          <el-button
            class="sidebar-toggle"
            circle
            text
            :icon="sidebarCollapsed ? Expand : Fold"
            @click="toggleSidebar"
          />
        </el-tooltip>
      </div>

      <el-menu :default-active="active" class="nav" :collapse="sidebarCollapsed" @select="active = $event">
        <el-menu-item v-for="item in navItems" :key="item.key" :index="item.key">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container class="main-pane">
      <el-header class="topbar">
        <div class="title-block">
          <h1>{{ currentTitle }}</h1>
          <p>{{ currentSubtitle }}</p>
        </div>
        <div class="top-actions">
          <el-input v-model="token" placeholder="启动 Token" clearable @change="saveToken">
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
          <el-button :icon="Refresh" @click="refreshAll">刷新</el-button>
        </div>
      </el-header>

      <el-main class="content">
        <Dashboard v-if="active === 'dashboard'" ref="dashboardRef" @open-tasks="active = 'tasks'" @open-view="active = $event" />
        <Messages v-if="active === 'messages'" @task-created="handleTaskCreated" />
        <CustomerResources v-if="active === 'files'" @task-created="handleTaskCreated" />
        <Development
          v-if="active === 'autoreply'"
          title="自动应答"
          description="关键词应答、监听策略和规则编排正在开发中，后续会在这里开放。"
        />
        <Contacts v-if="active === 'contacts'" @task-created="handleTaskCreated" />
        <Development
          v-if="active === 'groups'"
          title="群管理"
          description="群管理能力入口已保留，群设置、邀请、移除等操作后续逐步开放。"
        />
        <Moments v-if="active === 'moments'" @task-created="handleTaskCreated" />
        <Settings v-if="active === 'settings'" />
        <Tasks v-if="active === 'tasks'" ref="tasksRef" />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ChatDotRound, Collection, Connection, Expand, Files as FilesIcon, Fold, House, Lock, Refresh, Setting, Tickets, User, UserFilled } from '@element-plus/icons-vue'
import Dashboard from './views/Dashboard.vue'
import Messages from './views/Messages.vue'
import Contacts from './views/Contacts.vue'
import CustomerResources from './views/CustomerResources.vue'
import Development from './views/Development.vue'
import Moments from './views/Moments.vue'
import Settings from './views/Settings.vue'
import Tasks from './views/Tasks.vue'

const active = ref('dashboard')
const token = ref(localStorage.getItem('autowechat_token') || '')
const dashboardRef = ref(null)
const tasksRef = ref(null)
const sidebarCollapsed = ref(localStorage.getItem('autowechat_sidebar_collapsed') === '1')
const sidebarWidth = computed(() => (sidebarCollapsed.value ? '68px' : '216px'))

const navItems = [
  { key: 'dashboard', label: '仪表盘', icon: House, subtitle: '状态、队列和最近错误' },
  { key: 'messages', label: '消息控制台', icon: ChatDotRound, subtitle: '文本消息、群发和 @ 成员' },
  { key: 'files', label: '客户资源', icon: FilesIcon, subtitle: '客户资料、导入和资源管理' },
  { key: 'autoreply', label: '自动应答', icon: Connection, subtitle: '关键词规则和监听任务' },
  { key: 'contacts', label: '通讯录', icon: User, subtitle: '好友、群聊和群成员快照' },
  { key: 'groups', label: '群管理', icon: UserFilled, subtitle: '群能力入口和任务化执行' },
  { key: 'moments', label: '朋友圈', icon: Collection, subtitle: '发布朋友圈和 AI 文案' },
  { key: 'tasks', label: '任务中心', icon: Tickets, subtitle: '队列状态、日志和失败原因' },
  { key: 'settings', label: '系统配置', icon: Setting, subtitle: '微信适配和全局参数' },
]

const current = computed(() => navItems.find((item) => item.key === active.value) || navItems[0])
const currentTitle = computed(() => current.value.label)
const currentSubtitle = computed(() => current.value.subtitle)

function saveToken() {
  if (token.value) localStorage.setItem('autowechat_token', token.value)
  else localStorage.removeItem('autowechat_token')
}

function refreshAll() {
  dashboardRef.value?.refresh?.()
  tasksRef.value?.refresh?.()
}

function handleTaskCreated() {
  dashboardRef.value?.refresh?.()
  tasksRef.value?.refresh?.()
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem('autowechat_sidebar_collapsed', sidebarCollapsed.value ? '1' : '0')
}
</script>
