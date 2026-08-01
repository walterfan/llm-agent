/**
 * Admin store for user management
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type {
  User,
  UserAdminCreate,
  UserAdminUpdate,
  UserListParams,
  RoleUpdateRequest,
} from '@/types/rbac'
import { adminService } from '@/services/admin.service'

export const useAdminStore = defineStore('admin', () => {
  // State
  const users = ref<User[]>([])
  const totalUsers = ref(0)
  const currentUser = ref<User | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Actions
  async function fetchUsers(params?: UserListParams) {
    loading.value = true
    error.value = null

    try {
      const response = await adminService.getUsers(params)
      users.value = response.items
      totalUsers.value = response.total
      return response
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to fetch users'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function fetchUser(userId: number) {
    loading.value = true
    error.value = null

    try {
      const user = await adminService.getUser(userId)
      currentUser.value = user
      return user
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to fetch user'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function createUser(userData: UserAdminCreate) {
    loading.value = true
    error.value = null

    try {
      const user = await adminService.createUser(userData)
      // Add to users list
      users.value.unshift(user)
      totalUsers.value++
      return user
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to create user'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function updateUser(userId: number, userData: UserAdminUpdate) {
    loading.value = true
    error.value = null

    try {
      const user = await adminService.updateUser(userId, userData)
      // Update in users list
      const index = users.value.findIndex((u) => u.id === userId)
      if (index !== -1) {
        users.value[index] = user
      }
      if (currentUser.value?.id === userId) {
        currentUser.value = user
      }
      return user
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to update user'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function updateUserRole(userId: number, roleData: RoleUpdateRequest) {
    loading.value = true
    error.value = null

    try {
      const user = await adminService.updateUserRole(userId, roleData)
      // Update in users list
      const index = users.value.findIndex((u) => u.id === userId)
      if (index !== -1) {
        users.value[index] = user
      }
      if (currentUser.value?.id === userId) {
        currentUser.value = user
      }
      return user
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to update user role'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function deleteUser(userId: number) {
    loading.value = true
    error.value = null

    try {
      await adminService.deleteUser(userId)
      // Remove from users list
      users.value = users.value.filter((u) => u.id !== userId)
      totalUsers.value--
      if (currentUser.value?.id === userId) {
        currentUser.value = null
      }
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to delete user'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  function clearCurrentUser() {
    currentUser.value = null
  }

  return {
    // State
    users,
    totalUsers,
    currentUser,
    loading,
    error,
    // Actions
    fetchUsers,
    fetchUser,
    createUser,
    updateUser,
    updateUserRole,
    deleteUser,
    clearError,
    clearCurrentUser,
  }
})
