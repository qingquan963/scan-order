<template>
  <div class="table-manager">
    <div class="page-header">
      <h1>桌台管理</h1>
      <div class="header-actions">
        <el-button type="primary" @click="showAddDialog">
          <el-icon><Plus /></el-icon>
          新增桌台
        </el-button>
      </div>
    </div>

    <!-- 桌台列表（卡片展示） -->
    <div v-loading="loading" class="table-cards">
      <el-card
        v-for="table in tables"
        :key="table.id"
        class="table-card"
        shadow="hover"
      >
        <div class="card-body">
          <div class="card-icon" :class="statusClass(table.status)">
            <el-icon><Grid /></el-icon>
          </div>
          <div class="card-info">
            <div class="table-code">{{ table.code }}</div>
            <div class="table-name">{{ table.name }}</div>
            <div class="table-capacity">
              <el-icon><User /></el-icon>
              {{ table.capacity ?? 0 }}人
            </div>
          </div>
          <div class="card-status">
            <el-tag :type="statusTagType(table.status)" size="small">
              {{ statusLabel(table.status) }}
            </el-tag>
          </div>
        </div>
        <div class="card-actions">
          <!-- Phase 2: 查看二维码按钮 -->
          <el-button type="info" size="small" @click="showQrCode(table)">
            二维码
          </el-button>
          <el-button type="primary" size="small" @click="showEditDialog(table)">
            编辑
          </el-button>
          <el-button type="danger" size="small" @click="handleDelete(table)">
            删除
          </el-button>
        </div>
      </el-card>

      <!-- 空状态 -->
      <div v-if="!loading && tables.length === 0" class="empty-state">
        <el-empty description="暂无桌台数据，请点击上方按钮添加" />
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="桌台编号" prop="code">
          <el-input
            v-model="form.code"
            placeholder="请输入唯一编号，如 A01"
            maxlength="20"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="桌台名称" prop="name">
          <el-input
            v-model="form.name"
            placeholder="请输入桌台名称，如 靠窗双人桌"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="容量" prop="capacity">
          <el-input-number
            v-model="form.capacity"
            :min="1"
            :max="99"
            controls-position="right"
          />
          <span class="form-tip">可容纳人数</span>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="form.status" placeholder="请选择状态" style="width: 100%">
            <el-option label="空闲" value="available" />
            <el-option label="占用" value="occupied" />
            <el-option label="预订" value="reserved" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- Phase 2: 二维码弹窗 -->
    <el-dialog
      v-model="qrDialogVisible"
      :title="`桌台二维码 - ${currentTable?.name || ''}`"
      width="360px"
      align-center
    >
      <div class="qrcode-container" v-if="currentTable">
        <div class="qrcode-info">
          <div class="qrcode-table-name">{{ currentTable.name }}</div>
          <div class="qrcode-table-code">编号: {{ currentTable.code }}</div>
        </div>
        <div class="qrcode-image" v-loading="qrLoading">
          <img
            v-if="qrCodeUrl"
            :src="qrCodeUrl"
            :alt="`Table ${currentTable.code} QR Code`"
            class="qrcode-img"
          />
          <div v-else-if="!qrLoading" class="qrcode-placeholder">
            加载中...
          </div>
        </div>
        <div class="qrcode-tip">
          <el-icon><InfoFilled /></el-icon>
          顾客扫描二维码即可开始点餐
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Grid, User, InfoFilled } from '@element-plus/icons-vue'
import { tableApi } from '@/services/api'

const API_BASE = 'http://localhost:8002/api/v1'

const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

// Phase 2: QR Code dialog
const qrDialogVisible = ref(false)
const qrLoading = ref(false)
const qrCodeUrl = ref('')
const currentTable = ref<Table | null>(null)

interface Table {
  id: number
  code: string
  name: string
  capacity?: number
  status?: string
  created_at?: string
}

const tables = ref<Table[]>([])

const form = ref({
  code: '',
  name: '',
  capacity: 4,
  status: 'available'
})

const rules: FormRules = {
  code: [
    { required: true, message: '请输入桌台编号', trigger: 'blur' },
    { min: 1, max: 20, message: '长度在 1 到 20 个字符', trigger: 'blur' }
  ],
  name: [
    { required: true, message: '请输入桌台名称', trigger: 'blur' },
    { min: 1, max: 50, message: '长度在 1 到 50 个字符', trigger: 'blur' }
  ],
  capacity: [
    { required: true, message: '请输入容量', trigger: 'blur' }
  ],
  status: [
    { required: true, message: '请选择状态', trigger: 'change' }
  ]
}

const dialogTitle = computed(() => isEdit.value ? '编辑桌台' : '新增桌台')

const statusLabel = (status?: string) => {
  const map: Record<string, string> = {
    available: '空闲',
    occupied: '占用',
    reserved: '预订'
  }
  return map[status ?? 'available'] ?? '空闲'
}

const statusTagType = (status?: string) => {
  const map: Record<string, string> = {
    available: 'success',
    occupied: 'danger',
    reserved: 'warning'
  }
  return map[status ?? 'available'] ?? 'info'
}

