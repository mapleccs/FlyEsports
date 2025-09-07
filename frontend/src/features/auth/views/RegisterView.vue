<template>
  <div class="auth-container">
    <a-card class="auth-card">
      <template #title>
        <h2>注册</h2>
      </template>
      <a-form
        :model="form"
        :rules="rules"
        @finish="handleSubmit"
        layout="vertical"
      >
        <a-form-item name="email" label="邮箱">
          <a-input v-model:value="form.email" placeholder="请输入邮箱" />
        </a-form-item>
        <a-form-item name="username" label="用户名">
          <a-input v-model:value="form.username" placeholder="请输入用户名" />
        </a-form-item>
        <a-form-item name="password" label="密码">
          <a-input-password
            v-model:value="form.password"
            placeholder="请输入密码"
          />
        </a-form-item>
        <a-form-item name="confirm_password" label="确认密码">
          <a-input-password
            v-model:value="form.confirm_password"
            placeholder="请再次输入密码"
          />
        </a-form-item>
        <a-form-item>
          <a-button
            type="primary"
            html-type="submit"
            block
            :loading="authStore.loading"
          >
            注册
          </a-button>
        </a-form-item>
      </a-form>
      <div class="auth-links">
        <router-link to="/auth/login">已有账号？立即登录</router-link>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/shared/stores/auth'
import type { RegisterData } from '@/shared/types/auth'
import { message } from 'ant-design-vue'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive<RegisterData>({
  email: '',
  username: '',
  password: '',
  confirm_password: '',
})

const rules = {
  email: [
    { required: true, message: '请输入邮箱' },
    { type: 'email', message: '请输入有效的邮箱地址' },
  ],
  username: [
    { required: true, message: '请输入用户名' },
    { min: 2, message: '用户名至少2位' },
  ],
  password: [
    { required: true, message: '请输入密码' },
    { min: 8, message: '密码至少需要8个字符' },
  ],
  confirm_password: [
    { required: true, message: '请确认密码' },
    {
      validator: (_: any, value: string) => {
        if (value !== form.password) {
          return Promise.reject(new Error('两次输入的密码不一致'))
        }
        return Promise.resolve()
      },
    },
  ],
}

const handleSubmit = async () => {
  try {
    await authStore.register(form)
    message.success('注册成功')
    router.push('/')
  } catch (error) {
    console.error('Register failed:', error)
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

.password-hint {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}
</style>