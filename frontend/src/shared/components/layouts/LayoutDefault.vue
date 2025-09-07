<template>
  <a-layout class="layout">
    <a-layout-header class="header">
      <div class="header-content">
        <div class="logo">
          <router-link to="/">
            <h1>FlyEsports</h1>
          </router-link>
        </div>
        <!-- 桌面端导航菜单 -->
        <a-menu
          v-model:selectedKeys="selectedKeys"
          theme="dark"
          mode="horizontal"
          class="nav-menu desktop-nav"
          @click="handleMenuClick"
        >
          <a-menu-item key="home">主页</a-menu-item>
          <a-sub-menu key="events" title="赛事中心">
            <a-menu-item key="tournaments">赛事管理</a-menu-item>
            <a-menu-item key="schedule">赛程安排</a-menu-item>
            <a-menu-item key="live">直播中心</a-menu-item>
          </a-sub-menu>
          <a-menu-item key="teams" v-if="authStore.isAuthenticated">战队</a-menu-item>
          <a-sub-menu key="players" title="选手中心">
            <a-menu-item key="players-list">选手池</a-menu-item>
            <a-menu-item key="recruitment">招募专区</a-menu-item>
          </a-sub-menu>
          <a-menu-item key="hall" v-if="authStore.isAuthenticated">比赛大厅</a-menu-item>
        </a-menu>

        <!-- 移动端汉堡菜单 -->
        <div class="mobile-nav">
          <a-button type="text" @click="mobileMenuVisible = !mobileMenuVisible" class="mobile-menu-btn">
            <MenuOutlined style="color: white; font-size: 18px;" />
          </a-button>
        </div>
        <div class="header-actions">
          <div v-if="authStore.isAuthenticated" class="user-info">
            <a-dropdown>
              <a @click.prevent>
                <a-space>
                  <a-avatar :src="authStore.user?.avatar">
                    {{ authStore.user?.username?.charAt(0).toUpperCase() }}
                  </a-avatar>
                  {{ authStore.user?.username }}
                </a-space>
              </a>
              <template #overlay>
                <a-menu @click="handleUserMenuClick">
                  <a-menu-item key="profile">个人中心</a-menu-item>
                  <a-menu-divider />
                  <a-menu-item key="logout">退出登录</a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </div>
          <div v-else class="auth-buttons">
            <a-space>
              <a-button @click="$router.push('/auth/login')">登录</a-button>
              <a-button type="primary" @click="$router.push('/auth/register')">注册</a-button>
            </a-space>
          </div>
        </div>
      </div>
    </a-layout-header>
    <a-layout-content class="content">
      <slot />
    </a-layout-content>
    <a-layout-footer class="footer">
      <div class="footer-content">
        FlyEsports © 2024 - 专业电竞赛事管理平台
      </div>
    </a-layout-footer>

    <!-- 移动端抽屉菜单 -->
    <a-drawer
      v-model:open="mobileMenuVisible"
      title="导航菜单"
      placement="left"
      :width="280"
      :body-style="{ padding: 0 }"
      class="mobile-drawer"
    >
      <a-menu
        v-model:selectedKeys="selectedKeys"
        mode="inline"
        class="mobile-menu"
        @click="handleMobileMenuClick"
      >
        <a-menu-item key="home">
          <HomeOutlined />
          主页
        </a-menu-item>
        
        <a-sub-menu key="events" title="赛事中心">
          <template #icon><CalendarOutlined /></template>
          <a-menu-item key="tournaments">赛事管理</a-menu-item>
          <a-menu-item key="schedule">赛程安排</a-menu-item>
          <a-menu-item key="live">直播中心</a-menu-item>
        </a-sub-menu>
        
        <a-menu-item key="teams" v-if="authStore.isAuthenticated">
          <TeamOutlined />
          战队
        </a-menu-item>
        
        <a-sub-menu key="players" title="选手中心">
          <template #icon><UserOutlined /></template>
          <a-menu-item key="players-list">选手池</a-menu-item>
          <a-menu-item key="recruitment">招募专区</a-menu-item>
        </a-sub-menu>
        
        <a-menu-item key="hall" v-if="authStore.isAuthenticated">
          <TrophyOutlined />
          比赛大厅
        </a-menu-item>
        
        <a-menu-divider />
        
        <!-- 用户相关菜单项 -->
        <template v-if="authStore.isAuthenticated">
          <a-menu-item key="profile">
            <UserOutlined />
            个人中心
          </a-menu-item>
          <a-menu-item key="logout">
            <LogoutOutlined />
            退出登录
          </a-menu-item>
        </template>
        <template v-else>
          <a-menu-item key="login">
            <LoginOutlined />
            登录
          </a-menu-item>
          <a-menu-item key="register">
            <UserAddOutlined />
            注册
          </a-menu-item>
        </template>
      </a-menu>
    </a-drawer>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/shared/stores/auth'
