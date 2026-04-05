<template>
  <div class="category-manager">
    <div class="page-header">
      <h1>分类管理</h1>
      <div class="header-actions">
        <el-button type="primary" @click="showAddDialog">
          <el-icon><Plus /></el-icon>
          新增分类
        </el-button>
      </div>
    </div>

    <!-- 分类列表 -->
    <el-card>
      <el-table
        :data="sortedCategories"
        v-loading="loading"
        style="width: 100%"
        empty-text="暂无分类数据"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="分类名称" min-width="200">
          <template #default="{ row }">
            <span class="category-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="120" sortable>
          <template #default="{ row }">
            <el-tag type="info">{{ row.sort_order ?? 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="showEditDialog(row)">
              编辑
            </el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

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
        <el-form-item label="分类名称" prop="name">
          <el-input
            v-model="form.name"
            placeholder="请输入分类名称"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="排序" prop="sort_order">
          <el-input-number
            v-model="form.sort_order"
            :min="0"
            :max="9999"
            controls-position="right"
          />
          <span class="form-tip">数值越小越靠前</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { categoryApi } from '@/services/api'

// 格式化日期
const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 获取错误信息（兼容 FastAPI 的 detail 字段）
const getErrorMessage = (error: any): string => {
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || '操作失败'
}

const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

interface Category {
  id: number
  name: string
  sort_order?: number
  created_at: string
}

const categories = ref<Category[]>([])

const form = ref({
  name: '',
  sort_order: 0
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入分类名称', trigger: 'blur' },
    { min: 1, max: 50, message: '长度在 1 到 50 个字符', trigger: 'blur' }
  ]
}

const dialogTitle = computed(() => isEdit.value ? '编辑分类' : '新增分类')

// 按 sort_order 排序
const sortedCategories = computed(() => {
  return [...categories.value].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
})

// 加载分类列表
const loadCategories = async () => {
  loading.value = true
  try {
    const res = await categoryApi.getCategories()
    categories.value = res.data ?? []
  } catch (error: any) {
    console.error('加载分类失败:', error)
    ElMessage.error(getErrorMessage(error))
  } finally {
    loading.value = false
  }
}

// 显示新增弹窗
const showAddDialog = () => {
  isEdit.value = false
  editingId.value = null
  form.value = { name: '', sort_order: 0 }
  dialogVisible.value = true
}

// 显示编辑弹窗
const showEditDialog = (row: Category) => {
  isEdit.value = true
  editingId.value = row.id
  form.value = {
    name: row.name,
    sort_order: row.sort_order ?? 0
  }
  dialogVisible.value = true
}

// 重置表单
const resetForm = () => {
  formRef.value?.resetFields()
  form.value = { name: '', sort_order: 0 }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitLoading.value = true
    try {
      if (isEdit.value && editingId.value !== null) {
        await categoryApi.updateCategory(editingId.value, {
          name: form.value.name,
          sort_order: form.value.sort_order
        })
        ElMessage.success('更新成功')
      } else {
        await categoryApi.createCategory({
          name: form.value.name,
          sort_order: form.value.sort_order
        })
        ElMessage.success('新增成功')
      }
      dialogVisible.value = false
      await loadCategories()
    } catch (error: any) {
      console.error('保存失败:', error)
      ElMessage.error(getErrorMessage(error))
    } finally {
      submitLoading.value = false
    }
  })
}

// 删除分类
const handleDelete = (row: Category) => {
  ElMessageBox.confirm(
    '确定要删除该分类吗？',
    '删除确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )
    .then(async () => {
      try {
        await categoryApi.deleteCategory(row.id)
        ElMessage.success('删除成功')
        await loadCategories()
      } catch (error: any) {
        console.error('删除失败:', error)
        const msg = getErrorMessage(error)
        if (msg.includes('菜品')) {
          ElMessage.error('请先删除该分类下的菜品')
        } else {
          ElMessage.error(msg)
        }
      }
    })
    .catch(() => {})
}

onMounted(() => {
  loadCategories()
})
</script>

<style scoped>
.category-manager {
  padding: 20px;
  max-width: 900px;
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

.category-name {
  font-weight: 500;
}

.form-tip {
  margin-left: 10px;
  color: #999;
  font-size: 12px;
}
</style>
