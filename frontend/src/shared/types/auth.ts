export interface User {
  id: string
  email: string
  username: string
  avatar?: string
  created_at: string
  updated_at: string
  roles?: UserRole[]
  permissions?: Permission[]
}

export interface UserRole {
  id: number
  name: string
  level: number
  region_id?: number
  granted_at?: string
  expires_at?: string
}

export interface Permission {
  id: number
  name: string
  description?: string
  resource: string
  action: string
}

export interface RoleType {
  SUPER_ADMIN: 'SUPER_ADMIN'
  REGION_ADMIN: 'REGION_ADMIN'
  TEAM_CAPTAIN: 'TEAM_CAPTAIN'
  TEAM_MEMBER: 'TEAM_MEMBER'
  PLAYER: 'PLAYER'
  USER: 'USER'
}

export interface PermissionCheck {
  hasPermission: (permission: string) => boolean
  hasRole: (role: string) => boolean
  hasMinLevel: (level: number) => boolean
  canManage: (targetRole: string) => boolean
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  username: string
  password: string
  confirm_password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface LoginResponse {
  user: User
  tokens: TokenResponse
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}
