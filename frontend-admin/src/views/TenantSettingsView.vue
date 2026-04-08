<template>
  <div class="tenant-settings-container">
    <!-- 当前套餐区块 -->
    <el-card class="plan-card">
      <template #header>
        <div class="card-header">
          <span>当前套餐</span>
          <el-button type="primary" text @click="goToPricing">
            查看全部套餐
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </template>

      <div class="plan-overview">
        <div class="plan-info">
          <div class="plan-name">{{ usage.tier || '免费版' }}</div>
          <div class="plan-status" :class="usage.status">
            {{ getStatusText(usage.status) }}
          </div>
        </div>

        <div class="usage-bars">
          <div class="usage-item">
            <div class="usage-label">
              <span>菜品</span>
              <span>{{ usage.dish_count || 0 }} / {{ usage.dish_limit || 0 }}</span>
            </div>
            <el-progress
              :percentage="getPercentage(usage.dish_count, usage.dish_limit)"
              :stroke-width="8"
              :color="getProgressColor(usage.dish_count, usage.dish_limit)"
            />
          </div>

          <div class="usage-item">
            <div class="usage-label">
              <span>桌台</span>
              <span>{{ usage.table_count || 0 }} / {{ usage.table_limit || 0 }}</span>
            </div>
            <el-progress
              :percentage="getPercentage(usage.table_count, usage.table_limit)"
              :stroke-width="8"
              :color="getProgressColor(usage.table_count, usage.table_limit)"
            />
          </div>
        </div>

        <div v-if="usage.near_limit" class="limit-warning">
          <el-icon><Warning /></el-icon>
          <span>您的用量已接近上限，建议升级套餐以继续使用</span>
          <el-button type="primary" size="small" @click="goToPricing">立即升级</el-button>
        </div>
      </div>
    </el-card>

    <!-- 基本信息设置 -->
    <el-card class="settings-card">
      <template #header>
        <div class="card-header">
          <span>商户信息</span>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
        class="settings-form"
      >
        <el-form-item label="商户名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入商户名称" />
        </el-form-item>

        <el-form-item label="联系电话" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入联系电话" />
        </el-form-item>

        <el-form-item label="地址" prop="address">
          <el-input v-model="form.address" placeholder="请输入地址" />
        </el-form-item>

        <el-form-item label="营业时间" prop="business_hours">
          <el-input v-model="form.business_hours" placeholder="例如: 09:00-22:00" />
        </el-form-item>

        <el-form-item label="公告" prop="announcement">
          <el-input
            v-model="form.announcement"
            type="textarea"
            :rows="3"
            placeholder="店铺公告内容"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSave">
            保存设置
          </el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 修改密码 -->
    <el-card class="settings-card">
      <template #header>
        <div class="card-header">
          <span>修改密码</span>
        </div>
      </template>

      <el-form
        ref="pwdFormRef"
        :model="pwdForm"
        :rules="pwdRules"
        label-width="120px"
        class="settings-form"
      >
        <el-form-item label="当前密码" prop="old_password">
          <el-input
            v-model="pwdForm.old_password"
            type="password"
            placeholder="请输入当前密码"
            show-password
          />
        </el-form-item>

        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="pwdForm.new_password"
            type="password"
            placeholder="请输入新密码"
            show-password
          />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirm_password">
          <el-input
            v-model="pwdForm.confirm_password"
            type="password"
            placeholder="请再次输入新密码"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="pwdSaving" @click="handleChangePassword">
            修改密码
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { ArrowRight, Warning } from '@element-plus/icons-vue'
import { merchantApi, tierApi } from '@/services/api'

const router = useRouter()
const formRef = ref<FormInstance>()
const pwdFormRef = ref<FormInstance>()
const saving = ref(false)
const pwdSaving = ref(false)

const usage = reactive({
  tier: '',
  status: 'active',
  dish_count: 0,
  dish_limit: 10,
  table_count: 0,
  table_limit: 5,
  near_limit: false
})

const form = reactive({
  name: '',
  phone: '',
  address: '',
  business_hours: '',
  announcement: ''
})

const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入商户名称', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入联系电话', trigger: 'blur' }]
}

const pwdRules: FormRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== pwdForm.new_password) {
          callback(new Error('两次输入密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    active: '使用中',
    expired: '已过期',
    trial: '试用中'
  }
  return texts[status] || status
}

const getPercentage = (current: number, limit: number) => {
  if (!limit || limit <= 0) return 0
  return Math.min(Math.round((current / limit) * 100), 100)
}

const getProgressColor = (current: number, limit: number) => {
  const pct = getPercentage(current, limit)
  if (pct >= 90) return '#f56c6c'
  if (pct >= 70) return '#e6a23c'
  return '#67c23a'
}

const loadUsage = async () => {
  try {
    const res = await tierApi.getUsage()
    if (res.data) {
      Object.assign(usage, res.data)
    }
  } catch (error) {
    console.error('加载用量信息失败:', error)
  }
}

const loadSettings = async () => {
  try {
    const res = await merchantApi.getProfile()
    if (res.data) {
      Object.assign(form, res.data)
    }
  } catch (error) {
    console.error('加载设置失败:', error)
  }
}

const handleSave = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
    saving.value = true
    await merchantApi.updateProfile(form)
    ElMessage.success('保存成功')
  } catch (error) {
    console.error('保存失败:', error)
  } finally {
    saving.value = false
  }
}

const handleReset = () => {
  formRef.value?.resetFields()
  loadSettings()
}

const handleChangePassword = async () => {
  if (!pwdFormRef.value) return
  try {
    await pwdFormRef.value.validate()
    pwdSaving.value = true
    await merchantApi.changePassword({
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password
    })
    ElMessage.success('密码修改成功')
    pwdFormRef.value.resetFields()
  } catch (error) {
    console.error('修改密码失败:', error)
  } finally {
    pwdSaving.value = false
  }
}

const goToPricing = () => {
  router.push('/pricing')
}

onMounted(() => {
  loadUsage()
  loadSettings()
})
</script>

<style scoped>
.tenant-settings-container {
  max-width: 900px;
  margin: 0 auto;
}

.plan-card {
  margin-bottom: 20px;
}

.settings-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.plan-overview {
  padding: 10px 0;
}

.plan-info {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.plan-name {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
}

.plan-status {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.plan-status.active {
  background: #e8f4e8;
  color: #67c23a;
}

.plan-status.expired {
  background: #fef0f0;
  color: #f56c6c;
}

.plan-status.trial {
  background: #ecf5ff;
  color: #409eff;
}

.usage-bars {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 16px;
}

.usage-item {
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.usage-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
  color: #606266;
}

.limit-warning {
  margin-top: 16px;
  padding: 12px 16px;
  background: #fef0f0;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #f56c6c;
}

.limit-warning .el-icon {
  font-size: 16px;
}

.limit-warning .el-button {
  margin-left: auto;
}

.settings-form {
  max-width: 500px;
  margin-top: 20px;
}
</style>
