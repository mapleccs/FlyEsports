import type { DirectiveBinding, VNode } from 'vue'
import { usePermissionStore } from '@/shared/stores/permission'
import { useAuthStore } from '@/shared/stores/auth'

interface PermissionBinding {
  permissions?: string | string[]
  roles?: string | string[]
  minLevel?: number
  requireAuth?: boolean
  requireAdmin?: boolean
  any?: boolean // 是否满足任一条件即可，默认false（需满足所有条件）
}

function checkPermission(binding: PermissionBinding): boolean {
  const permissionStore = usePermissionStore()
  const authStore = useAuthStore()

  // 如果需要认证但未登录
  if (binding.requireAuth && !authStore.isAuthenticated) {
    return false
  }

  // 如果需要管理员权限但不是管理员
  if (binding.requireAdmin && !permissionStore.canAccessAdminPanel) {
    return false
  }

  const conditions: boolean[] = []

  // 权限检查
  if (binding.permissions) {
    const permissions = Array.isArray(binding.permissions)
      ? binding.permissions
      : [binding.permissions]

    if (binding.any) {
      conditions.push(permissionStore.hasAnyPermission(permissions))
    } else {
      conditions.push(permissions.every(p => permissionStore.hasPermission(p)))
    }
  }

  // 角色检查
  if (binding.roles) {
    const roles = Array.isArray(binding.roles) ? binding.roles : [binding.roles]

    if (binding.any) {
      conditions.push(permissionStore.hasAnyRole(roles))
    } else {
      conditions.push(roles.every(r => permissionStore.hasRole(r)))
    }
  }

  // 级别检查
  if (binding.minLevel !== undefined) {
    conditions.push(permissionStore.hasMinLevel(binding.minLevel))
  }

  // 如果没有设置任何条件，则默认显示
  if (conditions.length === 0) {
    return true
  }

  // 根据any参数决定是满足任一条件还是所有条件
  return binding.any
    ? conditions.some(condition => condition)
    : conditions.every(condition => condition)
}

function updateElement(el: HTMLElement, binding: DirectiveBinding<PermissionBinding>) {
  const hasPermission = checkPermission(binding.value || {})

  if (hasPermission) {
    el.style.display = ''
    el.style.visibility = ''
  } else {
    el.style.display = 'none'
  }
}

export const vPermission = {
  mounted(el: HTMLElement, binding: DirectiveBinding<PermissionBinding>) {
    updateElement(el, binding)
  },

  updated(el: HTMLElement, binding: DirectiveBinding<PermissionBinding>) {
    updateElement(el, binding)
  },
}

// 简化版本的指令，用于基于角色的简单显示控制
export const vRole = {
  mounted(el: HTMLElement, binding: DirectiveBinding<string | string[]>) {
    const permissionStore = usePermissionStore()
    const roles = Array.isArray(binding.value) ? binding.value : [binding.value]
    const hasRole = permissionStore.hasAnyRole(roles)

    if (!hasRole) {
      el.style.display = 'none'
    }
  },

  updated(el: HTMLElement, binding: DirectiveBinding<string | string[]>) {
    const permissionStore = usePermissionStore()
    const roles = Array.isArray(binding.value) ? binding.value : [binding.value]
    const hasRole = permissionStore.hasAnyRole(roles)

    el.style.display = hasRole ? '' : 'none'
  },
}

// 基于权限名称的简单指令
export const vCan = {
  mounted(el: HTMLElement, binding: DirectiveBinding<string | string[]>) {
    const permissionStore = usePermissionStore()
    const permissions = Array.isArray(binding.value) ? binding.value : [binding.value]
    const hasPermission = permissionStore.hasAnyPermission(permissions)

    if (!hasPermission) {
      el.style.display = 'none'
    }
  },

  updated(el: HTMLElement, binding: DirectiveBinding<string | string[]>) {
    const permissionStore = usePermissionStore()
    const permissions = Array.isArray(binding.value) ? binding.value : [binding.value]
    const hasPermission = permissionStore.hasAnyPermission(permissions)

    el.style.display = hasPermission ? '' : 'none'
  },
}

// 仅管理员可见的指令
export const vAdmin = {
  mounted(el: HTMLElement) {
    const permissionStore = usePermissionStore()
    if (!permissionStore.canAccessAdminPanel) {
      el.style.display = 'none'
    }
  },

  updated(el: HTMLElement) {
    const permissionStore = usePermissionStore()
    el.style.display = permissionStore.canAccessAdminPanel ? '' : 'none'
  },
}

// 需要认证的指令
export const vAuth = {
  mounted(el: HTMLElement) {
    const authStore = useAuthStore()
    if (!authStore.isAuthenticated) {
      el.style.display = 'none'
    }
  },

  updated(el: HTMLElement) {
    const authStore = useAuthStore()
    el.style.display = authStore.isAuthenticated ? '' : 'none'
  },
}
