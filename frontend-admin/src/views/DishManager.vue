<template>
  <div class="dish-manager">
    <div class="page-header">
      <h1>菜品管理</h1>
      <div class="header-actions">
        <el-button type="primary" @click="showAddDialog">
          <el-icon><Plus /></el-icon>
          新增菜品
        </el-button>
      </div>
    </div>

    <!-- 筛选条件 -->
    <el-card class="filter-card">
      <div class="filter-form">
        <el-form :inline="true" :model="filterForm">
          <el-form-item label="分类">
            <el-select
              v-model="filterForm.category_id"
              placeholder="全部分类"
              clearable
              @change="handleCategoryFilter"
            >
              <el-option
                v-for="category in categories"
                :key="category.id"
                :label="category.name"
                :value="category.id"
              />
            </el-select>
          </el-form-item>
        </el-form>

        <!-- 视图切换 -->
        <div class="view-toggle">
          <el-radio-group v-model="viewMode" size="small">
            <el-radio-button label="table">
              <el-icon><Grid /></el-icon>
              表格
            </el-radio-button>
            <el-radio-button label="card">
              <el-icon><Menu /></el-icon>
              卡片
            </el-radio-button>
          </el-radio-group>
        </div>
      </div>
    </el-card>

    <!-- 表格视图 -->
    <el-card v-show="viewMode === 'table'">
      <el-table
        :data="paginatedDishes"
        v-loading="loading"
        style="width: 100%"
      >
        <el-table-column label="菜品图片" width="100">
          <template #default="{ row }">
            <div class="dish-image">
              <img
                v-if="row.image_url && !imageErrors[row.id]"
                :src="row.image_url"
                :alt="row.name"
                @error="() => handleImageError(row.id)"
              />
              <div v-else class="no-image">
                <el-icon><Picture /></el-icon>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="name" label="菜品名称" width="180" />

        <el-table-column label="分类" width="140">
          <template #default="{ row }">
            {{ getCategoryName(row.category_id) }}
          </template>
        </el-table-column>

        <el-table-column prop="price" label="价格" width="100">
          <template #default="{ row }">
            ¥{{ row.price }}
          </template>
        </el-table-column>

        <el-table-column prop="description" label="描述" min-width="200">
          <template #default="{ row }">
            <div class="description">
              {{ row.description || '暂无描述' }}
            </div>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_available"
              :loading="row.statusLoading"
              @change="handleStatusChange(row)"
            />
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click="showEditDialog(row)"
            >
              编辑
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.current"
          v-model:page-size="pagination.size"
          :total="filteredDishes.length"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 卡片视图 -->
    <div v-show="viewMode === 'card'" class="card-grid">
      <el-card
        v-for="dish in paginatedDishes"
        :key="dish.id"
        class="dish-card"
        :body-style="{ padding: '0px' }"
      >
        <div class="dish-card-image">
          <img
            v-if="dish.image_url && !imageErrors[dish.id]"
            :src="dish.image_url"
            :alt="dish.name"
            @error="() => handleImageError(dish.id)"
          />
          <div v-else class="no-image">
            <el-icon><Picture /></el-icon>
            <span>暂无图片</span>
          </div>
          <div class="dish-card-status">
            <el-tag :type="dish.is_available ? 'success' : 'info'" size="small">
              {{ dish.is_available ? '上架' : '下架' }}
            </el-tag>
          </div>
        </div>
        <div class="dish-card-content">
          <h3 class="dish-card-name">{{ dish.name }}</h3>
          <div class="dish-card-category">{{ getCategoryName(dish.category_id) }}</div>
          <div class="dish-card-price">¥{{ dish.price }}</div>
          <div class="dish-card-desc">{{ dish.description || '暂无描述' }}</div>
        </div>
        <div class="dish-card-actions">
          <el-switch
            v-model="dish.is_available"
            :loading="dish.statusLoading"
            @change="handleStatusChange(dish)"
            active-text="上架"
            inactive-text="下架"
          />
          <div class="action-buttons">
            <el-button type="primary" size="small" @click="showEditDialog(dish)">
              编辑
            </el-button>
            <el-button type="danger" size="small" @click="handleDelete(dish)">
              删除
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 空状态 -->
    <el-empty v-if="!loading && filteredDishes.length === 0" description="暂无菜品" />

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="dishFormRef"
        :model="dishForm"
        :rules="dishRules"
        label-width="80px"
      >
        <el-form-item label="菜品名称" prop="name">
          <el-input
            v-model="dishForm.name"
            placeholder="请输入菜品名称"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="分类" prop="category_id">
          <el-select
            v-model="dishForm.category_id"
            placeholder="请选择分类"
            style="width: 100%"
          >
            <el-option
              v-for="category in categories"
              :key="category.id"
              :label="category.name"
              :value="category.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="价格" prop="price">
          <el-input-number
            v-model="dishForm.price"
            :min="0.01"
            :precision="2"
            :step="1"
            style="width: 100%"
            placeholder="请输入价格（必须大于0）"
          />
        </el-form-item>

        <el-form-item label="图片URL" prop="image_url">
          <el-input
            v-model="dishForm.image_url"
            placeholder="请输入图片URL（可选）"
            @input="onImageUrlInput"
          />
          <div v-if="dishForm.image_url && !previewError" class="image-preview">
            <img
              :src="dishForm.image_url"
              alt="预览"
              @error="handlePreviewError"
            />
          </div>
          <div v-else-if="dishForm.image_url && previewError" class="preview-error">
            图片加载失败，请检查URL
          </div>
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input
            v-model="dishForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入菜品描述（可选）"
          />
        </el-form-item>

        <el-form-item label="状态" prop="is_available">
          <el-switch v-model="dishForm.is_available" />
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="dialogLoading"
            @click="handleSubmit"
          >
            确定
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Plus, Grid, Menu, Picture } from '@element-plus/icons-vue'
import { dishApi, categoryApi } from '@/services/api'

