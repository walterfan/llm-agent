/**
 * RBAC store for role and permission management
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type {
  Permission,
  PermissionCreate,
  PermissionListParams,
  PermissionUpdate,
  Role,
  RoleCreate,
  RoleListParams,
  RolePermissionAssignment,
  RoleUpdate,
} from '@/types/rbac'
import { rbacService } from '@/services/rbac.service'

export const useRBACStore = defineStore('rbac', () => {
  // Permission State
  const permissions = ref<Permission[]>([])
  const totalPermissions = ref(0)
  const currentPermission = ref<Permission | null>(null)

  // Role State
  const roles = ref<Role[]>([])
  const totalRoles = ref(0)
  const currentRole = ref<Role | null>(null)

  // UI State
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Permission Actions
  async function fetchPermissions(params?: PermissionListParams) {
    loading.value = true
    error.value = null

    try {
      const response = await rbacService.getPermissions(params)
      permissions.value = response.items
      totalPermissions.value = response.total
      return response
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to fetch permissions'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function fetchPermission(permissionId: number) {
    loading.value = true
    error.value = null

    try {
      const permission = await rbacService.getPermission(permissionId)
      currentPermission.value = permission
      return permission
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to fetch permission'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function createPermission(data: PermissionCreate) {
    loading.value = true
    error.value = null

    try {
      const permission = await rbacService.createPermission(data)
      permissions.value.unshift(permission)
      totalPermissions.value++
      return permission
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to create permission'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function updatePermission(permissionId: number, data: PermissionUpdate) {
    loading.value = true
    error.value = null

    try {
      const permission = await rbacService.updatePermission(permissionId, data)
      const index = permissions.value.findIndex((p) => p.id === permissionId)
      if (index !== -1) {
        permissions.value[index] = permission
      }
      if (currentPermission.value?.id === permissionId) {
        currentPermission.value = permission
      }
      return permission
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to update permission'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function deletePermission(permissionId: number) {
    loading.value = true
    error.value = null

    try {
      await rbacService.deletePermission(permissionId)
      permissions.value = permissions.value.filter((p) => p.id !== permissionId)
      totalPermissions.value--
      if (currentPermission.value?.id === permissionId) {
        currentPermission.value = null
      }
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to delete permission'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  // Role Actions
  async function fetchRoles(params?: RoleListParams) {
    loading.value = true
    error.value = null

    try {
      const response = await rbacService.getRoles(params)
      roles.value = response.items
      totalRoles.value = response.total
      return response
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to fetch roles'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function fetchRole(roleId: number) {
    loading.value = true
    error.value = null

    try {
      const role = await rbacService.getRole(roleId)
      currentRole.value = role
      return role
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to fetch role'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function createRole(data: RoleCreate) {
    loading.value = true
    error.value = null

    try {
      const role = await rbacService.createRole(data)
      roles.value.unshift(role)
      totalRoles.value++
      return role
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to create role'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function updateRole(roleId: number, data: RoleUpdate) {
    loading.value = true
    error.value = null

    try {
      const role = await rbacService.updateRole(roleId, data)
      const index = roles.value.findIndex((r) => r.id === roleId)
      if (index !== -1) {
        roles.value[index] = role
      }
      if (currentRole.value?.id === roleId) {
        currentRole.value = role
      }
      return role
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to update role'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function deleteRole(roleId: number) {
    loading.value = true
    error.value = null

    try {
      await rbacService.deleteRole(roleId)
      roles.value = roles.value.filter((r) => r.id !== roleId)
      totalRoles.value--
      if (currentRole.value?.id === roleId) {
        currentRole.value = null
      }
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to delete role'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function addPermissionsToRole(roleId: number, data: RolePermissionAssignment) {
    loading.value = true
    error.value = null

    try {
      const role = await rbacService.addPermissionsToRole(roleId, data)
      const index = roles.value.findIndex((r) => r.id === roleId)
      if (index !== -1) {
        roles.value[index] = role
      }
      if (currentRole.value?.id === roleId) {
        currentRole.value = role
      }
      return role
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to add permissions to role'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function removePermissionsFromRole(roleId: number, data: RolePermissionAssignment) {
    loading.value = true
    error.value = null

    try {
      const role = await rbacService.removePermissionsFromRole(roleId, data)
      const index = roles.value.findIndex((r) => r.id === roleId)
      if (index !== -1) {
        roles.value[index] = role
      }
      if (currentRole.value?.id === roleId) {
        currentRole.value = role
      }
      return role
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to remove permissions from role'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  function clearCurrent() {
    currentPermission.value = null
    currentRole.value = null
  }

  return {
    // State
    permissions,
    totalPermissions,
    currentPermission,
    roles,
    totalRoles,
    currentRole,
    loading,
    error,
    // Actions
    fetchPermissions,
    fetchPermission,
    createPermission,
    updatePermission,
    deletePermission,
    fetchRoles,
    fetchRole,
    createRole,
    updateRole,
    deleteRole,
    addPermissionsToRole,
    removePermissionsFromRole,
    clearError,
    clearCurrent,
  }
})
