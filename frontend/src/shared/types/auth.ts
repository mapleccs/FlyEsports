export interface User {
  id: string
  email: string
  username: string
  avatar?: string
  created_at: string
  updated_at: string
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

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}