// 获取错误信息
const getErrorMessage = (error: any): string => {
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || '操作失败'
}

// 视图模式
const viewMode = ref<'table' | 'card'>('table')

// 筛选表单
const filterForm = reactive({
  category_id: undefined as number | undefined
})

// 分页
const pagination = reactive({
  current: 1,
  size: 20
})

// 菜品列表（完整数据）
const allDishes = ref<any[]>([])
const categories = ref<any[]>([])
const loading = ref(false)

// 图片错误记录
const imageErrors = ref<Record<number, boolean>>({})

// 对话框相关
const dialogVisible = ref(false)
const dialogTitle = ref('新增菜品')
const dialogLoading = ref(false)
const dishFormRef = ref<FormInstance>()
const dishForm = reactive({
  id: undefined as number | undefined,
  name: '',
  category_id: undefined as number | undefined,
  price: 0,
  image_url: '',
  description: '',
  is_available: true
})

// 实时预览错误标记
const previewError = ref(false)

// 表单验证规则 - price 必须 > 0
const dishRules: FormRules = {
  name: [
    { required: true, message: '请输入菜品名称', trigger: 'blur' },
    { min: 1, max: 100, message: '长度在 1 到 100 个字符', trigger: 'blur' }
  ],
  category_id: [
    { required: true, message: '请选择分类', trigger: 'change' }
  ],
  price: [
    { required: true, message: '请输入价格', trigger: 'blur' },
    {
      validator: (_rule: any, value: number, callback: any) => {
        if (value === undefined || value === null || value <= 0) {
          callback(new Error('价格必须大于 0'))
        } else {
          callback()
        }
      },
      trigger: 'change'
    }
  ]
}

// 根据 category_id 获取分类名称
const getCategoryName = (categoryId: number) => {
  const cat = categories.value.find(c => c.id === categoryId)
  return cat ? cat.name : '未分类'
}

// 过滤后的菜品
const filteredDishes = computed(() => {
  if (!filterForm.category_id) {
    return allDishes.value
  }
  return allDishes.value.filter(d => d.category_id === filterForm.category_id)
})

// 分页后的菜品
const paginatedDishes = computed(() => {
  const start = (pagination.current - 1) * pagination.size
  const end = start + pagination.size
  return filteredDishes.value.slice(start, end)
})

// 加载分类数据
const loadCategories = async () => {
  try {
    const res = await categoryApi.getCategories()
    categories.value = res.data ?? []
  } catch (error) {
    console.error('加载分类失败:', error)
  }
}

// 加载菜品数据（后端返回数组）
const loadDishes = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (filterForm.category_id) {
      params.category_id = filterForm.category_id
    }
    const res = await dishApi.getDishes(params)
    // 后端返回数组，不是分页对象
    allDishes.value = Array.isArray(res.data) ? res.data : []
    // 重置到第一页
    pagination.current = 1
  } catch (error: any) {
    console.error('加载菜品失败:', error)
    ElMessage.error(getErrorMessage(error))
    allDishes.value = []
  } finally {
    loading.value = false
  }
}

// 分类筛选变化
const handleCategoryFilter = () => {
  pagination.current = 1
  // 分类筛选不需要重新加载，因为后端支持按 category_id 筛选
  // 但为了简化，这里直接用前端过滤
  loadDishes()
}

// 分页大小变化
const handleSizeChange = (_size: number) => {
  pagination.current = 1
}

// 当前页变化
const handleCurrentChange = (_page: number) => {
  // 纯前端分页，无需操作
}

