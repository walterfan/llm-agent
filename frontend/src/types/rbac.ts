/**
 * Role-Based Access Control (RBAC) types
 */

export enum UserRole {
  SUPER_ADMIN = 'super_admin',
  ADMIN = 'admin',
  USER = 'user',
  GUEST = 'guest',
}

export interface User {
  id: number
  email: string
  full_name: string | null
  is_active: boolean
  role: UserRole
  created_at: string
  updated_at: string

  // Profile fields (optional)
  gender?: string | null
  age?: number | null
  identity?: string | null
  style?: string | null
  temperature_sensitivity?: string | null
  activity_context?: string | null
  other_preferences?: string | null
}

export interface UserAdminCreate {
  email: string
  password: string
  full_name?: string | null
  role?: UserRole
  is_active?: boolean
}

export interface UserAdminUpdate {
  full_name?: string | null
  email?: string | null
  role?: UserRole
  is_active?: boolean
  password?: string | null

  // Profile fields (optional)
  gender?: string | null
  age?: number | null
  identity?: string | null
  style?: string | null
  temperature_sensitivity?: string | null
  activity_context?: string | null
  other_preferences?: string | null
}

export interface RoleUpdateRequest {
  role: UserRole
}

export interface UserListResponse {
  items: User[]
  total: number
  limit: number
  offset: number
}

export interface UserListParams {
  skip?: number
  limit?: number
  search?: string
  role?: UserRole
}

// Permission types for RBAC
export interface Permission {
  id: number
  name: string
  resource: string
  action: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface PermissionCreate {
  name: string
  resource: string
  action: string
  description?: string | null
}

export interface PermissionUpdate {
  name?: string
  resource?: string
  action?: string
  description?: string | null
}

export interface PermissionListResponse {
  items: Permission[]
  total: number
  limit: number
  offset: number
}

export interface PermissionListParams {
  skip?: number
  limit?: number
  resource?: string
}

// Role types for RBAC
export interface Role {
  id: number
  name: string
  description: string | null
  created_at: string
  updated_at: string
  permissions: Permission[]
}

export interface RoleCreate {
  name: string
  description?: string | null
  permission_ids?: number[]
}

export interface RoleUpdate {
  name?: string
  description?: string | null
  permission_ids?: number[]
}

export interface RoleListResponse {
  items: Role[]
  total: number
  limit: number
  offset: number
}

export interface RoleListParams {
  skip?: number
  limit?: number
  search?: string
}

export interface RolePermissionAssignment {
  permission_ids: number[]
}
