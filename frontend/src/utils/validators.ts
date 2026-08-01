/**
 * Email validation regex pattern
 */
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/**
 * Validate email format
 */
export function validateEmail(email: string): string | null {
  if (!email) {
    return 'Email is required'
  }
  if (!EMAIL_REGEX.test(email)) {
    return 'Invalid email format'
  }
  return null
}

/**
 * Validate password
 */
export function validatePassword(password: string): string | null {
  if (!password) {
    return 'Password is required'
  }
  if (password.length < 8) {
    return 'Password must be at least 8 characters'
  }
  return null
}

/**
 * Validate full name
 */
export function validateFullName(name: string): string | null {
  if (name && name.length < 2) {
    return 'Name must be at least 2 characters'
  }
  return null
}
