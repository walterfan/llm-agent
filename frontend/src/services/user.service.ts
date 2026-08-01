import api from './api'
import type {
  ChangePasswordRequest,
  ChangePasswordResponse,
  User,
  UserProfileUpdate,
  UserUpdate,
} from '@/types/user'

export const userService = {
  /**
   * Get current user profile
   */
  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/users/me')
    return response.data
  },

  /**
   * Update current user profile
   */
  async updateProfile(data: UserUpdate): Promise<User> {
    const response = await api.patch<User>('/users/me', data)
    return response.data
  },

  /**
   * Update user dress preferences profile
   */
  async updateDressProfile(data: UserProfileUpdate): Promise<User> {
    const response = await api.patch<User>('/users/me/profile', data)
    return response.data
  },

  /**
   * Delete current user account
   */
  async deleteAccount(): Promise<void> {
    await api.delete('/users/me')
  },

  /**
   * Change current user's password
   */
  async changePassword(data: ChangePasswordRequest): Promise<ChangePasswordResponse> {
    const response = await api.post<ChangePasswordResponse>('/users/me/change-password', data)
    return response.data
  },
}
