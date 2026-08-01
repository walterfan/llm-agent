/**
 * Email Preferences Service
 *
 * API client for email notification preferences management.
 */

import api from './api'
import type {
  EmailPreferences,
  EmailPreferencesUpdate,
  TestEmailResponse,
} from '@/types/emailPreferences'

/**
 * Get current user's email preferences
 */
export async function getUserEmailPreferences(): Promise<EmailPreferences> {
  const response = await api.get<EmailPreferences>('/users/me/email-preferences')
  return response.data
}

/**
 * Update current user's email preferences
 */
export async function updateUserEmailPreferences(
  data: EmailPreferencesUpdate
): Promise<EmailPreferences> {
  const response = await api.patch<EmailPreferences>('/users/me/email-preferences', data)
  return response.data
}

/**
 * Get email preferences for a specific user (admin only)
 */
export async function getAdminUserEmailPreferences(userId: number): Promise<EmailPreferences> {
  const response = await api.get<EmailPreferences>(`/admin/users/${userId}/email-preferences`)
  return response.data
}

/**
 * Update email preferences for a specific user (admin only)
 */
export async function updateAdminUserEmailPreferences(
  userId: number,
  data: EmailPreferencesUpdate
): Promise<EmailPreferences> {
  const response = await api.patch<EmailPreferences>(
    `/admin/users/${userId}/email-preferences`,
    data
  )
  return response.data
}

/**
 * Test scheduled email for a user (admin only)
 * Sends a test email immediately to verify configuration
 */
export async function testScheduledEmail(userId: number): Promise<TestEmailResponse> {
  const response = await api.post<TestEmailResponse>(`/admin/users/${userId}/test-scheduled-email`)
  return response.data
}
