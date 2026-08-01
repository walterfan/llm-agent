import { UserRole } from './rbac'

export interface User {
  id: number
  email: string
  full_name: string | null
  is_active: boolean
  role: UserRole
  created_at: string
  updated_at: string
  // AI Recommendation Profile Fields
  gender?: string | null
  age?: number | null
  identity?: string | null
  style?: string | null
  temperature_sensitivity?: string | null
  activity_context?: string | null
  other_preferences?: string | null
}

export interface UserCreate {
  email: string
  password: string
  full_name?: string
}

export interface UserUpdate {
  full_name?: string
  password?: string
}

export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}

export interface ChangePasswordResponse {
  message: string
}

export interface UserProfileUpdate {
  gender?: string | null
  age?: number | null
  identity?: string | null
  style?: string | null
  temperature_sensitivity?: string | null
  activity_context?: string | null
  other_preferences?: string | null
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  user: User
  access_token: string
  refresh_token: string
  token_type: string
}

export interface SignupRequest {
  email: string
  password: string
  full_name?: string
}

export interface SignupResponse {
  user: User
  message: string
}

export interface ApiError {
  detail: string
}
