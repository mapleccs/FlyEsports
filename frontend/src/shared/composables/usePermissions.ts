import { computed, readonly } from 'vue'
import { usePermissionStore } from '@/shared/stores/permission'
import { useAuthStore } from '@/shared/stores/auth'

export function usePermissions() {
  const permissionStore = usePermissionStore()
  const authStore = useAuthStore()

  const isAuthenticated = computed(() => authStore.isAuthenticated)
  const userRoles = computed(() => permissionStore.userRoles)
  const userPermissions = computed(() => permissionStore.userPermissions)
  const highestRoleLevel = computed(() => permissionStore.highestRoleLevel)

  const hasPermission = (permission: string): boolean => {
    if (!isAuthenticated.value) return false
    return permissionStore.hasPermission(permission)
  }

  const hasAnyPermission = (permissions: string[]): boolean => {
    if (!isAuthenticated.value) return false
    return permissionStore.hasAnyPermission(permissions)
  }

  const hasAllPermissions = (permissions: string[]): boolean => {
    if (!isAuthenticated.value) return false
    return permissions.every(permission => permissionStore.hasPermission(permission))
  }

  const hasRole = (roleName: string): boolean => {
    if (!isAuthenticated.value) return false
    return permissionStore.hasRole(roleName)
  }

  const hasAnyRole = (roles: string[]): boolean => {
    if (!isAuthenticated.value) return false
    return permissionStore.hasAnyRole(roles)
  }

  const hasMinLevel = (minLevel: number): boolean => {
    if (!isAuthenticated.value) return false
    return permissionStore.hasMinLevel(minLevel)
  }

  const canManage = (targetRole: string): boolean => {
    if (!isAuthenticated.value) return false
    return permissionStore.canManage(targetRole)
  }

  const hasRegionRole = (regionId: number, roleName: string): boolean => {
    if (!isAuthenticated.value) return false
    return permissionStore.hasRegionRole(regionId, roleName)
  }

  const isSuperAdmin = computed(() => permissionStore.isSuperAdmin)
  const isRegionAdmin = computed(() => permissionStore.isRegionAdmin)
  const isTeamCaptain = computed(() => permissionStore.isTeamCaptain)
  const isPlayer = computed(() => permissionStore.isPlayer)

  const canAccessAdminPanel = computed(() => permissionStore.canAccessAdminPanel)
  const canManageUsers = computed(() => permissionStore.canManageUsers)
  const canManageRoles = computed(() => permissionStore.canManageRoles)
  const canManageRegion = computed(() => permissionStore.canManageRegion)
  const canCreateTeam = computed(() => permissionStore.canCreateTeam)
  const canManageTeam = computed(() => permissionStore.canManageTeam)
  const canCreateTournament = computed(() => permissionStore.canCreateTournament)

  const getPermissionCheck = () => permissionStore.getPermissionCheck()

  const requirePermission = (permission: string): boolean => {
    if (!hasPermission(permission)) {
      throw new Error(`权限不足，需要权限：${permission}`)
    }
    return true
  }

  const requireRole = (roleName: string): boolean => {
    if (!hasRole(roleName)) {
      throw new Error(`权限不足，需要角色：${roleName}`)
    }
    return true
  }

  const requireMinLevel = (minLevel: number): boolean => {
    if (!hasMinLevel(minLevel)) {
      throw new Error(`权限不足，需要最低级别：${minLevel}`)
    }
    return true
  }

  return {
    isAuthenticated: readonly(isAuthenticated),
    userRoles: readonly(userRoles),
    userPermissions: readonly(userPermissions),
    highestRoleLevel: readonly(highestRoleLevel),
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    hasRole,
    hasAnyRole,
    hasMinLevel,
    canManage,
    hasRegionRole,
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
    getPermissionCheck,
    requirePermission,
    requireRole,
    requireMinLevel,
  }
}

export function useAuthGuard() {
  const { hasPermission, hasRole, hasMinLevel, canAccessAdminPanel, isAuthenticated } =
    usePermissions()

  const guardRoute = (requirements: {
    permissions?: string[]
    roles?: string[]
    minLevel?: number
    requireAuth?: boolean
    requireAdmin?: boolean
  }) => {
    const { permissions, roles, minLevel, requireAuth = false, requireAdmin = false } = requirements

    if (requireAuth && !isAuthenticated.value) {
      return { allowed: false, reason: '需要登录' }
    }

    if (requireAdmin && !canAccessAdminPanel.value) {
      return { allowed: false, reason: '需要管理员权限' }
    }

    if (permissions && !permissions.some(p => hasPermission(p))) {
      return { allowed: false, reason: `需要权限：${permissions.join(' 或 ')}` }
    }

    if (roles && !roles.some(r => hasRole(r))) {
      return { allowed: false, reason: `需要角色：${roles.join(' 或 ')}` }
    }

    if (minLevel && !hasMinLevel(minLevel)) {
      return { allowed: false, reason: `需要最低权限级别：${minLevel}` }
    }

    return { allowed: true }
  }

  return {
    guardRoute,
    hasPermission,
    hasRole,
    hasMinLevel,
    canAccessAdminPanel,
    isAuthenticated,
  }
}
