<template>
  <div class="pricing-container">
    <div class="page-header">
      <h1>选择套餐</h1>
      <p class="subtitle">选择最适合您业务规模的方案</p>
    </div>

    <div v-loading="loading" class="tiers-grid">
      <el-card
        v-for="tier in tiers"
        :key="tier.id"
        class="tier-card"
        :class="{
          'current-tier': tier.id === currentTierId,
          'popular': tier.popular
        }"
        shadow="hover"
      >
        <div v-if="tier.popular" class="popular-badge">最受欢迎</div>
        <div v-if="tier.id === currentTierId" class="current-badge">当前套餐</div>

        <div class="tier-header">
          <h2 class="tier-name">{{ tier.name }}</h2>
          <div class="tier-price">
            <span class="price-symbol">¥</span>
            <span class="price-value">{{ tier.price }}</span>
            <span class="price-period" v-if="tier.price > 0">/{{ tier.period }}</span>
            <span class="price-free" v-else>免费</span>
          </div>
          <p class="tier-desc">{{ tier.description }}</p>
        </div>

        <div class="tier-features">
          <div class="feature-item">
            <el-icon><Dish /></el-icon>
            <span>菜品数量 <strong>{{ tier.limits.dishes }}</strong> 个</span>
          </div>
          <div class="feature-item">
            <el-icon><Grid /></el-icon>
            <span>桌台数量 <strong>{{ tier.limits.tables }}</strong> 个</span>
          </div>
          <div class="feature-item">
            <el-icon><User /></el-icon>
            <span>员工账号 <strong>{{ tier.limits.staff }}</strong> 个</span>
          </div>
          <div class="feature-item" v-if="tier.limits.orders !== -1">
            <el-icon><Document /></el-icon>
            <span>月订单量 <strong>{{ tier.limits.orders }}</strong> 单</span>
          </div>
          <div class="feature-item" v-else>
            <el-icon><Document /></el-icon>
            <span>月订单量 <strong>不限</strong></span>
          </div>
          <div class="feature-item" v-if="tier.features">
            <el-icon><CircleCheck /></el-icon>
            <span>{{ tier.features }}</span>
          </div>
        </div>

        <div class="tier-actions">
          <el-button
            v-if="tier.id !== currentTierId"
            type="primary"
            size="large"
            class="upgrade-btn"
            @click="handleUpgrade(tier)"
          >
            升级到 {{ tier.name }}
          </el-button>
          <el-button
            v-else
            type="info"
            size="large"
            disabled
            class="current-btn"
          >
            当前套餐
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- 升级说明 -->
    <div class="upgrade-note">
      <el-icon><InfoFilled /></el-icon>
      <span>升级套餐后，新功能即刻生效。如需降级或退款，请联系客服。</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Dish, Grid, User, Document, CircleCheck, InfoFilled } from '@element-plus/icons-vue'
import { tierApi } from '@/services/api'

interface TierLimits {
  dishes: number
  tables: number
  staff: number
  orders: number
}

interface Tier {
  id: string
  name: string
  price: number
  period: string
  description: string
  limits: TierLimits
  features?: string
  popular?: boolean
}

const loading = ref(false)
const tiers = ref<Tier[]>([])
const currentTierId = ref<string>('')

const loadTiers = async () => {
  loading.value = true
  try {
    const res = await tierApi.getTiers()
    tiers.value = res.data || []
  } catch (error) {
    console.error('加载套餐失败:', error)
    ElMessage.error('加载套餐信息失败')
  } finally {
    loading.value = false
  }
}

const loadTenant = async () => {
  try {
    const res = await tierApi.getTenant()
    currentTierId.value = res.data?.tier || ''
  } catch (error) {
    console.error('加载商户信息失败:', error)
  }
}

const handleUpgrade = (tier: Tier) => {
  window.dispatchEvent(new CustomEvent('show-upgrade-modal', {
    detail: {
      current_tier: currentTierId.value,
      target_tier: tier.id,
      target_tier_name: tier.name,
      price: tier.price,
      features: tier.features ? [tier.features] : []
    }
  }))
}

onMounted(() => {
  loadTiers()
  loadTenant()
})
</script>

<style scoped>
.pricing-container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  text-align: center;
  margin-bottom: 40px;
}

.page-header h1 {
  margin: 0 0 10px;
  font-size: 28px;
  color: #303133;
}

.subtitle {
  margin: 0;
  color: #909399;
  font-size: 16px;
}

.tiers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 24px;
}

.tier-card {
  position: relative;
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  transition: transform 0.3s, box-shadow 0.3s;
}

.tier-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
}

.tier-card.current-tier {
  border: 2px solid #409eff;
}

.tier-card.popular {
  border: 2px solid #67c23a;
}

.popular-badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: #67c23a;
  color: white;
  padding: 4px 16px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.current-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  background: #409eff;
  color: white;
  padding: 2px 10px;
  border-radius: 8px;
  font-size: 12px;
}

.tier-header {
  text-align: center;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
  margin-bottom: 20px;
}

.tier-name {
  margin: 0 0 12px;
  font-size: 20px;
  color: #303133;
}

.tier-price {
  margin-bottom: 8px;
}

.price-symbol {
  font-size: 18px;
  color: #f56c6c;
  vertical-align: top;
}

.price-value {
  font-size: 42px;
  font-weight: 700;
  color: #f56c6c;
}

.price-period {
  font-size: 14px;
  color: #909399;
}

.price-free {
  font-size: 24px;
  font-weight: 700;
  color: #67c23a;
}

.tier-desc {
  margin: 0;
  font-size: 13px;
  color: #909399;
}

.tier-features {
  flex: 1;
  padding: 0 0 20px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  color: #606266;
}

.feature-item .el-icon {
  color: #67c23a;
  font-size: 16px;
}

.feature-item strong {
  color: #303133;
}

.tier-actions {
  margin-top: auto;
}

.upgrade-btn,
.current-btn {
  width: 100%;
}

.tier-card.popular .upgrade-btn {
  background: #67c23a;
  border-color: #67c23a;
}

.upgrade-note {
  margin-top: 30px;
  padding: 12px 16px;
  background: #f4f4f5;
  border-radius: 8px;
  font-size: 13px;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
}
</style>
