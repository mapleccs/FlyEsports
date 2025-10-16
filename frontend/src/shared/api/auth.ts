import { apiClient } from './client'
import type { LoginCredentials, RegisterData, LoginResponse, User } from '@/shared/types/auth'

export const authApi = {
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    const response = await apiClient.post('/auth/login', credentials)
    return response.data
  },

  async register(data: RegisterData): Promise<User> {
    const response = await apiClient.post('/auth/register', data)
    return response.data
  },

  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get('/auth/me')
    return response.data
  },

  async logout(): Promise<void> {
    await apiClient.post('/auth/logout')
  },
}
