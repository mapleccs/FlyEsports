import { apiClient } from './client'
import type { UserRole, Permission } from '@/shared/types/auth'

export interface UserPermissionResponse {
  roles: UserRole[]
  permissions: Permission[]
}

export interface RoleInfo {
  id: number
  name: string
  description?: string
  level: number
  is_system: boolean
}

export interface PermissionInfo {
  id: number
  name: string
  description?: string
  resource: string
  action: string
}

export interface SystemStats {
  total_users: number
  active_users: number
  total_teams: number
  total_tournaments: number
  total_matches: number
  system_health: string
}

export const permissionApi = {
  async getUserPermissions(): Promise<UserPermissionResponse> {
    const response = await apiClient.get('/auth/me/permissions')
    return response.data
  },

  async getUserRoles(userId?: number, regionId?: number): Promise<UserRole[]> {
    const params = new URLSearchParams()
    if (regionId) params.append('region_id', regionId.toString())

    const url = userId
      ? `/admin/users/${userId}/roles${params.toString() ? `?${params.toString()}` : ''}`
      : `/auth/me/roles${params.toString() ? `?${params.toString()}` : ''}`

    const response = await apiClient.get(url)
    return response.data
  },

  async getAllRoles(): Promise<RoleInfo[]> {
    const response = await apiClient.get('/admin/roles')
    return response.data
  },

  async getAllPermissions(): Promise<PermissionInfo[]> {
    const response = await apiClient.get('/admin/permissions')
    return response.data
  },

  async getSystemStats(): Promise<SystemStats> {
    const response = await apiClient.get('/admin/system/stats')
    return response.data
  },

  async assignRole(userId: number, roleId: number, regionId?: number): Promise<void> {
    await apiClient.post('/admin/users/roles/assign', {
      user_id: userId,
      role_id: roleId,
      region_id: regionId,
    })
  },

  async revokeRole(userId: number, roleId: number, regionId?: number): Promise<void> {
    await apiClient.post('/admin/users/roles/revoke', {
      user_id: userId,
      role_id: roleId,
      region_id: regionId,
    })
  },

  async checkPermission(permission: string): Promise<boolean> {
    const response = await apiClient.get(`/auth/permissions/check?permission=${permission}`)
    return response.data.has_permission
  },
}