const statusClass = (status?: string) => {
  const map: Record<string, string> = {
    available: 'status-available',
    occupied: 'status-occupied',
    reserved: 'status-reserved'
  }
  return map[status ?? 'available'] ?? 'status-available'
}

// 加载桌台列表
const loadTables = async () => {
  loading.value = true
  try {
    const res = await tableApi.getTables()
    tables.value = res.data?.data ?? res.data ?? []
  } catch (error: any) {
    console.error('加载桌台失败:', error)
    ElMessage.error(error?.response?.data?.detail || '加载桌台失败')
  } finally {
    loading.value = false
  }
}

// 显示新增弹窗
const showAddDialog = () => {
  isEdit.value = false
  editingId.value = null
  form.value = { code: '', name: '', capacity: 4, status: 'available' }
  dialogVisible.value = true
}

// 显示编辑弹窗
const showEditDialog = (row: Table) => {
  isEdit.value = true
  editingId.value = row.id
  form.value = {
    code: row.code,
    name: row.name,
    capacity: row.capacity ?? 4,
    status: row.status ?? 'available'
  }
  dialogVisible.value = true
}

// Phase 2: 显示二维码
const showQrCode = async (row: Table) => {
  currentTable.value = row
  qrDialogVisible.value = true
  qrCodeUrl.value = ''
  qrLoading.value = true
  try {
    // 直接使用 img 标签加载后端PNG
    qrCodeUrl.value = `${API_BASE}/admin/tables/${row.id}/qrcode`
  } catch (error) {
    console.error('加载二维码失败:', error)
    ElMessage.error('加载二维码失败')
  } finally {
    qrLoading.value = false
  }
}

// 重置表单
const resetForm = () => {
  formRef.value?.resetFields()
  form.value = { code: '', name: '', capacity: 4, status: 'available' }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitLoading.value = true
    try {
      if (isEdit.value && editingId.value !== null) {
        await tableApi.updateTable(editingId.value, {
          code: form.value.code,
          name: form.value.name,
          capacity: form.value.capacity,
          status: form.value.status
        })
        ElMessage.success('更新成功')
      } else {
        await tableApi.createTable({
          code: form.value.code,
          name: form.value.name,
          capacity: form.value.capacity,
          status: form.value.status
        })
        ElMessage.success('新增成功')
      }
      dialogVisible.value = false
      await loadTables()
    } catch (error: any) {
      console.error('保存失败:', error)
      const status = error?.response?.status
      if (status === 409) {
        ElMessage.error('桌台编号已存在')
      } else {
        ElMessage.error(error?.response?.data?.detail || '保存失败')
      }
    } finally {
      submitLoading.value = false
    }
  })
}

// 删除桌台
const handleDelete = (row: Table) => {
  ElMessageBox.confirm(
    `确定要删除桌台「${row.name}」吗？`,
    '删除确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )
    .then(async () => {
      try {
        await tableApi.deleteTable(row.id)
        ElMessage.success('删除成功')
        await loadTables()
      } catch (error: any) {
        console.error('删除失败:', error)
        const status = error?.response?.status
        if (status === 409) {
          ElMessage.error('该桌台存在关联订单，无法删除')
        } else {
          ElMessage.error(error?.response?.data?.detail || '删除失败')
        }
      }
    })
    .catch(() => {})
}

onMounted(() => {
  loadTables()
})
</script>

<style scoped>
.table-manager {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  color: #333;
}

.table-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 20px;
}

.table-card {
  cursor: default;
}

.card-body {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.card-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 28px;
  flex-shrink: 0;
}

.card-icon.status-available {
  background: linear-gradient(135deg, #67c23a, #85ce61);
}

.card-icon.status-occupied {
  background: linear-gradient(135deg, #f56c6c, #f78989);
}

.card-icon.status-reserved {
  background: linear-gradient(135deg, #e6a23c, #ebb563);
}

.card-info {
  flex: 1;
  min-width: 0;
}

.table-code {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}

.table-name {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.table-capacity {
  font-size: 13px;
  color: #666;
  display: flex;
  align-items: center;
  gap: 4px;
}

.card-status {
  flex-shrink: 0;
}

.card-actions {
  display: flex;
  gap: 8px;
  border-top: 1px solid #f0f0f0;
  padding-top: 12px;
}

.empty-state {
  grid-column: 1 / -1;
  padding: 60px 0;
}

.form-tip {
  margin-left: 10px;
  color: #999;
  font-size: 12px;
}

/* Phase 2: QR Code dialog styles */
.qrcode-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 10px 0;
}

.qrcode-info {
  text-align: center;
}

.qrcode-table-name {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.qrcode-table-code {
  font-size: 13px;
  color: #999;
  margin-top: 4px;
}

.qrcode-image {
  width: 240px;
  height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fafafa;
  border-radius: 8px;
}

.qrcode-img {
  width: 240px;
  height: 240px;
  object-fit: contain;
}

.qrcode-placeholder {
  color: #ccc;
  font-size: 14px;
}

.qrcode-tip {
  font-size: 12px;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
