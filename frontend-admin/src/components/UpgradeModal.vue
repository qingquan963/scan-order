<template>
  <el-dialog
    v-model="visible"
    title="升级套餐"
    width="500px"
    :close-on-click-modal="false"
  >
    <div class="upgrade-content">
      <div class="upgrade-header">
        <p>您的当前套餐无法满足需求，请升级到更高版本</p>
      </div>
      
      <div class="tier-comparison">
        <div class="tier current">
          <h3>当前套餐</h3>
          <div class="tier-name">{{ currentTierName || '免费版' }}</div>
        </div>
        <div class="arrow">→</div>
        <div class="tier target">
          <h3>目标套餐</h3>
          <div class="tier-name">{{ targetTierName || '专业版' }}</div>
          <div class="tier-price" v-if="price > 0">¥{{ price }}</div>
        </div>
      </div>
      
      <div class="upgrade-features" v-if="features.length">
        <h4>升级后享受：</h4>
        <ul>
          <li v-for="(feature, index) in features" :key="index">{{ feature }}</li>
        </ul>
      </div>

      <!-- Phase 6: 升级流程说明 -->
      <div class="upgrade-guide">
        <h4><el-icon><InfoFilled /></el-icon> 升级流程</h4>
        <ol>
          <li>
            <span class="step-num">1</span>
            <span>复制下方商户信息</span>
            <el-button size="small" @click="copyTenantInfo" :icon="CopyDocument">
              {{ copied ? '已复制!' : '复制信息' }}
            </el-button>
          </li>
          <li>
            <span class="step-num">2</span>
            <span>联系客服微信/支付宝转账 <strong>¥{{ price || 0 }}</strong></span>
          </li>
          <li>
            <span class="step-num">3</span>
            <span>客服确认后即刻开通新套餐</span>
          </li>
        </ol>
      </div>

      <!-- Phase 6: 客服联系方式 -->
      <div class="contact-section">
        <div class="contact-item">
          <span class="contact-label">微信客服</span>
          <span class="contact-value">lxb-service001</span>
          <el-button size="small" @click="copyText('lxb-service001')">复制</el-button>
        </div>
        <div class="contact-item">
          <span class="contact-label">支付宝</span>
          <span class="contact-value">pay@lobsterpos.com</span>
          <el-button size="small" @click="copyText('pay@lobsterpos.com')">复制</el-button>
        </div>
      </div>
    </div>
    
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="visible = false">关闭</el-button>
        <el-button type="primary" @click="handleUpgrade">
          我已付款，通知客服
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled, CopyDocument } from '@element-plus/icons-vue'

const visible = ref(false)
const currentTier = ref('')
const currentTierName = ref('')
const targetTier = ref('')
const targetTierName = ref('')
const price = ref(0)
const features = ref<string[]>([])
const copied = ref(false)

const handleShow = (event: Event) => {
  const detail = (event as CustomEvent).detail || {}
  currentTier.value = detail.current_tier || ''
  currentTierName.value = detail.current_tier_name || detail.current_tier || ''
  targetTier.value = detail.target_tier || ''
  targetTierName.value = detail.target_tier_name || detail.target_tier || ''
  price.value = detail.price || 0
  features.value = detail.features || []
  copied.value = false
  visible.value = true
}

const copyTenantInfo = async () => {
  const info = `商户ID: ${currentTier.value || '未知'}
目标套餐: ${targetTierName.value}
联系电话: 请在消息中告知`
  try {
    await navigator.clipboard.writeText(info)
    copied.value = true
    ElMessage.success('商户信息已复制到剪贴板')
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}

const copyText = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

const handleUpgrade = () => {
  ElMessage.info('请联系客服转账，转账后点击"我已付款，通知客服"')
  visible.value = false
}

onMounted(() => {
  window.addEventListener('show-upgrade-modal', handleShow)
})

onUnmounted(() => {
  window.removeEventListener('show-upgrade-modal', handleShow)
})
</script>

<style scoped>
.upgrade-content {
  padding: 10px 0;
}

.upgrade-header {
  text-align: center;
  margin-bottom: 20px;
}

.upgrade-header p {
  color: #666;
  font-size: 14px;
}

.tier-comparison {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  margin-bottom: 24px;
}

.tier {
  flex: 1;
  padding: 16px;
  border-radius: 8px;
  text-align: center;
}

.tier.current {
  background: #f5f5f5;
}

.tier.target {
  background: #ecf5ff;
}

.tier h3 {
  margin: 0 0 8px;
  font-size: 14px;
  color: #666;
}

.tier-name {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.tier-price {
  margin-top: 6px;
  font-size: 16px;
  font-weight: 700;
  color: #f56c6c;
}

.arrow {
  font-size: 24px;
  color: #409eff;
}

.upgrade-features {
  margin-bottom: 20px;
}

.upgrade-features h4 {
  margin: 0 0 12px;
  font-size: 14px;
  color: #333;
}

.upgrade-features ul {
  margin: 0;
  padding-left: 20px;
}

.upgrade-features li {
  margin-bottom: 8px;
  color: #666;
}

/* Phase 6: 升级流程样式 */
.upgrade-guide {
  background: #f4f4f5;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.upgrade-guide h4 {
  margin: 0 0 12px;
  font-size: 14px;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 6px;
}

.upgrade-guide ol {
  margin: 0;
  padding-left: 20px;
}

.upgrade-guide li {
  margin-bottom: 12px;
  color: #606266;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: #409eff;
  color: white;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.upgrade-guide li .el-button {
  margin-left: auto;
}

/* Phase 6: 客服联系方式 */
.contact-section {
  border: 1px dashed #dcdfe6;
  border-radius: 8px;
  padding: 12px;
}

.contact-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

.contact-item + .contact-item {
  border-top: 1px solid #ebeef5;
}

.contact-label {
  font-size: 13px;
  color: #909399;
  width: 60px;
}

.contact-value {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
  flex: 1;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
