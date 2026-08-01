import api from './api'
import type {
  RecommendationCreate,
  RecommendationListResponse,
  RecommendationResponse,
  MultiDayRecommendationResponse,
} from '@/types/recommendation'

class RecommendationService {
  /**
   * Generate 3-day recommendations (today, tomorrow, day after tomorrow)
   */
  async generateRecommendation(
    data: RecommendationCreate
  ): Promise<MultiDayRecommendationResponse> {
    const response = await api.post<MultiDayRecommendationResponse>('/recommendations/', data)
    return response.data
  }

  /**
   * List user's recommendations
   */
  async listRecommendations(
    limit: number = 20,
    offset: number = 0,
    startDate?: string,
    endDate?: string
  ): Promise<RecommendationListResponse> {
    const params = new URLSearchParams()
    params.append('limit', limit.toString())
    params.append('offset', offset.toString())
    if (startDate) params.append('start_date', startDate)
    if (endDate) params.append('end_date', endDate)

    const response = await api.get<RecommendationListResponse>(
      `/recommendations/?${params.toString()}`
    )
    return response.data
  }

  /**
   * Get a specific recommendation by ID
   */
  async getRecommendation(id: string): Promise<RecommendationResponse> {
    const response = await api.get<RecommendationResponse>(`/recommendations/${id}`)
    return response.data
  }

  /**
   * Get the API base URL for EventSource connections.
   * In development, use the backend directly. In production, use relative URLs.
   */
  private getApiBaseUrl(): string {
    // Check for explicit environment variable
    if (import.meta.env.VITE_API_URL) {
      return import.meta.env.VITE_API_URL
    }
    // In development, connect to the backend directly
    // Default to same origin (works when proxied or in production)
    return ''
  }

  /**
   * Create EventSource for streaming recommendations
   * Note: EventSource doesn't support custom headers, so we pass token as query param
   */
  createStreamingEventSource(city: string, token: string, date?: string): EventSource {
    const params = new URLSearchParams()
    params.append('city', city)
    params.append('token', token) // Pass token as query param for EventSource
    if (date) params.append('date', date)

    const baseUrl = this.getApiBaseUrl()
    const url = `${baseUrl}/api/v1/recommendations/stream?${params.toString()}`

    return new EventSource(url)
  }

  /**
   * Create EventSource for 3-day streaming recommendations.
   * Endpoint: GET /api/v1/recommendations/stream/3days
   */
  createStreamingEventSource3Days(city: string, token: string): EventSource {
    const params = new URLSearchParams()
    params.append('city', city)
    params.append('token', token)

    const baseUrl = this.getApiBaseUrl()
    const url = `${baseUrl}/api/v1/recommendations/stream/3days?${params.toString()}`
    return new EventSource(url)
  }

  createStreamingEventSource3DaysWithDays(
    city: string,
    token: string,
    days: 1 | 2 | 3
  ): EventSource {
    const params = new URLSearchParams()
    params.append('city', city)
    params.append('token', token)
    params.append('days', String(days))

    const baseUrl = this.getApiBaseUrl()
    const url = `${baseUrl}/api/v1/recommendations/stream/3days?${params.toString()}`
    return new EventSource(url)
  }
}

export default new RecommendationService()
