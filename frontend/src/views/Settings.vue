<template>
  <div class="settings-page">
    <section class="panel">
      <div class="panel-title">
        <h2>微信全局配置</h2>
        <el-button :icon="Refresh" @click="loadWechat">读取</el-button>
      </div>
      <el-form label-width="120px" :model="wechatForm">
        <div class="grid two">
          <el-form-item label="主窗口最大化"><el-switch v-model="wechatForm.is_maximize" /></el-form-item>
          <el-form-item label="任务后关闭微信"><el-switch v-model="wechatForm.close_weixin" /></el-form-item>
          <el-form-item label="搜索页数"><el-input-number v-model="wechatForm.search_pages" :min="0" /></el-form-item>
          <el-form-item label="发送间隔"><el-input-number v-model="wechatForm.send_delay" :min="0" :step="0.1" /></el-form-item>
          <el-form-item label="加载等待"><el-input-number v-model="wechatForm.load_delay" :min="0" :step="0.5" /></el-form-item>
        </div>
        <div class="form-actions"><el-button type="primary" @click="saveWechat">保存微信配置</el-button></div>
      </el-form>
    </section>

    <section class="panel">
      <div class="panel-title">
        <div>
          <h2>微信 UI 树增强</h2>
          <span class="muted">常驻 UIA 客户端用于唤醒和诊断微信隐藏控件树</span>
        </div>
        <el-tag :type="uiaStatus.running ? 'success' : 'info'">{{ uiaStatus.running ? '运行中' : '未运行' }}</el-tag>
      </div>
      <el-form label-width="120px" :model="uiaForm">
        <div class="grid two">
          <el-form-item label="自动启用"><el-switch v-model="uiaForm.enabled" /></el-form-item>
          <el-form-item label="原生监听"><el-switch v-model="uiaForm.use_dotnet_watcher" /></el-form-item>
          <el-form-item label="探测间隔"><el-input-number v-model="uiaForm.interval_seconds" :min="2" :max="300" /></el-form-item>
          <el-form-item label="节点上限"><el-input-number v-model="uiaForm.max_nodes" :min="50" :max="5000" /></el-form-item>
          <el-form-item label="保存截图"><el-switch v-model="uiaForm.save_screenshot_on_probe" /></el-form-item>
        </div>
        <div class="form-actions">
          <el-button @click="startUia">启动</el-button>
          <el-button @click="stopUia">停止</el-button>
          <el-button :loading="uiaLoading" :icon="View" @click="probeUia">探测 UI 树</el-button>
          <el-button :loading="uiaLoading" :icon="View" @click="probeAlternativeUia">扫描 HWND 树</el-button>
          <el-button :loading="compatLoading" :icon="Refresh" @click="restartWeChatCompat">兼容模式重启微信</el-button>
          <el-button type="primary" @click="saveUia">保存增强配置</el-button>
        </div>
      </el-form>

      <div class="uia-summary">
        <div>
          <span>节点数量</span>
          <strong>{{ uiaStatus.last_probe?.effective_node_count ?? uiaStatus.last_probe?.node_count ?? '-' }}</strong>
        </div>
        <div>
          <span>树状态</span>
          <strong>{{ uiaStatus.last_probe?.effective_tree_state || uiaStatus.last_probe?.tree_state || '-' }}</strong>
        </div>
        <div>
          <span>微信窗口</span>
          <strong>{{ uiaStatus.last_probe?.window?.title || '-' }}</strong>
        </div>
        <div>
          <span>耗时</span>
          <strong>{{ uiaStatus.last_probe?.duration_seconds ?? '-' }}s</strong>
        </div>
        <div>
          <span>原生监听</span>
          <strong>{{ uiaStatus.watcher_process_id ? `PID ${uiaStatus.watcher_process_id}` : '-' }}</strong>
        </div>
      </div>
      <pre v-if="uiaStatus.last_error || uiaStatus.last_probe" class="pre uia-pre">{{ uiaText }}</pre>
    </section>

    <section class="panel">
      <div class="panel-title">
        <h2>AI 模型配置</h2>
        <el-tag :type="aiKeySet ? 'success' : 'warning'">{{ aiKeySet ? 'Key 已配置' : 'Key 未配置' }}</el-tag>
      </div>
      <el-form label-width="120px" :model="aiForm">
        <div class="grid two">
          <el-form-item label="接口地址">
            <el-input v-model="aiForm.base_url" placeholder="https://api.deepseek.com" />
          </el-form-item>
          <el-form-item label="模型名称">
            <el-input v-model="aiForm.model" placeholder="deepseek-v4-flash" />
          </el-form-item>
          <el-form-item label="API Key">
            <el-input
              v-model="aiForm.api_key"
              type="password"
              show-password
              clearable
              placeholder="留空则不修改已有 Key"
            />
          </el-form-item>
          <el-form-item label="温度">
            <el-input-number v-model="aiForm.temperature" :min="0" :max="2" :step="0.1" />
          </el-form-item>
          <el-form-item label="最大 Token">
            <el-input-number v-model="aiForm.max_tokens" :min="1" :max="8192" />
          </el-form-item>
          <el-form-item label="超时秒数">
            <el-input-number v-model="aiForm.timeout_seconds" :min="1" :max="300" />
          </el-form-item>
        </div>
        <el-form-item label="系统提示词">
          <el-input v-model="aiForm.system_prompt" type="textarea" :rows="4" />
        </el-form-item>
        <div class="form-actions">
          <el-button :icon="Refresh" @click="loadAi">读取</el-button>
          <el-button type="primary" @click="saveAi">保存 AI 配置</el-button>
        </div>
      </el-form>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, View } from '@element-plus/icons-vue'
