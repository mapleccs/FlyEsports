import { defineStore } from 'pinia'
import { ref, computed, readonly } from 'vue'
import type { UserRole, Permission, PermissionCheck } from '@/shared/types/auth'

export const usePermissionStore = defineStore('permission', () => {
  const userRoles = ref<UserRole[]>([])
  const userPermissions = ref<Permission[]>([])
  const loading = ref(false)
  const initialized = ref(false)

  const highestRoleLevel = computed(() => {
    if (userRoles.value.length === 0) return 0
    return Math.max(...userRoles.value.map(role => role.level))
  })

  const roleNames = computed(() => userRoles.value.map(role => role.name))
  const permissionNames = computed(() => userPermissions.value.map(perm => perm.name))

  const hasPermission = (permission: string): boolean => {
    return permissionNames.value.includes(permission)
  }

  const hasRole = (roleName: string): boolean => {
    return roleNames.value.includes(roleName)
  }

  const hasMinLevel = (minLevel: number): boolean => {
    return highestRoleLevel.value >= minLevel
  }

  const canManage = (targetRole: string): boolean => {
    const targetRoleObj = userRoles.value.find(role => role.name === targetRole)
    if (!targetRoleObj) return false
    return highestRoleLevel.value > targetRoleObj.level
  }

  const hasAnyRole = (roles: string[]): boolean => {
    return roles.some(role => hasRole(role))
  }

  const hasAnyPermission = (permissions: string[]): boolean => {
    return permissions.some(permission => hasPermission(permission))
  }

  const isSuperAdmin = computed(() => hasRole('超级管理员'))
  const isRegionAdmin = computed(() => hasRole('赛区管理员') || isSuperAdmin.value)
  const isTeamCaptain = computed(() => hasRole('队长') || isRegionAdmin.value)
  const isPlayer = computed(() => hasRole('选手') || hasRole('队员') || isTeamCaptain.value)

  const canAccessAdminPanel = computed(() => isSuperAdmin.value || isRegionAdmin.value)
  const canManageUsers = computed(() => hasPermission('管理用户'))
  const canManageRoles = computed(() => hasPermission('管理角色'))
  const canManageRegion = computed(() => hasPermission('管理赛区'))
  const canCreateTeam = computed(() => hasPermission('创建战队'))
  const canManageTeam = computed(() => hasPermission('管理战队'))
  const canCreateTournament = computed(() => hasPermission('创建赛事'))

  const setRoles = (roles: UserRole[]) => {
    userRoles.value = roles
  }

  const setPermissions = (permissions: Permission[]) => {
    userPermissions.value = permissions
  }

  const updatePermissions = (roles: UserRole[], permissions: Permission[]) => {
    setRoles(roles)
    setPermissions(permissions)
    initialized.value = true
  }

  const clearPermissions = () => {
    userRoles.value = []
    userPermissions.value = []
    initialized.value = false
  }

  const getRegionRoles = (regionId: string | number) => {
    const id = typeof regionId === 'string' ? parseInt(regionId) : regionId
    return userRoles.value.filter(role => role.region_id === id)
  }

  const hasRegionRole = (regionId: string | number, roleName: string): boolean => {
    return getRegionRoles(regionId).some(role => role.name === roleName)
  }

  const getPermissionCheck = (): PermissionCheck => ({
    hasPermission,
    hasRole,
    hasMinLevel,
    canManage,
  })

  return {
    userRoles: readonly(userRoles),
    userPermissions: readonly(userPermissions),
    loading: readonly(loading),
    initialized: readonly(initialized),
    highestRoleLevel,
    roleNames,
    permissionNames,
    hasPermission,
    hasRole,
    hasMinLevel,
    canManage,
    hasAnyRole,
    hasAnyPermission,
    isSuperAdmin,
    isRegionAdmin,
    isTeamCaptain,
    isPlayer,
    canAccessAdminPanel,
    canManageUsers,
    canManageRoles,
    canManageRegion,
    canCreateTeam,
    canManageTeam,
    canCreateTournament,
    setRoles,
    setPermissions,
    updatePermissions,
    clearPermissions,
    getRegionRoles,
    hasRegionRole,
    getPermissionCheck,
  }
})
