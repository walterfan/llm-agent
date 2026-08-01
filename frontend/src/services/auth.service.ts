import axios from 'axios'
import api from './api'
import type { LoginRequest, LoginResponse, SignupRequest, SignupResponse } from '@/types/user'

export const authService = {
  /**
   * Sign up a new user
   */
  async signup(data: SignupRequest): Promise<SignupResponse> {
    const response = await api.post<SignupResponse>('/auth/signup', data)
    return response.data
  },

  /**
   * Sign in with email and password
   */
  async signin(data: LoginRequest): Promise<LoginResponse> {
    const response = await api.post<LoginResponse>('/auth/signin', data)
    return response.data
  },

  /**
   * Refresh the access token using the stored refresh token.
   * Uses a standalone axios instance to avoid triggering the 401 interceptor.
   */
  async refreshToken(): Promise<{ access_token: string; refresh_token: string } | null> {
    const refreshToken = this.getRefreshToken()
    if (!refreshToken) return null

    try {
      const response = await axios.post<{ access_token: string; refresh_token: string }>(
        '/api/v1/auth/refresh',
        { refresh_token: refreshToken }
      )
      const { access_token, refresh_token: newRefreshToken } = response.data
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', newRefreshToken)
      return response.data
    } catch {
      return null
    }
  },

  /**
   * Save authentication data to localStorage
   */
  saveAuth(token: string, refreshToken: string, user: LoginResponse['user']): void {
    localStorage.setItem('access_token', token)
    localStorage.setItem('refresh_token', refreshToken)
    localStorage.setItem('user', JSON.stringify(user))
  },

  /**
   * Clear authentication data from localStorage
   */
  clearAuth(): void {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
  },

  /**
   * Get stored access token
   */
  getToken(): string | null {
    return localStorage.getItem('access_token')
  },

  /**
   * Get stored refresh token
   */
  getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token')
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return !!this.getToken()
  },
}
