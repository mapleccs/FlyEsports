<template>
  <a-config-provider :locale="zhCN">
    <div id="app">
      <router-view />
    </div>
  </a-config-provider>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/shared/stores/auth'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import dayjs from 'dayjs'

const authStore = useAuthStore()

onMounted(async () => {
  console.log('FlyEsports App Initialized')
  console.log('Dayjs配置状态检查:', {
    currentTime: dayjs().format('YYYY-MM-DD HH:mm:ss'),
    isWorking: true,
  })

  // 在Vue完全挂载后初始化认证状态
  await authStore.initAuth()
  console.log('Auth initialized')
})
</script>

<style>
#app {
  font-family:
    -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans',
    sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji';
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
