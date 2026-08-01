/**
 * Weather store for state management
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { WeatherData } from '@/types/weather'
import type { City } from '@/types/city'
import weatherService from '@/services/weather.service'
import cityService from '@/services/city.service'

export const useWeatherStore = defineStore('weather', () => {
  // State
  const weatherData = ref<WeatherData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastFetchedCity = ref<string | null>(null)

  // Getters
  const hasWeather = computed(() => weatherData.value !== null)
  const isCached = computed(() => weatherData.value?.cached ?? false)

  // Actions
  async function fetchWeather(city: string, extensions: 'base' | 'all' = 'base'): Promise<void> {
    // Avoid duplicate requests for same city
    if (loading.value && lastFetchedCity.value === city) {
      return
    }

    loading.value = true
    error.value = null
    lastFetchedCity.value = city

    try {
      const response = await weatherService.getWeather(city, extensions)

      if (response.success && response.data) {
        weatherData.value = response.data
        error.value = null
      } else {
        weatherData.value = null
        error.value = response.error || 'Failed to fetch weather data'
      }
    } catch (err: any) {
      weatherData.value = null
      error.value = err.message || 'An unexpected error occurred'
    } finally {
      loading.value = false
    }
  }

  function clearWeather(): void {
    weatherData.value = null
    error.value = null
    lastFetchedCity.value = null
  }

  function clearError(): void {
    error.value = null
  }

  async function searchCities(query: string, limit: number = 10): Promise<City[]> {
    try {
      const response = await cityService.searchCities(query, limit)
      return response.cities
    } catch (err: any) {
      error.value = err.message || 'Failed to search cities'
      return []
    }
  }

  return {
    // State
    weatherData,
    loading,
    error,
    lastFetchedCity,

    // Getters
    hasWeather,
    isCached,

    // Actions
    fetchWeather,
    searchCities,
    clearWeather,
    clearError,
  }
})
