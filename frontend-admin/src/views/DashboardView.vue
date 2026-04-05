<template>
  <div class="dashboard-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>商户后台</h1>
      <div class="header-actions">
        <el-button type="primary" @click="refreshData">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>
    
    <!-- 统计卡片 -->
    <div class="stats-cards">
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon" style="background: #409eff;">
            <el-icon><Document /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.total_orders || 0 }}</div>
            <div class="stat-label">今日订单</div>
          </div>
        </div>
      </el-card>
      
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon" style="background: #67c23a;">
            <el-icon><Money /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">¥{{ stats.total_revenue || 0 }}</div>
            <div class="stat-label">今日营业额</div>
          </div>
        </div>
      </el-card>
      
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon" style="background: #e6a23c;">
            <el-icon><Clock /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.pending_orders || 0 }}</div>
            <div class="stat-label">待接单</div>
          </div>
        </div>
      </el-card>
      
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-icon" style="background: #f56c6c;">
            <el-icon><Check /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.completed_orders || 0 }}</div>
            <div class="stat-label">已完成</div>
          </div>
        </div>
      </el-card>
    </div>
    
    <!-- 最近订单 -->
    <el-card class="recent-orders">
      <template #header>
        <div class="card-header">
          <span>最近订单</span>
          <el-button type="primary" text @click="goToOrders">
            查看全部
          </el-button>
        </div>
      </template>
      
      <el-table
        :data="recentOrders"
        v-loading="loading"
        style="width: 100%"
      >
        <el-table-column prop="order_number" label="订单号" width="180" />
        <el-table-column prop="table_id" label="桌台" width="100" />
        <el-table-column prop="total_amount" label="金额" width="100">
          <template #default="{ row }">
            ¥{{ row.total_amount }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="下单时间" width="180" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click="viewOrderDetail(row.id)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 快捷导航 -->
    <div class="quick-nav">
      <h2>快捷导航</h2>
      <div class="nav-cards">
        <el-card class="nav-card" @click="goToCategories">
          <div class="nav-content">
            <el-icon class="nav-icon"><Collection /></el-icon>
            <div class="nav-text">分类管理</div>
          </div>
        </el-card>
        
        <el-card class="nav-card" @click="goToDishes">
          <div class="nav-content">
            <el-icon class="nav-icon"><Food /></el-icon>
            <div class="nav-text">菜品管理</div>
          </div>
        </el-card>
        
        <el-card class="nav-card" @click="goToTables">
          <div class="nav-content">
            <el-icon class="nav-icon"><Grid /></el-icon>
            <div class="nav-text">桌台管理</div>
          </div>
        </el-card>
        
        <el-card class="nav-card" @click="goToOrders">
          <div class="nav-content">
            <el-icon class="nav-icon"><List /></el-icon>
            <div class="nav-text">订单管理</div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Refresh,
  Document,
  Money,
  Clock,
  Check,
  Collection,
  Food,
  Grid,
  List
} from '@element-plus/icons-vue'
import { statsApi, orderApi } from '@/services/api'

const router = useRouter()

const loading = ref(false)
const stats = ref({
  total_orders: 0,
  total_revenue: 0,
  pending_orders: 0,
  completed_orders: 0
})

const recentOrders = ref<any[]>([])

// 获取状态类型
const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    pending: 'warning',
    confirmed: 'primary',
    paid: 'success',
    cancelled: 'danger'
  }
  return types[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    pending: '待接单',
    confirmed: '已接单',
    paid: '已结账',
    cancelled: '已取消'
  }
  return texts[status] || status
}

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    // 加载统计信息
    const statsResponse = await statsApi.getTodayStats()
    if (statsResponse.data) {
      stats.value = statsResponse.data
    }
    
    // 加载最近订单
    const ordersResponse = await orderApi.getOrders({
      limit: 10,
      page: 1
    })
    if (ordersResponse.data?.orders) {
      recentOrders.value = ordersResponse.data.orders
    }
  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

// 刷新数据
const refreshData = () => {
  loadData()
  ElMessage.success('数据已刷新')
}

// 查看订单详情
const viewOrderDetail = (orderId: number) => {
  router.push(`/orders?orderId=${orderId}`)
}

// 导航到各个页面
const goToCategories = () => router.push('/categories')
const goToDishes = () => router.push('/dishes')
const goToTables = () => router.push('/tables')
const goToOrders = () => router.push('/orders')

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.dashboard-container {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}

.page-header h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  cursor: pointer;
  transition: transform 0.3s;
}

.stat-card:hover {
  transform: translateY(-5px);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 20px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #333;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

.recent-orders {
  margin-bottom: 30px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.quick-nav {
  margin-top: 30px;
}

.quick-nav h2 {
  margin: 0 0 20px 0;
  font-size: 20px;
  color: #333;
}

.nav-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.nav-card {
  cursor: pointer;
  transition: all 0.3s;
}

.nav-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}

.nav-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 30px 20px;
}

.nav-icon {
  font-size: 48px;
  color: #409eff;
  margin-bottom: 15px;
}

.nav-text {
  font-size: 16px;
  font-weight: 500;
  color: #333;
}
</style>