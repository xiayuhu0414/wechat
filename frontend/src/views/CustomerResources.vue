<template>
  <div class="customer-resources customer-resources-single">
    <section v-if="viewMode === 'table'" class="panel customers-panel">
      <div class="panel-title">
        <h2>客户表</h2>
        <div class="table-actions">
          <el-upload :show-file-list="false" :http-request="uploadExcel" accept=".xlsx,.xlsm,.csv,.tsv">
            <el-button type="primary" :icon="Upload">上传 Excel</el-button>
          </el-upload>
          <el-button :icon="Refresh" @click="reloadCustomersFromFirstPage">刷新</el-button>
          <el-button :icon="EditPen" :disabled="!selectedCustomers.length" @click="openGreetingsDialog('selected')">
            设置招呼语
          </el-button>
          <el-button type="primary" :icon="UserFilled" :disabled="!selectedCustomers.length" @click="batchAddSelected">
            添加选中
          </el-button>
          <el-button type="success" :icon="Connection" @click="batchAddFiltered">添加当前筛选</el-button>
        </div>
      </div>

      <div class="tab-toolbar">
        <el-form inline>
          <el-form-item label="搜索">
            <el-input v-model="filters.keyword" clearable placeholder="号码 / 备注 / 原始信息" @keyup.enter="reloadCustomersFromFirstPage" />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="filters.add_status" clearable placeholder="全部" style="width: 140px">
              <el-option label="待添加" value="pending" />
              <el-option label="添加中" value="adding" />
              <el-option label="已添加" value="added" />
              <el-option label="失败" value="failed" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button :icon="Search" @click="reloadCustomersFromFirstPage">查询</el-button>
          </el-form-item>
        </el-form>
        <div class="table-actions">
          <el-button :icon="EditPen" @click="openGreetingsDialog('filtered')">批量设置当前筛选招呼语</el-button>
          <el-switch v-model="addOptions.chat_only" active-text="仅聊天" />
        </div>
      </div>

      <el-table
        v-loading="customersLoading"
        :data="customers"
        height="560"
        row-key="id"
        empty-text="暂无客户，请点击上传 Excel 导入"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="46" />
        <el-table-column prop="number" label="号码" min-width="150" show-overflow-tooltip />
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column prop="greetings" label="招呼语" min-width="260" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.add_status)" size="small">{{ statusText(row.add_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source_filename" label="来源文件" min-width="180" show-overflow-tooltip />
        <el-table-column prop="source_row" label="源行" width="80" />
        <el-table-column prop="updated_at" label="更新时间" min-width="170" />
        <el-table-column label="操作" fixed="right" width="170">
          <template #default="{ row }">
            <el-button link type="primary" :icon="EditPen" @click="openEdit(row)">编辑</el-button>
            <el-button link type="primary" :icon="View" @click="openRaw(row)">原始信息</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="table-pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[20, 50, 100, 200]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handlePageSizeChange"
          @current-change="loadCustomers"
        />
      </div>
    </section>

    <section v-else class="panel import-panel import-panel-wide">
      <div class="panel-title">
        <h2>数据预览与列映射</h2>
        <div class="table-actions">
          <el-upload :show-file-list="false" :http-request="uploadExcel" accept=".xlsx,.xlsm,.csv,.tsv">
            <el-button :icon="Upload">重新上传</el-button>
          </el-upload>
          <el-button :icon="Back" @click="backToTable">返回客户表</el-button>
        </div>
      </div>

      <template v-if="preview">
        <div class="import-summary">
          <div>
            <span>文件</span>
            <strong>{{ preview.filename }}</strong>
          </div>
          <div>
            <span>可导入行数</span>
            <strong>{{ preview.row_count }}</strong>
          </div>
          <div>
            <span>表头行</span>
            <strong>{{ preview.header_row }}</strong>
          </div>
        </div>

        <div class="mapping-board">
          <div v-if="preview.sheets?.length > 1" class="sheet-row">
            <span>工作表</span>
            <el-select v-model="sheetName" filterable @change="reloadPreview">
              <el-option v-for="sheet in preview.sheets" :key="sheet" :label="sheet" :value="sheet" />
            </el-select>
          </div>

          <div class="mapping-row mapping-head">
            <span>目标字段</span>
            <span>来源列</span>
            <span>样例</span>
          </div>
          <div v-for="field in mappingFields" :key="field.key" class="mapping-row">
            <div class="field-name">
              <strong>{{ field.label }}</strong>
              <span>{{ field.required ? '必填' : '可选' }}</span>
            </div>
            <el-select v-model="mapping[field.key]" clearable filterable :placeholder="field.placeholder">
              <el-option v-for="column in preview.headers" :key="column.key" :label="column.label" :value="column.key" />
            </el-select>
            <div class="sample-value">{{ sampleFor(mapping[field.key]) || '-' }}</div>
          </div>

          <div class="mapping-actions">
            <el-button :icon="Refresh" @click="reloadPreview">重新解析</el-button>
            <el-button type="primary" :loading="importing" :icon="Finished" @click="commitImport">导入客户表</el-button>
          </div>
        </div>

        <el-table :data="preview.rows" height="430" class="preview-table" empty-text="没有可预览的数据">
          <el-table-column type="index" width="58" />
          <el-table-column
            v-for="column in preview.headers.slice(0, 12)"
            :key="column.key"
            :prop="column.key"
            :label="column.label"
            min-width="140"
            show-overflow-tooltip
          />
        </el-table>
      </template>
    </section>

    <el-dialog v-model="greetingsDialogVisible" title="批量设置招呼语" width="560px">
      <el-form label-width="92px">
        <el-form-item label="作用范围">
          <el-tag>{{ greetingsScope === 'selected' ? `已选 ${selectedCustomers.length} 位客户` : '当前筛选结果' }}</el-tag>
        </el-form-item>
        <el-form-item label="招呼语">
          <el-input
            v-model="greetingsDraft"
            type="textarea"
            :rows="4"
            placeholder="例如：你好，我是通过资料联系到你的，方便加个微信沟通吗？"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="greetingsDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingGreetings" @click="saveGreetings">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editVisible" title="编辑客户" width="620px">
      <el-form label-width="84px">
        <el-form-item label="号码">
          <el-input v-model="editForm.number" placeholder="手机号或微信号" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.remark" placeholder="客户备注" />
        </el-form-item>
        <el-form-item label="招呼语">
          <el-input v-model="editForm.greetings" type="textarea" :rows="4" placeholder="添加好友时发送的验证语" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.add_status">
            <el-option label="待添加" value="pending" />
            <el-option label="添加中" value="adding" />
            <el-option label="已添加" value="added" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingCustomer" @click="saveCustomer">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="rawVisible" title="原始表格信息" width="720px">
      <pre class="pre">{{ JSON.stringify(currentRaw, null, 2) }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Back, Connection, EditPen, Finished, Refresh, Search, Upload, UserFilled, View } from '@element-plus/icons-vue'
