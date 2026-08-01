/**
 * RBAC service for role and permission management
 */

import api from './api'
import type {
  Permission,
  PermissionCreate,
  PermissionListParams,
  PermissionListResponse,
  PermissionUpdate,
  Role,
  RoleCreate,
  RoleListParams,
  RoleListResponse,
  RolePermissionAssignment,
  RoleUpdate,
} from '@/types/rbac'

class RBACService {
  // Permission API calls
  async getPermissions(params?: PermissionListParams): Promise<PermissionListResponse> {
    const response = await api.get<PermissionListResponse>('/rbac/permissions', { params })
    return response.data
  }

  async getPermission(permissionId: number): Promise<Permission> {
    const response = await api.get<Permission>(`/rbac/permissions/${permissionId}`)
    return response.data
  }

  async createPermission(data: PermissionCreate): Promise<Permission> {
    const response = await api.post<Permission>('/rbac/permissions', data)
    return response.data
  }

  async updatePermission(permissionId: number, data: PermissionUpdate): Promise<Permission> {
    const response = await api.patch<Permission>(`/rbac/permissions/${permissionId}`, data)
    return response.data
  }

  async deletePermission(permissionId: number): Promise<void> {
    await api.delete(`/rbac/permissions/${permissionId}`)
  }

  // Role API calls
  async getRoles(params?: RoleListParams): Promise<RoleListResponse> {
    const response = await api.get<RoleListResponse>('/rbac/roles', { params })
    return response.data
  }

  async getRole(roleId: number): Promise<Role> {
    const response = await api.get<Role>(`/rbac/roles/${roleId}`)
    return response.data
  }

  async createRole(data: RoleCreate): Promise<Role> {
    const response = await api.post<Role>('/rbac/roles', data)
    return response.data
  }

  async updateRole(roleId: number, data: RoleUpdate): Promise<Role> {
    const response = await api.patch<Role>(`/rbac/roles/${roleId}`, data)
    return response.data
  }

  async deleteRole(roleId: number): Promise<void> {
    await api.delete(`/rbac/roles/${roleId}`)
  }

  async addPermissionsToRole(roleId: number, data: RolePermissionAssignment): Promise<Role> {
    const response = await api.post<Role>(`/rbac/roles/${roleId}/permissions`, data)
    return response.data
  }

  async removePermissionsFromRole(roleId: number, data: RolePermissionAssignment): Promise<Role> {
    const response = await api.delete<Role>(`/rbac/roles/${roleId}/permissions`, { data })
    return response.data
  }
}

export const rbacService = new RBACService()
export default rbacService
