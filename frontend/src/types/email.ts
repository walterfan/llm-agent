export interface EmailPreferences {
  email_notifications_enabled: boolean
  email_send_time: string | null // HH:MM format
  email_additional_recipients: string[] | null
  email_preferred_city: string | null
}

export interface EmailPreferencesUpdate {
  email_notifications_enabled?: boolean
  email_send_time?: string // HH:MM format
  email_additional_recipients?: string[]
  email_preferred_city?: string | null
}

export interface EmailSendRequest {
  city: string
  recipient_emails: string[]
}

export interface EmailDeliveryResult {
  recipient_email: string
  status: 'sent' | 'failed'
  error_message?: string | null
}

export interface EmailSendResponse {
  success: boolean
  message: string
  deliveries: EmailDeliveryResult[]
}

export interface EmailLog {
  id: number
  user_id: number
  recommendation_id: string | null
  recipient_email: string
  status: string
  sent_at: string
  error_message: string | null
}

export interface EmailLogListResponse {
  total: number
  items: EmailLog[]
}
