import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import recommendationService from '@/services/recommendation.service'
import { useAuthStore } from './auth'
import type {
  RecommendationResponse,
  RecommendationCreate,
  StreamEvent,
  MultiDayRecommendationResponse,
} from '@/types/recommendation'

export const useRecommendationStore = defineStore('recommendation', () => {
  // State
  const recommendations = ref<RecommendationResponse[]>([])
  const currentRecommendation = ref<MultiDayRecommendationResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Streaming state
  const isStreaming = ref(false)
  const streamingText = ref('')
  const streamingWeather = ref<any>(null)
  const streamingStatus = ref('')
  const streamingForecast = ref<{ city?: string; ad_code?: string; days?: number } | null>(null)
  const streamingDays = ref<
    Array<{
      index: number
      date: string
      label: string
      weather_text?: string
      temperature_low?: number | string
      temperature_high?: number | string
      text: string
      recommendation_id?: string | null
    }>
  >([])
  const streamingCurrentDayIndex = ref<number>(0)

  // Computed
  const hasRecommendations = computed(() => recommendations.value.length > 0)
  const latestRecommendation = computed(() =>
    recommendations.value.length > 0 ? recommendations.value[0] : null
  )

  // Actions

  /**
   * Generate 3-day recommendations (today, tomorrow, day after tomorrow)
   */
  async function generateRecommendation(data: RecommendationCreate) {
    loading.value = true
    error.value = null
    try {
      const multiDayRecommendation = await recommendationService.generateRecommendation(data)
      currentRecommendation.value = multiDayRecommendation
      // Add each day's recommendation to the list
      multiDayRecommendation.recommendations.forEach((daily) => {
        recommendations.value.unshift(daily.recommendation)
      })
      return multiDayRecommendation
    } catch (err: any) {
      error.value =
        err.response?.data?.detail || err.message || 'Failed to generate recommendations'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Generate a recommendation with streaming
   */
  async function generateRecommendationStream(
    city: string,
    token: string,
    date?: string,
    days: 1 | 2 | 3 = 1,
    onToken?: (token: string) => void,
    onData?: (field: string, value: any) => void,
    onComplete?: (recommendationId?: string) => void
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      isStreaming.value = true
      streamingText.value = ''
      streamingWeather.value = null
      streamingStatus.value = ''
      streamingDays.value = []
      streamingCurrentDayIndex.value = 0
      error.value = null

      const eventSource =
        days === 1
          ? recommendationService.createStreamingEventSource(city, token, date)
          : recommendationService.createStreamingEventSource3DaysWithDays(city, token, days)

      eventSource.onmessage = (event) => {
        try {
          const data: StreamEvent = JSON.parse(event.data)

          switch (data.type) {
            case 'start':
              streamingStatus.value = data.message
              break

            case 'token':
              // Multi-day streaming (2 or 3 days): group tokens by day
              if (days > 1 && streamingDays.value.length > 0) {
                const idx = streamingCurrentDayIndex.value
                if (streamingDays.value[idx]) {
                  streamingDays.value[idx].text += data.content
                } else {
                  // Fallback: append to plain text if day not initialized yet
                  streamingText.value += data.content
                }
              } else {
                // Single-day streaming: append to plain text
                streamingText.value += data.content
              }
              onToken?.(data.content)
              break

            case 'data':
              if (data.field === 'status') {
                streamingStatus.value = data.value
              } else if (data.field === 'weather') {
                // single-day stream
                streamingWeather.value = data.value
              } else if (data.field === 'forecast') {
                // Multi-day stream: forecast info
                streamingForecast.value = data.value as any
              } else if (data.field === 'day') {
                // 3-day stream: start of a day block
                const day = data.value as any
                const index = Number(day.index ?? 0)
                streamingCurrentDayIndex.value = index
                // Ensure array length
                if (!streamingDays.value[index]) {
                  streamingDays.value[index] = {
                    index,
                    date: String(day.date || ''),
                    label: String(day.label || `Day ${index + 1}`),
                    weather_text: day.weather_text,
                    temperature_low: day.temperature_low,
                    temperature_high: day.temperature_high,
                    text: '',
                    recommendation_id: null,
                  }
                } else {
                  // Update metadata if already exists
                  streamingDays.value[index].date = String(
                    day.date || streamingDays.value[index].date
                  )
                  streamingDays.value[index].label = String(
                    day.label || streamingDays.value[index].label
                  )
                  streamingDays.value[index].weather_text =
                    day.weather_text ?? streamingDays.value[index].weather_text
                  streamingDays.value[index].temperature_low =
                    day.temperature_low ?? streamingDays.value[index].temperature_low
                  streamingDays.value[index].temperature_high =
                    day.temperature_high ?? streamingDays.value[index].temperature_high
                }
              } else if (data.field === 'day_done') {
                const payload = data.value as any
                const index = Number(payload.index ?? 0)
                if (streamingDays.value[index]) {
                  streamingDays.value[index].recommendation_id = payload.recommendation_id ?? null
                }
              }
              onData?.(data.field, data.value)
              break

            case 'error':
              error.value = data.message
              eventSource.close()
              isStreaming.value = false
              reject(new Error(data.message))
              break

            case 'done':
              streamingStatus.value = data.message
              eventSource.close()
              isStreaming.value = false
              onComplete?.(data.recommendation_id || undefined)

              // For multi-day streaming, convert streamingDays to MultiDayRecommendationResponse
              if (days > 1 && streamingDays.value.length > 0) {
                const cityName =
                  streamingForecast.value?.city ||
                  streamingDays.value.find((d) => d.weather_text)?.weather_text?.split(' ')[0] ||
                  ''
                const cityCode = streamingForecast.value?.ad_code || ''

                const dailyRecommendations = streamingDays.value.map((day, idx) => {
                  // Create a basic RecommendationResponse from streaming text
                  const recResponse: RecommendationResponse = {
                    id: day.recommendation_id || `stream-${idx}-${Date.now()}`,
                    user_id: 0, // Will be set from auth store
                    city: cityName,
                    weather_data: {
                      city: cityName,
                      temperature:
                        typeof day.temperature_low === 'number'
                          ? day.temperature_low
                          : typeof day.temperature_low === 'string'
                            ? parseFloat(day.temperature_low) || 0
                            : 0,
                      weather: day.weather_text || '',
                      humidity: 0,
                      wind_direction: '',
                      wind_power: '',
                      date: day.date || new Date().toISOString().split('T')[0],
                      day_of_week: '',
                    },
                    clothing_items: [], // Streaming doesn't provide structured data
                    advice: day.text || '',
                    weather_warnings: null,
                    emoji_summary: '👔',
                    cached: false,
                    cost_estimate: null,
                    created_at: new Date().toISOString(),
                  }

                  return {
                    date:
                      day.date ||
                      new Date(Date.now() + idx * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                    date_label: day.label || (idx === 0 ? '今天' : idx === 1 ? '明天' : '后天'),
                    recommendation: recResponse,
                    weather_summary: `${day.weather_text || ''}，${day.temperature_low || ''}°C - ${day.temperature_high || ''}°C`,
                  }
                })

                // Set currentRecommendation for email preview
                const authStore = useAuthStore()
                currentRecommendation.value = {
                  user: {
                    id: authStore.user?.id || 0,
                    email: authStore.user?.email || '',
                    full_name: authStore.user?.full_name || null,
                  },
                  city: cityName,
                  city_code: cityCode,
                  recommendations: dailyRecommendations,
                  email_sent: false,
                  generated_at: new Date().toISOString(),
                }
              } else if (days === 1 && streamingText.value) {
                // Single-day streaming: create a simple MultiDayRecommendationResponse
                const cityName = streamingWeather.value?.city || ''
                const recResponse: RecommendationResponse = {
                  id: data.recommendation_id || `stream-${Date.now()}`,
                  user_id: 0,
                  city: cityName,
                  weather_data: streamingWeather.value || {},
                  clothing_items: [],
                  advice: streamingText.value,
                  weather_warnings: null,
                  emoji_summary: '👔',
                  cached: false,
                  cost_estimate: null,
                  created_at: new Date().toISOString(),
                }

                const authStore = useAuthStore()
                currentRecommendation.value = {
                  user: {
                    id: authStore.user?.id || 0,
                    email: authStore.user?.email || '',
                    full_name: authStore.user?.full_name || null,
                  },
                  city: cityName,
                  city_code: '',
                  recommendations: [
                    {
                      date: new Date().toISOString().split('T')[0],
                      date_label: '今天',
                      recommendation: recResponse,
                      weather_summary: streamingWeather.value
                        ? `${streamingWeather.value.weather || ''}，${streamingWeather.value.temperature || ''}°C`
                        : '',
                    },
                  ],
                  email_sent: false,
                  generated_at: new Date().toISOString(),
                }
              }

              // Refresh recommendations list
              listRecommendations()

              resolve()
              break
          }
        } catch (err) {
          console.error('Error parsing stream event:', err)
        }
      }

      eventSource.onerror = (err) => {
        console.error('EventSource error:', err)
        error.value = 'Connection error. Please try again.'
        eventSource.close()
        isStreaming.value = false
        reject(new Error('Stream connection failed'))
      }
    })
  }

  /**
   * List user's recommendations
   */
  async function listRecommendations(limit: number = 20, offset: number = 0) {
    loading.value = true
    error.value = null
    try {
      const response = await recommendationService.listRecommendations(limit, offset)
      recommendations.value = response.items
      return response
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to list recommendations'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Get a specific recommendation
   */
  async function getRecommendation(id: string) {
    loading.value = true
    error.value = null
    try {
      const recommendation = await recommendationService.getRecommendation(id)
      // Convert single recommendation to MultiDayRecommendationResponse format for email preview
      currentRecommendation.value = {
        user: {
          id: recommendation.user_id,
          email: '',
          full_name: null,
        },
        city: recommendation.city,
        city_code: '',
        recommendations: [
          {
            date: recommendation.created_at.split('T')[0],
            date_label: '今天',
            recommendation: recommendation,
            weather_summary: recommendation.weather_data?.weather
              ? `${recommendation.weather_data.weather}，${recommendation.weather_data.temperature || ''}°C`
              : '',
          },
        ],
        email_sent: false,
        generated_at: recommendation.created_at,
      }
      return recommendation
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to get recommendation'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Clear current recommendation
   */
  function clearCurrentRecommendation() {
    currentRecommendation.value = null
    streamingText.value = ''
    streamingWeather.value = null
    streamingStatus.value = ''
    streamingForecast.value = null
    streamingDays.value = []
    streamingCurrentDayIndex.value = 0
  }

  /**
   * Clear error
   */
  function clearError() {
    error.value = null
  }

  /**
   * Stop streaming
   */
  function stopStreaming() {
    isStreaming.value = false
    streamingText.value = ''
    streamingStatus.value = ''
    streamingDays.value = []
    streamingCurrentDayIndex.value = 0
  }

  return {
    // State
    recommendations,
    currentRecommendation,
    loading,
    error,
    isStreaming,
    streamingText,
    streamingWeather,
    streamingStatus,
    streamingDays,
    streamingCurrentDayIndex,

    // Computed
    hasRecommendations,
    latestRecommendation,

    // Actions
    generateRecommendation,
    generateRecommendationStream,
    listRecommendations,
    getRecommendation,
    clearCurrentRecommendation,
    clearError,
    stopStreaming,
  }
})
