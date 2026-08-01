import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, LoginRequest, SignupRequest } from '@/types/user'
import { UserRole } from '@/types/rbac'
import { authService } from '@/services/auth.service'
import { userService } from '@/services/user.service'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!user.value)
  const currentUser = computed(() => user.value)
  const token = computed(() => authService.getToken())

  // Actions
  async function login(credentials: LoginRequest) {
    loading.value = true
    error.value = null

    try {
      const response = await authService.signin(credentials)
      user.value = response.user
      authService.saveAuth(response.access_token, response.refresh_token, response.user)
      return response
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Login failed. Please try again.'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function signup(data: SignupRequest) {
    loading.value = true
    error.value = null

    try {
      const response = await authService.signup(data)
      // After signup, automatically login
      await login({ email: data.email, password: data.password })
      return response
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Signup failed. Please try again.'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    user.value = null
    authService.clearAuth()
  }

  async function loadUser() {
    if (!authService.isAuthenticated()) {
      return
    }

    loading.value = true
    error.value = null

    try {
      const userData = await userService.getCurrentUser()
      user.value = userData
    } catch (err: any) {
      // If loading user fails, clear auth
      logout()
    } finally {
      loading.value = false
    }
  }

  async function updateProfile(data: { full_name?: string; password?: string }) {
    loading.value = true
    error.value = null

    try {
      const updatedUser = await userService.updateProfile(data)
      user.value = updatedUser
      // Update user in localStorage
      if (authService.getToken()) {
        authService.saveAuth(
          authService.getToken()!,
          authService.getRefreshToken() || '',
          updatedUser
        )
      }
      return updatedUser
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Update failed. Please try again.'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function changePassword(data: { current_password: string; new_password: string }) {
    loading.value = true
    error.value = null

    try {
      await userService.changePassword(data)
      return true
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Password change failed. Please try again.'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function updateDressProfile(data: any) {
    loading.value = true
    error.value = null

    try {
      const updatedUser = await userService.updateDressProfile(data)
      user.value = updatedUser
      // Update user in localStorage
      if (authService.getToken()) {
        authService.saveAuth(
          authService.getToken()!,
          authService.getRefreshToken() || '',
          updatedUser
        )
      }
      return updatedUser
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to update dress profile'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  // Initialize auth state from localStorage
  function init() {
    const storedUser = localStorage.getItem('user')
    if (storedUser) {
      try {
        user.value = JSON.parse(storedUser)
      } catch {
        // Invalid stored user, clear it
        authService.clearAuth()
      }
    }
  }

  // Role-based access control helpers
  const isSuperAdmin = computed(() => user.value?.role === UserRole.SUPER_ADMIN)
  const isAdmin = computed(
    () => user.value?.role === UserRole.SUPER_ADMIN || user.value?.role === UserRole.ADMIN
  )
  const isUser = computed(
    () =>
      user.value?.role === UserRole.SUPER_ADMIN ||
      user.value?.role === UserRole.ADMIN ||
      user.value?.role === UserRole.USER
  )

  function hasRole(requiredRole: UserRole): boolean {
    if (!user.value?.role) return false

    const roleHierarchy = {
      [UserRole.SUPER_ADMIN]: 4,
      [UserRole.ADMIN]: 3,
      [UserRole.USER]: 2,
      [UserRole.GUEST]: 1,
    }

    return roleHierarchy[user.value.role] >= roleHierarchy[requiredRole]
  }

  return {
    // State
    user,
    loading,
    error,
    // Getters
    isAuthenticated,
    currentUser,
    token,
    isSuperAdmin,
    isAdmin,
    isUser,
    // Actions
    login,
    signup,
    logout,
    loadUser,
    updateProfile,
    updateDressProfile,
    changePassword,
    clearError,
    init,
    hasRole,
  }
})
