/**
 * Admin Recommendation Store
 *
 * Pinia store for managing admin recommendation operations
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  MultiDayRecommendationResponse,
  AdminGenerateMultiDayRequest,
} from '@/types/recommendation'
import {
  generateForUser as generateForUserService,
  sendMultiDayEmail,
} from '@/services/adminRecommendation.service'

export const useAdminRecommendationStore = defineStore('adminRecommendation', () => {
  // State
  const recommendations = ref<MultiDayRecommendationResponse | null>(null)
  const loading = ref<boolean>(false)
  const error = ref<string | null>(null)

  // Getters
  const hasRecommendations = computed(() => recommendations.value !== null)

  const currentUser = computed(() => recommendations.value?.user || null)

  const currentCity = computed(() => recommendations.value?.city || null)

  const dailyRecommendations = computed(() => recommendations.value?.recommendations || [])

  const wasEmailSent = computed(() => recommendations.value?.email_sent || false)

  const emailSent = computed(() => recommendations.value?.email_sent || false)

  // Actions
  async function generate(
    userId: number,
    cityCode: string,
    sendEmail: boolean = false
  ): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const result = await generateForUserService(userId, cityCode, sendEmail)
      recommendations.value = result
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to generate recommendations'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function generateForUser(request: AdminGenerateMultiDayRequest): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const result = await generateForUserService(
        request.user_id,
        request.city_code,
        request.send_email || false
      )
      recommendations.value = result
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to generate recommendations'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function sendEmail(userId: number, cityCode: string): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const result = await sendMultiDayEmail(userId, cityCode)
      recommendations.value = result
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to send email'
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearRecommendations(): void {
    recommendations.value = null
    error.value = null
  }

  function clearError(): void {
    error.value = null
  }

  return {
    // State
    recommendations,
    loading,
    error,

    // Getters
    hasRecommendations,
    currentUser,
    currentCity,
    dailyRecommendations,
    wasEmailSent,
    emailSent,

    // Actions
    generate,
    generateForUser,
    sendEmail,
    clearRecommendations,
    clearError,
  }
})
