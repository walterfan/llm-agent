import { defineStore } from 'pinia'
import { ref } from 'vue'
import emailService from '@/services/email.service'
import type {
  EmailLog,
  EmailPreferences,
  EmailPreferencesUpdate,
  EmailSendRequest,
  EmailSendResponse,
} from '@/types/email'

export const useEmailStore = defineStore('email', () => {
  // State
  const preferences = ref<EmailPreferences | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const emailLogs = ref<EmailLog[]>([])
  const sendingEmail = ref(false)

  // Actions
  async function fetchPreferences(): Promise<EmailPreferences> {
    loading.value = true
    error.value = null
    try {
      const data = await emailService.getEmailPreferences()
      preferences.value = data
      return data
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to fetch email preferences'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updatePreferences(update: EmailPreferencesUpdate) {
    loading.value = true
    error.value = null
    try {
      preferences.value = await emailService.updateEmailPreferences(update)
    } catch (err: any) {
      error.value =
        err.response?.data?.detail || err.message || 'Failed to update email preferences'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function sendEmail(request: EmailSendRequest): Promise<EmailSendResponse> {
    sendingEmail.value = true
    error.value = null
    try {
      const response = await emailService.sendEmailManually(request)
      // Refresh logs after sending
      await fetchEmailLogs()
      return response
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to send email'
      throw err
    } finally {
      sendingEmail.value = false
    }
  }

  async function fetchEmailLogs(limit: number = 20, offset: number = 0) {
    loading.value = true
    error.value = null
    try {
      const response = await emailService.getEmailLogs(limit, offset)
      emailLogs.value = response.items
      return response
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to fetch email logs'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    preferences,
    loading,
    error,
    emailLogs,
    sendingEmail,
    // Actions
    fetchPreferences,
    updatePreferences,
    sendEmail,
    fetchEmailLogs,
  }
})