import { message } from 'ant-design-vue'
import {
  MenuOutlined,
  HomeOutlined,
  CalendarOutlined,
  TeamOutlined,
  UserOutlined,
  TrophyOutlined,
  LogoutOutlined,
  LoginOutlined,
  UserAddOutlined
} from '@ant-design/icons-vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const selectedKeys = ref<string[]>([])
const mobileMenuVisible = ref(false)

const handleMenuClick = ({ key }: { key: string }) => {
  switch (key) {
    case 'home':
      router.push('/')
      break
    case 'tournaments':
      router.push('/tournaments')
      break
    case 'schedule':
      router.push('/schedule')
      break
    case 'live':
      router.push('/live')
      break
    case 'teams':
      router.push('/teams')
      break
    case 'players-list':
      router.push('/players')
      break
    case 'recruitment':
      router.push('/recruitment')
      break
    case 'hall':
      router.push('/hall')
      break
  }
}

const handleMobileMenuClick = ({ key }: { key: string }) => {
  mobileMenuVisible.value = false // 关闭抽屉
  
  // 处理用户相关菜单项
  if (key === 'profile') {
    router.push(`/players/${authStore.user?.id}`)
    return
  }
  if (key === 'logout') {
    authStore.logout()
    message.success('已成功退出登录')
    router.push('/')
    return
  }
  if (key === 'login') {
    router.push('/auth/login')
    return
  }
  if (key === 'register') {
    router.push('/auth/register')
    return
  }
  
  // 其他菜单项复用桌面端处理逻辑
  handleMenuClick({ key })
}

const handleUserMenuClick = ({ key }: { key: string }) => {
  switch (key) {
    case 'profile':
      router.push(`/players/${authStore.user?.id}`)
      break
    case 'logout':
      authStore.logout()
      message.success('已成功退出登录')
      router.push('/')
      break
  }
}

watch(
  () => route.path,
  (path) => {
    if (path === '/') {
      selectedKeys.value = ['home']
    } else if (path.startsWith('/tournaments')) {
      selectedKeys.value = ['tournaments']
    } else if (path.startsWith('/schedule')) {
      selectedKeys.value = ['schedule']
    } else if (path.startsWith('/live')) {
      selectedKeys.value = ['live']
    } else if (path.startsWith('/teams')) {
      selectedKeys.value = ['teams']
    } else if (path.startsWith('/players') && !path.startsWith('/players/')) {
      selectedKeys.value = ['players-list']
    } else if (path.startsWith('/recruitment')) {
      selectedKeys.value = ['recruitment']
    } else if (path.startsWith('/hall')) {
      selectedKeys.value = ['hall']
    } else {
      selectedKeys.value = []
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.layout {
  min-height: 100vh;
}

.header {
  position: sticky;
  top: 0;
  z-index: 1000;
}

.header-content {
  display: flex;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
  height: 100%;
}

.logo {
  margin-right: 32px;
}

.logo a {
  color: white;
  text-decoration: none;
}

.logo h1 {
  color: white;
  margin: 0;
  font-size: 24px;
  font-weight: bold;
}

.nav-menu {
  flex: 1;
  background: transparent;
}

.header-actions {
  margin-left: auto;
}

.user-info a {
  color: white;
}

.content {
  background: #f0f2f5;
}

.footer {
  text-align: center;
  background: #001529;
  color: white;
}

.footer-content {
  max-width: 1200px;
  margin: 0 auto;
}

/* 响应式设计 */
.mobile-nav {
  display: none;
}

.mobile-menu-btn {
  padding: 0 !important;
  height: auto !important;
  border: none !important;
}

.mobile-drawer :deep(.ant-drawer-header) {
  background: #001529;
  color: white;
}

.mobile-drawer :deep(.ant-drawer-title) {
  color: white;
}

.mobile-menu {
  border-right: none;
}

/* 移动端样式 */
@media (max-width: 768px) {
  .desktop-nav {
    display: none !important;
  }
  
  .mobile-nav {
    display: block;
  }
  
  .header-content {
    padding: 0 16px;
  }
  
  .logo h1 {
    font-size: 18px;
  }
  
  .header-actions .auth-buttons {
    display: none; /* 移动端隐藏登录注册按钮，在抽屉菜单中显示 */
  }
  
  .user-info {
    margin-left: 8px;
  }
  
  .user-info a {
    font-size: 14px;
  }
}

/* 平板端适配 */
@media (max-width: 992px) and (min-width: 769px) {
  .header-content {
    padding: 0 16px;
  }
  
  .logo h1 {
    font-size: 20px;
  }
  
  .nav-menu {
    font-size: 14px;
  }
}

/* 小屏幕设备进一步优化 */
@media (max-width: 480px) {
  .header-content {
    padding: 0 12px;
  }
  
  .logo {
    margin-right: 12px;
  }
  
  .logo h1 {
    font-size: 16px;
  }
  
  .mobile-drawer {
    width: 100% !important;
  }
  
  .mobile-drawer :deep(.ant-drawer-content-wrapper) {
    width: 280px !important;
  }
}

/* 超大屏幕优化 */
@media (min-width: 1400px) {
  .header-content {
    max-width: 1400px;
  }
  
  .footer-content {
    max-width: 1400px;
  }
}
</style>