import { api } from '../api/client'

const aiKeySet = ref(false)
const uiaLoading = ref(false)
const compatLoading = ref(false)
const uiaStatus = ref({})

const wechatForm = reactive({
  is_maximize: false,
  close_weixin: false,
  search_pages: 5,
  send_delay: 0.2,
  load_delay: 3.5,
})

const uiaForm = reactive({
  enabled: false,
  interval_seconds: 8,
  max_nodes: 800,
  save_screenshot_on_probe: true,
  use_dotnet_watcher: true,
})

const aiForm = reactive({
  base_url: 'https://api.deepseek.com',
  api_key: '',
  model: 'deepseek-v4-flash',
  temperature: 0.7,
  max_tokens: 600,
  timeout_seconds: 60,
  system_prompt: '',
})

const uiaText = computed(() => JSON.stringify({
  error: uiaStatus.value.last_error,
  probe: uiaStatus.value.last_probe,
  alternative: uiaStatus.value.alternative_probe,
  watcher: uiaStatus.value.watcher_state,
}, null, 2))

async function loadWechat() {
  const data = await api.get('/api/settings/wechat')
  Object.assign(wechatForm, data)
}

async function saveWechat() {
  const data = await api.post('/api/settings/wechat', wechatForm)
  Object.assign(wechatForm, data)
  ElMessage.success('微信配置已保存')
}

async function loadUia() {
  const data = await api.get('/api/settings/uia')
  uiaStatus.value = data
  Object.assign(uiaForm, data.config || {})
}

async function saveUia() {
  const data = await api.post('/api/settings/uia', uiaForm)
  uiaStatus.value = data
  Object.assign(uiaForm, data.config || {})
  ElMessage.success('UI 树增强配置已保存')
}

async function startUia() {
  uiaStatus.value = await api.post('/api/wechat/uia/start', {})
  ElMessage.success('UIA 增强已启动')
}

async function stopUia() {
  uiaStatus.value = await api.post('/api/wechat/uia/stop', {})
  ElMessage.success('UIA 增强已停止')
}

async function probeUia() {
  uiaLoading.value = true
  try {
    const result = await api.post('/api/wechat/uia/probe', {})
    uiaStatus.value = { ...uiaStatus.value, last_probe: result, last_error: result.ok ? null : result.error }
    const count = result.node_count ?? 0
    ElMessage.success(`UI 树探测完成，节点 ${count}`)
  } finally {
    uiaLoading.value = false
  }
}

async function probeAlternativeUia() {
  uiaLoading.value = true
  try {
    const result = await api.post('/api/wechat/uia/probe-alternative', {})
    uiaStatus.value = { ...uiaStatus.value, alternative_probe: result, last_error: result.ok ? null : result.error }
    const count = result.best_main_item?.node_count ?? result.best_item?.node_count ?? 0
    ElMessage.success(`HWND 树扫描完成，最佳节点 ${count}`)
  } finally {
    uiaLoading.value = false
  }
}

async function restartWeChatCompat() {
  await ElMessageBox.confirm(
    '将关闭当前微信进程，并用软件渲染兼容模式重新启动。未发送的聊天输入可能会丢失。',
    '兼容模式重启微信',
    { type: 'warning', confirmButtonText: '重启微信', cancelButtonText: '取消' },
  )
  compatLoading.value = true
  try {
    const data = await api.post('/api/wechat/uia/launch-compat', {
      restart: true,
      wait_seconds: 3,
      probe_timeout_seconds: 30,
      probe_interval_seconds: 2,
    })
    if (!data.ok) {
      ElMessage.error(data.error || '兼容模式启动失败')
      return
    }
    uiaStatus.value = {
      ...(data.uia || uiaStatus.value),
      last_probe: data.probe?.best_main_probe || data.probe?.best_probe || data.uia?.last_probe || uiaStatus.value.last_probe,
    }
    ElMessage.success('微信已用兼容模式启动，登录后可重新探测 UI 树')
  } finally {
    compatLoading.value = false
  }
}

async function loadAi() {
  const data = await api.get('/api/settings/ai')
  aiKeySet.value = Boolean(data.api_key_set)
  Object.assign(aiForm, data, { api_key: '' })
}

async function saveAi() {
  const payload = { ...aiForm }
  if (!payload.api_key) delete payload.api_key
  const data = await api.post('/api/settings/ai', payload)
  aiKeySet.value = Boolean(data.api_key_set)
  Object.assign(aiForm, data, { api_key: '' })
  ElMessage.success('AI 配置已保存')
}

onMounted(() => {
  loadWechat()
  loadUia()
  loadAi()
})
</script>
