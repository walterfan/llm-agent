/**
 * Admin service for user management
 */

import api from './api'
import type {
  User,
  UserAdminCreate,
  UserAdminUpdate,
  UserListParams,
  UserListResponse,
  RoleUpdateRequest,
} from '@/types/rbac'

class AdminService {
  /**
   * Get paginated list of users
   */
  async getUsers(params?: UserListParams): Promise<UserListResponse> {
    const response = await api.get<UserListResponse>('/admin/users', { params })
    return response.data
  }

  /**
   * Get user by ID
   */
  async getUser(userId: number): Promise<User> {
    const response = await api.get<User>(`/admin/users/${userId}`)
    return response.data
  }

  /**
   * Create a new user as admin
   */
  async createUser(userData: UserAdminCreate): Promise<User> {
    const response = await api.post<User>('/admin/users', userData)
    return response.data
  }

  /**
   * Update user as admin
   */
  async updateUser(userId: number, userData: UserAdminUpdate): Promise<User> {
    const response = await api.patch<User>(`/admin/users/${userId}`, userData)
    return response.data
  }

  /**
   * Update user role
   */
  async updateUserRole(userId: number, roleData: RoleUpdateRequest): Promise<User> {
    const response = await api.patch<User>(`/admin/users/${userId}/role`, roleData)
    return response.data
  }

  /**
   * Delete user
   */
  async deleteUser(userId: number): Promise<void> {
    await api.delete(`/admin/users/${userId}`)
  }
}

export const adminService = new AdminService()
export default adminService
