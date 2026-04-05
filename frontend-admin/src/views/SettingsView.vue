<template>
  <div class="settings-container">
    <!-- 基本信息设置 -->
    <el-card class="settings-card">
      <template #header>
        <div class="card-header">
          <span>商户设置</span>
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

    <!-- Phase 2: 支付模式设置 -->
    <el-card class="settings-card">
      <template #header>
        <div class="card-header">
          <span>支付模式</span>
        </div>
      </template>

      <div class="payment-mode-section">
        <el-radio-group v-model="paymentMode" @change="handlePaymentModeChange">
          <el-radio value="counter_pay">
            <div class="payment-mode-option">
              <div class="mode-title">柜台付款</div>
              <div class="mode-desc">顾客下单后显示支付码，凭支付码到柜台确认付款</div>
            </div>
          </el-radio>
          <el-radio value="credit_pay">
            <div class="payment-mode-option">
              <div class="mode-title">挂账模式</div>
              <div class="mode-desc">顾客下单后直接记账离场，由商户在后台确认结账</div>
            </div>
          </el-radio>
        </el-radio-group>

        <div class="payment-mode-tip">
          <el-icon><InfoFilled /></el-icon>
          <span>修改支付模式后，新下单将使用新模式，已有订单不受影响</span>
        </div>
      </div>
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
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import { merchantApi } from '@/services/api'

const formRef = ref<FormInstance>()
const pwdFormRef = ref<FormInstance>()
const saving = ref(false)
const pwdSaving = ref(false)
const paymentMode = ref<'counter_pay' | 'credit_pay'>('counter_pay')

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

// Phase 2: 加载支付模式
const loadPaymentMode = async () => {
  try {
    const res = await merchantApi.getPaymentSettings()
    if (res.data) {
      paymentMode.value = res.data.mode || 'counter_pay'
    }
  } catch (error) {
    console.error('加载支付模式失败:', error)
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

// Phase 2: 切换支付模式
const handlePaymentModeChange = async (val: 'counter_pay' | 'credit_pay') => {
  try {
    await merchantApi.updatePaymentSettings({ mode: val })
    ElMessage.success('支付模式已更新')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '更新支付模式失败')
    // 恢复原值
    paymentMode.value = paymentMode.value === 'counter_pay' ? 'credit_pay' : 'counter_pay'
  }
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

onMounted(() => {
  loadSettings()
  loadPaymentMode()
})
</script>

<style scoped>
.settings-container {
  max-width: 800px;
  margin: 0 auto;
}

.settings-card {
  margin-bottom: 20px;
}

.card-header {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.settings-form {
  max-width: 500px;
  margin-top: 20px;
}

/* Phase 2: 支付模式样式 */
.payment-mode-section {
  padding: 10px 0;
}

.payment-mode-option {
  display: inline-block;
  text-align: left;
  vertical-align: middle;
  margin-left: 8px;
}

.mode-title {
  font-size: 15px;
  font-weight: 600;
  color: #333;
}

.mode-desc {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}

.payment-mode-tip {
  margin-top: 16px;
  padding: 10px 12px;
  background: #f4f4f5;
  border-radius: 6px;
  font-size: 12px;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 6px;
}

:deep(.el-radio) {
  margin-bottom: 16px;
  display: flex;
  align-items: flex-start;
}

:deep(.el-radio__label) {
  white-space: normal;
  line-height: 1.5;
}
</style>