import { api } from '../api/client'

const emit = defineEmits(['task-created'])
const viewMode = ref('table')
const preview = ref(null)
const sheetName = ref('')
const mapping = reactive({ number: '', greetings: '', remark: '' })
const importing = ref(false)
const customers = ref([])
const selectedCustomers = ref([])
const customersLoading = ref(false)
const rawVisible = ref(false)
const currentRaw = ref({})
const filters = reactive({ keyword: '', add_status: '' })
const pagination = reactive({ page: 1, page_size: 50, total: 0 })
const addOptions = reactive({ chat_only: false })
const greetingsDialogVisible = ref(false)
const greetingsScope = ref('selected')
const greetingsDraft = ref('')
const savingGreetings = ref(false)
const editVisible = ref(false)
const savingCustomer = ref(false)
const editingCustomerId = ref('')
const editForm = reactive({ number: '', remark: '', greetings: '', add_status: 'pending' })
const mappingFields = [
  { key: 'number', label: 'number', required: true, placeholder: '手机号 / 微信号列' },
  { key: 'greetings', label: 'greetings', required: false, placeholder: '招呼语列' },
  { key: 'remark', label: 'remark', required: false, placeholder: '备注列' },
]

async function uploadExcel(options) {
  const data = new FormData()
  data.append('file', options.file)
  preview.value = await api.upload('/api/customers/imports/preview', data)
  sheetName.value = preview.value.sheet_name || ''
  viewMode.value = 'import'
  applySuggestedMapping()
  ElMessage.success('文件已解析，请确认字段映射')
}

async function reloadPreview() {
  if (!preview.value?.path) return
  const query = new URLSearchParams({ path: preview.value.path })
  if (sheetName.value) query.set('sheet_name', sheetName.value)
  preview.value = await api.get(`/api/customers/imports/preview?${query.toString()}`)
  sheetName.value = preview.value.sheet_name || sheetName.value
  applySuggestedMapping(false)
}

function applySuggestedMapping(overwrite = true) {
  const suggested = preview.value?.suggested_mapping || {}
  if (overwrite || !mapping.number) mapping.number = suggested.number || ''
  if (overwrite || !mapping.greetings) mapping.greetings = suggested.greetings || ''
  if (overwrite || !mapping.remark) mapping.remark = suggested.remark || ''
}

