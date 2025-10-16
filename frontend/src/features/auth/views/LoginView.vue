<template>
  <div class="auth-container">
    <a-card class="auth-card">
      <template #title>
        <h2>登录</h2>
      </template>
      <a-form :model="form" :rules="rules" @finish="handleSubmit" layout="vertical">
        <a-form-item name="email" label="邮箱">
          <a-input v-model:value="form.email" placeholder="请输入邮箱" />
        </a-form-item>
        <a-form-item name="password" label="密码">
          <a-input-password v-model:value="form.password" placeholder="请输入密码" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" block :loading="authStore.loading">
            登录
          </a-button>
        </a-form-item>
      </a-form>
      <div class="auth-links">
        <router-link to="/auth/register">还没有账号？立即注册</router-link>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/shared/stores/auth'
import type { LoginCredentials } from '@/shared/types/auth'
import { message } from 'ant-design-vue'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive<LoginCredentials>({
  email: '',
  password: '',
})

const rules = {
  email: [
    { required: true, message: '请输入邮箱' },
    { type: 'email', message: '请输入有效的邮箱地址' },
  ],
  password: [
    { required: true, message: '请输入密码' },
    { min: 6, message: '密码至少6位' },
  ],
}

const handleSubmit = async () => {
  try {
    await authStore.login(form)
    message.success('登录成功')
    router.push('/')
  } catch (error) {
    console.error('Login failed:', error)
  }
}
</script>

<style scoped>
.auth-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: #f0f2f5;
}

.auth-card {
  width: 400px;
}

.auth-links {
  text-align: center;
  margin-top: 16px;
}
</style>
