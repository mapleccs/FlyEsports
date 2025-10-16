import { defineStore } from 'pinia'
import { ref, computed, readonly } from 'vue'
import type { User, LoginCredentials, RegisterData } from '@/shared/types/auth'
import { authApi } from '@/shared/api/auth'
import { permissionApi } from '@/shared/api/permission'
import { usePermissionStore } from './permission'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('auth_token'))
  const loading = ref(false)

  const isAuthenticated = computed(() => !!token.value && !!user.value)

  const login = async (credentials: LoginCredentials) => {
    loading.value = true
    try {
      const response = await authApi.login(credentials)

      token.value = response.tokens.access_token
      user.value = response.user
      localStorage.setItem('auth_token', response.tokens.access_token)
      localStorage.setItem('refresh_token', response.tokens.refresh_token)

      return response
    } catch (error) {
      throw error
    } finally {
      loading.value = false
    }
  }

  const register = async (data: RegisterData) => {
    loading.value = true
    try {
      const response = await authApi.register(data)
      // 注册成功后用户信息被返回，但需要单独登录获取token
      // 或者注册后自动进行登录
      await login({ email: data.email, password: data.password })
      return response
    } finally {
      loading.value = false
    }
  }

  const logout = () => {
    const permissionStore = usePermissionStore()

    user.value = null
    token.value = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('refresh_token')

    // 清除权限信息
    permissionStore.clearPermissions()
  }

  const getCurrentUser = async () => {
    if (!token.value) return null

    loading.value = true
    try {
      const userData = await authApi.getCurrentUser()
      user.value = userData

      // 同时获取用户权限信息
      await loadUserPermissions()

      return userData
    } catch (error) {
      logout()
      throw error
    } finally {
      loading.value = false
    }
  }

  const loadUserPermissions = async () => {
    const permissionStore = usePermissionStore()

    try {
      // 尝试获取权限信息，如果失败则使用空数组
      const permissionData = await permissionApi.getUserPermissions().catch(() => ({
        roles: [],
        permissions: [],
      }))

      permissionStore.updatePermissions(permissionData.roles, permissionData.permissions)
    } catch (error) {
      console.warn('Failed to load user permissions:', error)
      permissionStore.clearPermissions()
    }
  }

  const initAuth = async () => {
    if (token.value) {
      try {
        await getCurrentUser()
      } catch (error) {
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
    loadUserPermissions,
    initAuth,
  }
})