function sampleFor(columnKey) {
  if (!columnKey) return ''
  const row = preview.value?.rows?.find((item) => item?.[columnKey])
  const value = row?.[columnKey]
  return value === undefined || value === null ? '' : String(value)
}

async function commitImport() {
  if (!mapping.number) {
    ElMessage.warning('请先指定 number 对应列')
    return
  }
  importing.value = true
  try {
    const result = await api.post('/api/customers/imports', {
      path: preview.value.path,
      sheet_name: sheetName.value || null,
      mapping,
    })
    ElMessage.success(`导入 ${result.imported_count} 条，更新 ${result.updated_count} 条，跳过 ${result.skipped_count} 条`)
    await reloadCustomersFromFirstPage()
    viewMode.value = 'table'
  } finally {
    importing.value = false
  }
}

function backToTable() {
  viewMode.value = 'table'
}

async function loadCustomers() {
  customersLoading.value = true
  try {
    const query = new URLSearchParams()
    if (filters.keyword) query.set('keyword', filters.keyword)
    if (filters.add_status) query.set('add_status', filters.add_status)
    query.set('page', pagination.page)
    query.set('page_size', pagination.page_size)
    const result = await api.get(`/api/customers?${query.toString()}`)
    customers.value = result.items || []
    pagination.total = result.total || 0
  } finally {
    customersLoading.value = false
  }
}

function reloadCustomersFromFirstPage() {
  pagination.page = 1
  return loadCustomers()
}

function handlePageSizeChange() {
  pagination.page = 1
  loadCustomers()
}

function handleSelectionChange(rows) {
  selectedCustomers.value = rows
}

function openGreetingsDialog(scope) {
  greetingsScope.value = scope
  greetingsDraft.value = ''
  greetingsDialogVisible.value = true
}

async function saveGreetings() {
  savingGreetings.value = true
  try {
    const selected = greetingsScope.value === 'selected'
    const hasFilter = Boolean(filters.keyword || filters.add_status)
    const result = await api.patch('/api/customers/greetings', {
      greetings: greetingsDraft.value,
      customer_ids: selected || !hasFilter ? (selected ? selectedCustomers.value : customers.value).map((row) => row.id) : [],
      keyword: selected || !hasFilter ? null : filters.keyword || null,
      add_status: selected || !hasFilter ? null : filters.add_status || null,
    })
    ElMessage.success(`已更新 ${result.updated} 位客户的招呼语`)
    greetingsDialogVisible.value = false
    await loadCustomers()
  } finally {
    savingGreetings.value = false
  }
}

async function batchAddSelected() {
  await createBatchTask(selectedCustomers.value.map((row) => row.id), '将选中的客户发起好友添加？')
}

async function batchAddFiltered() {
  await createBatchTask([], '将当前筛选结果全部发起好友添加？')
}

async function createBatchTask(customerIds, message) {
  await ElMessageBox.confirm(message, '确认批量添加', { type: 'warning' })
  await api.post('/api/customers/batch-add', {
    customer_ids: customerIds,
    keyword: customerIds.length ? null : filters.keyword || null,
    add_status: customerIds.length ? null : filters.add_status || 'pending',
    chat_only: addOptions.chat_only,
  })
  ElMessage.success('批量添加任务已创建')
  emit('task-created')
  await loadCustomers()
}

function openRaw(row) {
  currentRaw.value = row.raw || {}
  rawVisible.value = true
}

function openEdit(row) {
  editingCustomerId.value = row.id
  editForm.number = row.number || ''
  editForm.remark = row.remark || ''
  editForm.greetings = row.greetings || ''
  editForm.add_status = row.add_status || 'pending'
  editVisible.value = true
}

async function saveCustomer() {
  if (!editForm.number.trim()) {
    ElMessage.warning('号码不能为空')
    return
  }
  savingCustomer.value = true
  try {
    await api.patch(`/api/customers/${encodeURIComponent(editingCustomerId.value)}`, {
      number: editForm.number.trim(),
      remark: editForm.remark,
      greetings: editForm.greetings,
      add_status: editForm.add_status,
    })
    ElMessage.success('客户信息已保存')
    editVisible.value = false
    await loadCustomers()
  } finally {
    savingCustomer.value = false
  }
}

function statusText(status) {
  return { pending: '待添加', adding: '添加中', added: '已添加', failed: '失败' }[status] || status
}

function statusType(status) {
  return { pending: 'info', adding: 'warning', added: 'success', failed: 'danger' }[status] || 'info'
}

onMounted(loadCustomers)
</script>
