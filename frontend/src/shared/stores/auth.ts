import { defineStore } from 'pinia'
import { ref, computed, readonly } from 'vue'
import type { User, LoginCredentials, RegisterData } from '@/shared/types/auth'
import { authApi } from '@/shared/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('auth_token'))
  const loading = ref(false)

  const isAuthenticated = computed(() => !!token.value && !!user.value)

  const login = async (credentials: LoginCredentials) => {
    loading.value = true
    try {
      const response = await authApi.login(credentials)
      token.value = response.access_token
      user.value = response.user
      localStorage.setItem('auth_token', response.access_token)
      return response
    } finally {
      loading.value = false
    }
  }

  const register = async (data: RegisterData) => {
    loading.value = true
    try {
      const response = await authApi.register(data)
      token.value = response.access_token
      user.value = response.user
      localStorage.setItem('auth_token', response.access_token)
      return response
    } finally {
      loading.value = false
    }
  }

  const logout = () => {
    user.value = null
    token.value = null
    localStorage.removeItem('auth_token')
  }

  const getCurrentUser = async () => {
    if (!token.value) return null
    
    loading.value = true
    try {
      const userData = await authApi.getCurrentUser()
      user.value = userData
      return userData
    } catch (error) {
      logout()
      throw error
    } finally {
      loading.value = false
    }
  }

  const initAuth = async () => {
    if (token.value) {
      try {
        await getCurrentUser()
      } catch (error) {
        console.warn('Failed to initialize auth:', error)
        logout()
      }
    }
  }

  return {
    user: readonly(user),
    token: readonly(token),
    loading: readonly(loading),
    isAuthenticated,
    login,
    register,
    logout,
    getCurrentUser,
    initAuth,
  }
})