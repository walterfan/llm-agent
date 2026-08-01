/**
 * Recommendation-related TypeScript interfaces
 */

export interface RecommendationOutput {
  clothing_items: string[]
  advice: string
  weather_warnings?: string | null
  emoji?: string | null
}

export interface WeatherSnapshot {
  city: string
  temperature: number
  weather: string
  humidity: number
  wind_direction: string
  wind_power: string
  date: string
  day_of_week: string
}

export interface RecommendationResponse {
  id: string
  user_id: number
  city: string
  weather_data: WeatherSnapshot
  clothing_items: string[]
  advice: string
  weather_warnings?: string | null
  emoji_summary?: string | null
  cached: boolean
  cost_estimate?: number | null
  created_at: string
}

export interface RecommendationCreate {
  city: string
  date?: string | null // used by single-day streaming endpoint only
  days?: 1 | 2 | 3
}

export interface RecommendationListResponse {
  items: RecommendationResponse[]
  total: number
  limit: number
  offset: number
}

// Streaming event types
export interface StreamStartEvent {
  type: 'start'
  message: string
}

export interface StreamTokenEvent {
  type: 'token'
  content: string
}

export interface StreamDataEvent {
  type: 'data'
  field: string
  value: any
}

export interface StreamErrorEvent {
  type: 'error'
  message: string
}

export interface StreamDoneEvent {
  type: 'done'
  message: string
  recommendation_id?: string | null
}

export type StreamEvent =
  | StreamStartEvent
  | StreamTokenEvent
  | StreamDataEvent
  | StreamErrorEvent
  | StreamDoneEvent

// User profile types
export interface UserProfile {
  gender?: string | null
  age?: number | null
  identity?: string | null
  style?: string | null
  temperature_sensitivity?: string | null
  activity_context?: string | null
  other_preferences?: string | null
}

export interface UserProfileUpdate extends UserProfile {}

// Admin multi-day recommendation types

export interface AdminGenerateMultiDayRequest {
  user_id: number
  city_code: string
  send_email: boolean
}

export interface DailyRecommendation {
  date: string
  date_label: string
  recommendation: RecommendationResponse
  weather_summary: string
}

export interface UserBasicInfo {
  id: number
  email: string
  full_name: string | null
}

export interface MultiDayRecommendationResponse {
  user: UserBasicInfo
  city: string
  city_code: string
  recommendations: DailyRecommendation[]
  email_sent: boolean
  generated_at: string
}
