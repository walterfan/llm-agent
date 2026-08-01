import api from './api'
import type {
  EmailLogListResponse,
  EmailPreferences,
  EmailPreferencesUpdate,
  EmailSendRequest,
  EmailSendResponse,
} from '@/types/email'

class EmailService {
  async getEmailPreferences(): Promise<EmailPreferences> {
    const response = await api.get<EmailPreferences>('/users/me/email-preferences')
    return response.data
  }

  async updateEmailPreferences(preferences: EmailPreferencesUpdate): Promise<EmailPreferences> {
    const response = await api.patch<EmailPreferences>('/users/me/email-preferences', preferences)
    return response.data
  }

  async sendEmailManually(request: EmailSendRequest): Promise<EmailSendResponse> {
    const response = await api.post<EmailSendResponse>('/recommendations/send-email', request)
    return response.data
  }

  async getEmailLogs(limit: number = 20, offset: number = 0): Promise<EmailLogListResponse> {
    const params = new URLSearchParams()
    params.append('limit', limit.toString())
    params.append('offset', offset.toString())

    const response = await api.get<EmailLogListResponse>(
      `/users/me/email-logs?${params.toString()}`
    )
    return response.data
  }
}

export default new EmailService()
