/**
 * Weather API service
 */

import api from './api'
import type { WeatherResponse } from '@/types/weather'

export const weatherService = {
  /**
   * Get current weather for a city
   * @param city City name (Chinese/English) or AD code
   * @param extensions Weather type: 'base' (current) or 'all' (current + forecast)
   */
  async getWeather(city: string, extensions: 'base' | 'all' = 'base'): Promise<WeatherResponse> {
    try {
      const response = await api.get<WeatherResponse>('/weather', {
        params: { city, extensions },
      })
      return response.data
    } catch (error: any) {
      // Handle API errors
      if (error.response?.data) {
        return error.response.data
      }

      // Network or other errors
      return {
        success: false,
        error: error.message || 'Failed to fetch weather data',
      }
    }
  },
}

export default weatherService
