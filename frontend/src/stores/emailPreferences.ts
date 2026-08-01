/**
 * Email Preferences Store
 *
 * State management for email notification preferences.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { EmailPreferences, EmailPreferencesUpdate } from '@/types/emailPreferences'
import * as emailPreferencesService from '@/services/emailPreferences.service'

export const useEmailPreferencesStore = defineStore('emailPreferences', () => {
  // State
  const preferences = ref<EmailPreferences | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const testEmailLoading = ref(false)
  const testEmailError = ref<string | null>(null)
  const testEmailSuccess = ref<string | null>(null)

  // Getters
  const hasPreferences = computed(() => preferences.value !== null)
  const isEnabled = computed(() => preferences.value?.email_notifications_enabled ?? false)
  const sendTime = computed(() => preferences.value?.email_send_time ?? null)
  const additionalRecipients = computed(() => preferences.value?.email_additional_recipients ?? [])
  const preferredCity = computed(() => preferences.value?.email_preferred_city ?? null)

  // Actions
  async function fetchPreferences() {
    loading.value = true
    error.value = null
    try {
      preferences.value = await emailPreferencesService.getUserEmailPreferences()
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to load email preferences'
      console.error('Failed to fetch email preferences:', err)
    } finally {
      loading.value = false
    }
  }

  async function updatePreferences(data: EmailPreferencesUpdate) {
    loading.value = true
    error.value = null
    try {
      preferences.value = await emailPreferencesService.updateUserEmailPreferences(data)
      return true
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to update email preferences'
      console.error('Failed to update email preferences:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchAdminPreferences(userId: number) {
    loading.value = true
    error.value = null
    try {
      preferences.value = await emailPreferencesService.getAdminUserEmailPreferences(userId)
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to load user email preferences'
      console.error('Failed to fetch admin email preferences:', err)
    } finally {
      loading.value = false
    }
  }

  async function updateAdminPreferences(userId: number, data: EmailPreferencesUpdate) {
    loading.value = true
    error.value = null
    try {
      preferences.value = await emailPreferencesService.updateAdminUserEmailPreferences(
        userId,
        data
      )
      return true
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to update user email preferences'
      console.error('Failed to update admin email preferences:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  async function testEmail(userId: number) {
    testEmailLoading.value = true
    testEmailError.value = null
    testEmailSuccess.value = null
    try {
      const result = await emailPreferencesService.testScheduledEmail(userId)
      testEmailSuccess.value = `Test email sent! ${result.emails_sent} sent, ${result.emails_failed} failed`
      return true
    } catch (err: any) {
      testEmailError.value = err.response?.data?.detail || 'Failed to send test email'
      console.error('Failed to send test email:', err)
      return false
    } finally {
      testEmailLoading.value = false
    }
  }

  function clearError() {
    error.value = null
    testEmailError.value = null
  }

  function clearTestEmailSuccess() {
    testEmailSuccess.value = null
  }

  function reset() {
    preferences.value = null
    loading.value = false
    error.value = null
    testEmailLoading.value = false
    testEmailError.value = null
    testEmailSuccess.value = null
  }

  return {
    // State
    preferences,
    loading,
    error,
    testEmailLoading,
    testEmailError,
    testEmailSuccess,
    // Getters
    hasPreferences,
    isEnabled,
    sendTime,
    additionalRecipients,
    preferredCity,
    // Actions
    fetchPreferences,
    updatePreferences,
    fetchAdminPreferences,
    updateAdminPreferences,
    testEmail,
    clearError,
    clearTestEmailSuccess,
    reset,
  }
})
