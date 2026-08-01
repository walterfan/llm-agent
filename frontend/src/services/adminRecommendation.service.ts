/**
 * Admin Recommendation Service
 *
 * Service for admin operations on recommendations (generate for other users, multi-day)
 */

import axios from 'axios'
import type {
  AdminGenerateMultiDayRequest,
  MultiDayRecommendationResponse,
} from '@/types/recommendation'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const API_V1_PREFIX = '/api/v1'

/**
 * Generate multi-day recommendations for a specific user (admin only)
 */
export async function generateForUser(
  userId: number,
  cityCode: string,
  sendEmail: boolean = false
): Promise<MultiDayRecommendationResponse> {
  const token = localStorage.getItem('access_token')

  if (!token) {
    throw new Error('No authentication token found')
  }

  const request: AdminGenerateMultiDayRequest = {
    user_id: userId,
    city_code: cityCode,
    send_email: sendEmail,
  }

  try {
    const response = await axios.post<MultiDayRecommendationResponse>(
      `${API_BASE_URL}${API_V1_PREFIX}/admin/recommendations/generate-for-user`,
      request,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }
    )

    return response.data
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const message = error.response?.data?.detail || error.message
      throw new Error(`Failed to generate recommendations: ${message}`)
    }
    throw error
  }
}

/**
 * Send multi-day email for already generated recommendations
 *
 * This is a convenience method that calls generateForUser with send_email=true
 * and the same parameters to trigger email sending
 */
export async function sendMultiDayEmail(
  userId: number,
  cityCode: string
): Promise<MultiDayRecommendationResponse> {
  return generateForUser(userId, cityCode, true)
}

export default {
  generateForUser,
  sendMultiDayEmail,
}
