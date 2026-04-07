<template>
  <div class="order-manager">
    <div class="page-header">
      <h1>订单管理</h1>
      <el-button type="primary" @click="loadOrders">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <!-- 状态 Tabs -->
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <el-tab-pane label="全部" name="all" />
      <el-tab-pane label="待付款" name="pending_payment" />
      <el-tab-pane label="待接单" name="pending" />
      <el-tab-pane label="已接单" name="confirmed" />
      <el-tab-pane label="已结账" name="paid" />
      <el-tab-pane label="已取消" name="cancelled" />
    </el-tabs>

    <!-- 订单列表 -->
    <el-table
      :data="orders"
      v-loading="loading"
      :expand-row-keys="expandedRows"
      row-key="id"
      @row-click="toggleExpand"
      style="width: 100%"
    >
      <el-table-column type="expand" width="50">
        <template #default="{ row }">
          <div class="order-detail" v-if="expandedRows.includes(row.id)">
            <div class="detail-header">
              <h4>订单详情 #{{ row.order_number }}</h4>
              <el-button type="primary" size="small" @click.stop="printTicket(row)">
                <el-icon><Printer /></el-icon>
                打印小票
              </el-button>
            </div>

            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="订单号">{{ row.order_number }}</el-descriptions-item>
              <el-descriptions-item label="桌台">{{ row.table?.name || row.table_id }}</el-descriptions-item>
              <el-descriptions-item label="总金额">¥{{ row.total_amount?.toFixed(2) }}</el-descriptions-item>
              <el-descriptions-item label="订单状态">
                <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="下单时间">{{ formatDateTime(row.created_at) }}</el-descriptions-item>
              <el-descriptions-item label="备注" v-if="row.remark">{{ row.remark }}</el-descriptions-item>
            </el-descriptions>

            <div class="dish-list">
              <h5>菜品明细</h5>
              <el-table :data="row.items || []" size="small" border>
                <el-table-column prop="dish_name" label="菜品名称" />
                <el-table-column prop="unit_price" label="单价" width="100">
                  <template #default="{ col }">¥{{ col.row.unit_price?.toFixed(2) }}</template>
                </el-table-column>
                <el-table-column prop="quantity" label="数量" width="80" />
                <el-table-column label="小计" width="100">
                  <template #default="{ col }">¥{{ col.row.subtotal?.toFixed(2) }}</template>
                </el-table-column>
                <el-table-column prop="note" label="备注" v-if="row.items?.some((i: OrderItem) => i.note)" />
              </el-table>
            </div>

            <!-- 操作按钮（pending_payment 状态不显示接单/结账按钮，仅可取消） -->
            <div class="detail-actions" v-if="row.status === 'pending' || row.status === 'confirmed' || row.status === 'pending_payment'">
              <el-button
                v-if="row.status === 'pending'"
                type="success"
                :disabled="actionLoading"
                @click.stop="handleStatusUpdate(row, 'confirmed')"
              >
                接单
              </el-button>
              <el-button
                v-if="row.status === 'confirmed'"
                type="warning"
                :disabled="actionLoading"
                @click.stop="handleStatusUpdate(row, 'paid')"
              >
                结账
              </el-button>
              <el-button
                type="danger"
                :disabled="actionLoading"
                @click.stop="handleStatusUpdate(row, 'cancelled')"
              >
                取消订单
              </el-button>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="order_number" label="订单号" width="200" />
      <el-table-column label="桌台" width="120">
        <template #default="{ row }">{{ row.table?.name || row.table_id }}</template>
      </el-table-column>
      <el-table-column prop="total_amount" label="金额" width="120">
        <template #default="{ row }">¥{{ row.total_amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <!-- Phase 2: 支付方式列 -->
      <el-table-column label="支付方式" width="100">
        <template #default="{ row }">
          <span>{{ getPaymentModeText(row.payment_mode) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="下单时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button type="primary" size="small" @click.stop="printTicket(row)">
            小票
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadOrders"
        @current-change="loadOrders"
      />
    </div>

    <!-- 小票预览 Dialog -->
    <el-dialog v-model="ticketDialogVisible" title="小票预览" width="400px">
      <div class="ticket-preview" v-if="ticketData">
        <div class="ticket-header">
          <h3>结账单</h3>
          <p>桌号：{{ ticketData.table?.name || ticketData.table_id }}</p>
          <p>订单号：{{ ticketData.order_number }}</p>
          <p>时间：{{ formatDateTime(ticketData.created_at) }}</p>
        </div>
        <el-divider />
        <div class="ticket-items">
          <div class="ticket-item header">
            <span>菜品</span>
            <span>单价</span>
            <span>数量</span>
            <span>小计</span>
          </div>
          <div class="ticket-item" v-for="item in ticketData.items" :key="item.id">
            <span>{{ item.dish_name }}</span>
            <span>¥{{ item.unit_price?.toFixed(2) }}</span>
            <span>{{ item.quantity }}</span>
            <span>¥{{ item.subtotal?.toFixed(2) }}</span>
          </div>
        </div>
        <el-divider />
        <div class="ticket-total">
          <span>合计：</span>
          <span class="total-amount">¥{{ ticketData.total_amount?.toFixed(2) }}</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="ticketDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="handlePrint">打印</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Printer } from '@element-plus/icons-vue'
import { orderApi } from '@/services/api'

// 订单项
interface OrderItem {
  id: number
  order_id: number
  dish_id: number
  dish_name: string
  unit_price: number
  quantity: number
  subtotal: number
  note: string | null
  created_at: string
}

// 桌台信息
interface TableInfo {
  id: number
  name: string
  code: string
}

// 订单
interface Order {
  id: number
  merchant_id: number
  order_number: string
  table_id: number
  table?: TableInfo
  customer_name: string | null
  customer_phone: string | null
  remark: string | null
  status: string
  total_amount: number
  created_at: string
  updated_at: string
  payment_mode?: string
  paid_at?: string | null
  items: OrderItem[]
}

const loading = ref(false)
const actionLoading = ref(false)
const orders = ref<Order[]>([])
const activeTab = ref('all')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const expandedRows = ref<number[]>([])
const ticketDialogVisible = ref(false)
const ticketData = ref<Order | null>(null)

const statusMap: Record<string, string> = {
  pending: 'warning',
  pending_payment: 'warning',
  confirmed: 'primary',
  paid: 'success',
  cancelled: 'danger'
}

const statusTextMap: Record<string, string> = {
  pending: '待接单',
  pending_payment: '待付款',
  confirmed: '已接单',
  paid: '已结账',
  cancelled: '已取消'
}

// 状态流转规则：pending -> confirmed -> paid, pending/confirmed -> cancelled
const validTransitions: Record<string, string[]> = {
  pending: ['confirmed', 'cancelled'],
  pending_payment: ['cancelled'],  // counter_pay: 待付款状态只能取消
  confirmed: ['paid', 'cancelled'],
  paid: [],
  cancelled: []
}

const getStatusType = (status: string) => statusMap[status] || 'info'
const getStatusText = (status: string) => statusTextMap[status] || status

// Phase 2: 支付方式文字
const getPaymentModeText = (mode?: string) => {
  if (!mode) return '-'
  return mode === 'counter_pay' ? '柜台付款' : '挂账'
}

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const getStatusParam = () => {
  return activeTab.value === 'all' ? undefined : activeTab.value
}

const loadOrders = async () => {
  loading.value = true
  try {
    const response = await orderApi.getOrders({
      status: getStatusParam(),
      page: currentPage.value,
      limit: pageSize.value
    })
    
    // 正确处理 API 返回结构：{total, page, limit, orders: [...]}
    if (response.data) {
      orders.value = response.data.orders || []
      total.value = response.data.total || 0
    }
  } catch (error: any) {
    console.error('加载订单失败:', error)
    ElMessage.error(error?.response?.data?.detail || '加载订单失败')
  } finally {
    loading.value = false
  }
}

const onTabChange = () => {
  currentPage.value = 1
  expandedRows.value = []
  loadOrders()
}

const toggleExpand = (row: Order) => {
  const idx = expandedRows.value.indexOf(row.id)
  if (idx >= 0) {
    expandedRows.value.splice(idx, 1)
  } else {
    expandedRows.value.push(row.id)
    // 如果没有菜品数据，尝试加载详情
    if (!row.items || row.items.length === 0) {
      loadOrderDetail(row.id)
    }
  }
}

const loadOrderDetail = async (orderId: number) => {
  try {
    const response = await orderApi.getOrder(orderId)
    if (response.data) {
      const order = orders.value.find(o => o.id === orderId)
      if (order) {
        order.items = response.data.items || []
        order.table = response.data.table
      }
    }
  } catch (error) {
    console.error('加载订单详情失败:', error)
  }
}

const handleStatusUpdate = async (order: Order, newStatus: string) => {
  // 状态流转校验
  const allowedTransitions = validTransitions[order.status] || []
  if (!allowedTransitions.includes(newStatus)) {
    ElMessage.error(`无法将订单从"${getStatusText(order.status)}"变更为"${getStatusText(newStatus)}"`)
    return
  }

  const actionText = newStatus === 'confirmed' ? '接单' : newStatus === 'paid' ? '结账' : '取消'
  try {
    await ElMessageBox.confirm(`确定要${actionText}吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }

  actionLoading.value = true
  try {
    await orderApi.updateOrderStatus(order.id, newStatus)
    ElMessage.success(`${actionText}成功`)
    // 刷新订单，保持当前展开状态
    await loadOrders()
    // 重新设置展开行
    expandedRows.value = expandedRows.value.filter(id => orders.value.some(o => o.id === id))
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || `${actionText}失败`)
  } finally {
    actionLoading.value = false
  }
}

const printTicket = async (order: Order) => {
  // 如果已经有完整数据，直接显示
  if (order.items && order.items.length > 0) {
    ticketData.value = order
    ticketDialogVisible.value = true
    return
  }
  
  // 否则尝试获取详情
  try {
    const response = await orderApi.getOrder(order.id)
    if (response.data) {
      ticketData.value = response.data
    } else {
      ticketData.value = order
    }
  } catch {
    ticketData.value = order
  }
  ticketDialogVisible.value = true
}

const handlePrint = () => {
  window.print()
  ticketDialogVisible.value = false
}

onMounted(() => {
  loadOrders()
})
</script>

<style scoped>
.order-manager {
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

.order-detail {
  padding: 15px 20px;
  background: #f5f7fa;
  border-radius: 4px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.detail-header h4 {
  margin: 0;
  color: #333;
}

.dish-list {
  margin-top: 15px;
}

.dish-list h5 {
  margin: 0 0 10px 0;
  color: #666;
}

.detail-actions {
  margin-top: 15px;
  display: flex;
  gap: 10px;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

/* 小票样式 */
.ticket-preview {
  font-family: 'Courier New', monospace;
  font-size: 14px;
  padding: 10px;
}

.ticket-header {
  text-align: center;
  margin-bottom: 10px;
}

.ticket-header h3 {
  margin: 0 0 10px 0;
  font-size: 18px;
}

.ticket-header p {
  margin: 3px 0;
}

.ticket-items {
  margin: 10px 0;
}

.ticket-item {
  display: grid;
  grid-template-columns: 1fr 60px 50px 70px;
  gap: 5px;
  padding: 4px 0;
}

.ticket-item.header {
  font-weight: bold;
  border-bottom: 1px dashed #999;
  padding-bottom: 5px;
  margin-bottom: 5px;
}

.ticket-total {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  font-size: 16px;
}

.total-amount {
  font-weight: bold;
  font-size: 18px;
  color: #f56c6c;
  margin-left: 10px;
}

@media print {
  .ticket-preview {
    width: 80mm;
    margin: 0 auto;
  }
}
</style>
