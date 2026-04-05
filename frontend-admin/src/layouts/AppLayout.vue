<template>
  <el-container class="app-layout">
    <!-- 左侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="sidebar">
      <!-- Logo 区域 -->
      <div class="sidebar-logo">
        <span v-if="!isCollapse" class="logo-text">龙虾小兵</span>
        <el-icon v-else class="collapse-icon"><Food /></el-icon>
      </div>

      <!-- 导航菜单 -->
      <el-menu
        :default-active="activeMenu"
        class="sidebar-menu"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
      >
        <el-menu-item index="/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <template #title>Dashboard</template>
        </el-menu-item>

        <el-menu-item index="/categories">
          <el-icon><Collection /></el-icon>
          <template #title>分类管理</template>
        </el-menu-item>

        <el-menu-item index="/dishes">
          <el-icon><Food /></el-icon>
          <template #title>菜品管理</template>
        </el-menu-item>

        <el-menu-item index="/tables">
          <el-icon><Grid /></el-icon>
          <template #title>桌台管理</template>
        </el-menu-item>

        <el-menu-item index="/orders">
          <el-icon><List /></el-icon>
          <template #title>订单管理</template>
        </el-menu-item>

        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <template #title>商户设置</template>
        </el-menu-item>
      </el-menu>

      <!-- 折叠按钮 -->
      <div class="sidebar-footer">
        <div class="collapse-btn" @click="toggleCollapse">
          <el-icon :size="18">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          <span v-if="!isCollapse">收起</span>
        </div>
      </div>
    </el-aside>

    <!-- 右侧主内容区 -->
    <el-container class="main-container">
      <!-- 顶部导航栏 -->
      <el-header class="main-header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="routeNameMap[route.name as string] && route.name !== 'dashboard'">
              {{ currentRouteNameCN }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <!-- 返回首页 -->
          <el-button type="primary" text @click="goHome">
            <el-icon><HomeFilled /></el-icon>
            返回首页
          </el-button>

          <!-- 商户信息 -->
          <div class="merchant-info">
            <el-icon><User /></el-icon>
            <span>{{ merchantName || '商户用户' }}</span>
          </div>

          <!-- 退出登录 -->
          <el-button type="danger" @click="handleLogout">
            <el-icon><SwitchButton /></el-icon>
            退出登录
          </el-button>
        </div>
      </el-header>

      <!-- 内容区域 -->
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import {
  HomeFilled,
  Collection,
  Food,
  Grid,
  List,
  Setting,
  Fold,
  Expand,
  SwitchButton,
  User
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const isCollapse = ref(false)
const merchantName = ref(localStorage.getItem('merchant_name') || '')

// 当前激活菜单
const activeMenu = computed(() => route.path)

// 当前路由名称（中文）
const routeNameMap: Record<string, string> = {
  dashboard: 'Dashboard',
  categories: '分类管理',
  dishes: '菜品管理',
  tables: '桌台管理',
  orders: '订单管理',
  settings: '商户设置'
}

const currentRouteNameCN = computed(() => {
  const name = route.name as string
  return routeNameMap[name] || ''
})

// 切换折叠状态
const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

// 返回首页
const goHome = () => {
  router.push('/dashboard')
}

// 退出登录
const handleLogout = () => {
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  })
    .then(() => {
      authStore.logout()
      ElMessage.success('已退出登录')
    })
    .catch(() => {})
}
</script>

<style scoped>
.app-layout {
  height: 100vh;
  overflow: hidden;
}

/* 侧边栏 */
.sidebar {
  background: linear-gradient(180deg, #304156 0%, #1c2433 100%);
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  overflow: hidden;
}

.sidebar-logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 0 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-icon {
  width: 28px;
  height: 28px;
}

.logo-text {
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  white-space: nowrap;
}

.collapse-icon {
  color: #409eff;
  font-size: 24px;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  background: transparent;
}

.sidebar-menu:not(.el-menu--collapse) {
  width: 220px;
}

.sidebar-menu .el-menu-item {
  height: 56px;
  line-height: 56px;
  color: #bfcbd9;
  margin: 4px 8px;
  border-radius: 8px;
  transition: all 0.3s;
}

.sidebar-menu .el-menu-item:hover {
  background: rgba(255, 255, 255, 0.08) !important;
  color: #fff;
}

.sidebar-menu .el-menu-item.is-active {
  background: #409eff !important;
  color: #fff !important;
}

.sidebar-menu .el-menu-item .el-icon {
  font-size: 18px;
  margin-right: 8px;
}

.sidebar-footer {
  padding: 12px 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.collapse-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  color: #bfcbd9;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.3s;
  font-size: 14px;
}

.collapse-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

/* 主内容区 */
.main-container {
  background: #f0f2f5;
  flex-direction: column;
}

.main-header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  height: 60px;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.merchant-info {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #606266;
  font-size: 14px;
  padding: 0 12px;
  background: #f5f7fa;
  border-radius: 4px;
  height: 36px;
}

.main-content {
  padding: 20px;
  overflow-y: auto;
  height: calc(100vh - 60px);
}

/* 路由切换动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