// 处理状态变化
const handleStatusChange = async (dish: any) => {
  dish.statusLoading = true
  try {
    await dishApi.toggleAvailable(dish.id)
    ElMessage.success(dish.is_available ? '上架成功' : '下架成功')
  } catch (error) {
    console.error('更新状态失败:', error)
    dish.is_available = !dish.is_available
    ElMessage.error(getErrorMessage(error))
  } finally {
    dish.statusLoading = false
  }
}

// 显示新增对话框
const showAddDialog = () => {
  dialogTitle.value = '新增菜品'
  previewError.value = false
  Object.assign(dishForm, {
    id: undefined,
    name: '',
    category_id: undefined,
    price: 0,
    image_url: '',
    description: '',
    is_available: true
  })
  dialogVisible.value = true
}

// 显示编辑对话框
const showEditDialog = (dish: any) => {
  dialogTitle.value = '编辑菜品'
  previewError.value = false
  Object.assign(dishForm, {
    id: dish.id,
    name: dish.name,
    category_id: dish.category_id,
    price: dish.price,
    image_url: dish.image_url || '',
    description: dish.description || '',
    is_available: dish.is_available
  })
  dialogVisible.value = true
}

// 处理提交
const handleSubmit = async () => {
  if (!dishFormRef.value) return

  try {
    await dishFormRef.value.validate()

    // 再次校验 price > 0
    if (dishForm.price === undefined || dishForm.price === null || dishForm.price <= 0) {
      ElMessage.error('价格必须大于 0')
      return
    }

    dialogLoading.value = true

    const payload = {
      name: dishForm.name,
      category_id: dishForm.category_id!,
      price: dishForm.price,
      description: dishForm.description || '',
      image_url: dishForm.image_url || '',
      is_available: dishForm.is_available
    }

    if (dishForm.id) {
      // 更新菜品
      await dishApi.updateDish(dishForm.id, payload)
      ElMessage.success('更新菜品成功')
    } else {
      // 新增菜品
      await dishApi.createDish(payload)
      ElMessage.success('新增菜品成功')
    }

    dialogVisible.value = false
    loadDishes()
  } catch (error: any) {
    if (error !== false) {
      console.error('保存菜品失败:', error)
      ElMessage.error(getErrorMessage(error))
    }
  } finally {
    dialogLoading.value = false
  }
}

// 处理删除
const handleDelete = (dish: any) => {
  ElMessageBox.confirm(
    `确定要删除菜品 "${dish.name}" 吗？`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await dishApi.deleteDish(dish.id)
      ElMessage.success('删除菜品成功')
      loadDishes()
    } catch (error) {
      console.error('删除菜品失败:', error)
      ElMessage.error(getErrorMessage(error))
    }
  }).catch(() => {
    // 用户取消
  })
}

// 处理图片加载错误（列表卡片）
const handleImageError = (dishId: number) => {
  imageErrors.value[dishId] = true
}

// 预览图输入处理
const onImageUrlInput = () => {
  previewError.value = false
}

const handlePreviewError = () => {
  previewError.value = true
}

onMounted(() => {
  loadCategories()
  loadDishes()
})
</script>

<style scoped>
.dish-manager {
  padding: 20px;
  max-width: 1400px;
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

.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 15px;
}

.view-toggle {
  display: flex;
  align-items: center;
}

/* 表格视图样式 */
.dish-image {
  width: 60px;
  height: 60px;
  border-radius: 6px;
  overflow: hidden;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dish-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-image {
  color: #999;
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.description {
  max-height: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

/* 卡片视图样式 */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.dish-card {
  transition: transform 0.3s, box-shadow 0.3s;
}

.dish-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.dish-card-image {
  height: 180px;
  overflow: hidden;
  background: #f5f5f5;
  position: relative;
}

.dish-card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.dish-card-image .no-image {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  gap: 8px;
  color: #999;
}

.dish-card-image .no-image span {
  font-size: 12px;
}

.dish-card-status {
  position: absolute;
  top: 10px;
  right: 10px;
}

.dish-card-content {
  padding: 15px;
}

.dish-card-name {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.dish-card-category {
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
}

.dish-card-price {
  font-size: 20px;
  font-weight: bold;
  color: #f56c6c;
  margin-bottom: 8px;
}

.dish-card-desc {
  font-size: 13px;
  color: #666;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dish-card-actions {
  padding: 12px 15px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

/* 图片预览 */
.image-preview {
  margin-top: 10px;
}

.image-preview img {
  max-width: 100%;
  max-height: 200px;
  border-radius: 6px;
  border: 1px solid #dcdfe6;
}

.preview-error {
  margin-top: 8px;
  color: #f56c6c;
  font-size: 12px;
}
</style>
