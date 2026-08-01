/**
 * Email Preferences Types
 *
 * TypeScript interfaces for email notification preferences.
 */

export interface EmailPreferences {
  email_notifications_enabled: boolean
  email_send_time: string | null // HH:MM format (24-hour)
  email_additional_recipients: string[] | null
  email_preferred_city: string | null
}

export interface EmailPreferencesUpdate {
  email_notifications_enabled?: boolean
  email_send_time?: string | null // HH:MM format (24-hour)
  email_additional_recipients?: string[] | null
  email_preferred_city?: string | null
}

export interface TestEmailResponse {
  message: string
  user_id: number
  emails_sent: number
  emails_failed: number
  total_recipients: number
}

/**
 * Validate time format (HH:MM)
 * @param time Time string to validate
 * @returns True if valid HH:MM format (24-hour)
 */
export function isValidTimeFormat(time: string): boolean {
  if (!time) return false
  const timeRegex = /^([01]\d|2[0-3]):([0-5]\d)$/
  return timeRegex.test(time)
}

/**
 * Format time string to HH:MM
 * @param hour Hour (0-23)
 * @param minute Minute (0-59)
 * @returns Formatted time string
 */
export function formatTime(hour: number, minute: number): string {
  return `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`
}

/**
 * Parse time string to hour and minute
 * @param time Time string in HH:MM format
 * @returns Object with hour and minute, or null if invalid
 */
export function parseTime(time: string): { hour: number; minute: number } | null {
  if (!isValidTimeFormat(time)) return null
  const [hourStr, minuteStr] = time.split(':')
  return {
    hour: parseInt(hourStr, 10),
    minute: parseInt(minuteStr, 10),
  }
}

/**
 * Validate email address format
 * @param email Email address to validate
 * @returns True if valid email format
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
  return emailRegex.test(email)
}

/**
 * Validate list of email addresses
 * @param emails Array of email addresses
 * @returns Array of invalid emails, or empty array if all valid
 */
export function validateEmails(emails: string[]): string[] {
  return emails.filter((email) => !isValidEmail(email))
}
