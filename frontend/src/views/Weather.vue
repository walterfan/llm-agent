<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useWeatherStore } from '@/stores/weather'
import type { City } from '@/types/city'
import AppLayout from '@/components/layout/AppLayout.vue'
import CitySearch from '@/components/weather/CitySearch.vue'
import WeatherCard from '@/components/weather/WeatherCard.vue'

const weatherStore = useWeatherStore()

// Local state
const selectedCity = ref<City | null>(null)
const showError = ref(false)
const weatherMode = ref<'base' | 'all'>('base') // 'base' = 实时, 'all' = 预报

// Quick select cities
const quickCities = [
  { name: '长沙', name_en: 'Changsha', ad_code: '430100' },
  { name: '合肥', name_en: 'Hefei', ad_code: '340100' },
  { name: '北京', name_en: 'Beijing', ad_code: '110000' },
  { name: '上海', name_en: 'Shanghai', ad_code: '310000' },
]

// Handle city selection
async function handleCitySelect(city: City) {
  selectedCity.value = city
  weatherStore.clearError()
  await weatherStore.fetchWeather(city.ad_code, weatherMode.value)
}

// Handle quick select
async function handleQuickSelect(quickCity: { name: string; name_en: string; ad_code: string }) {
  // Create a mock City object for the quick select
  const city: City = {
    location_id: quickCity.ad_code,
    location_name_zh: quickCity.name,
    location_name_en: quickCity.name_en,
    ad_code: quickCity.ad_code,
    display_name: quickCity.name,
  }

  selectedCity.value = city
  weatherStore.clearError()
  await weatherStore.fetchWeather(city.ad_code, weatherMode.value)
}

// Handle weather mode change
async function handleModeChange(mode: 'base' | 'all') {
  weatherMode.value = mode

  // Re-fetch weather if a city is already selected
  if (selectedCity.value) {
    weatherStore.clearError()
    await weatherStore.fetchWeather(selectedCity.value.ad_code, mode)
  }
}

// Dismiss error
function dismissError() {
  weatherStore.clearError()
  showError.value = false
}

// Watch for errors
onMounted(() => {
  // Clear previous weather data on mount
  weatherStore.clearWeather()
})
</script>

<template>
  <AppLayout>
    <div class="weather-page min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div class="max-w-4xl mx-auto">
        <!-- Header -->
        <div class="text-center mb-8">
          <h1 class="text-4xl font-bold text-gray-900 mb-2">🌤️ Weather Information</h1>
          <p class="text-gray-600">Search for any Chinese city to get real-time weather updates</p>
        </div>

        <!-- Search Section -->
        <div class="bg-white rounded-xl shadow-md p-6 mb-8">
          <div class="flex items-center justify-between mb-4">
            <label class="block text-sm font-medium text-gray-700"> Search City </label>

            <!-- Weather Mode Toggle -->
            <div class="inline-flex rounded-lg border border-gray-300 bg-gray-50 p-1">
              <button
                type="button"
                class="px-4 py-1.5 text-sm font-medium rounded-md transition-colors"
                :class="
                  weatherMode === 'base'
                    ? 'bg-white text-blue-700 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                "
                @click="handleModeChange('base')"
              >
                🌡️ 实时
              </button>
              <button
                type="button"
                class="px-4 py-1.5 text-sm font-medium rounded-md transition-colors"
                :class="
                  weatherMode === 'all'
                    ? 'bg-white text-blue-700 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                "
                @click="handleModeChange('all')"
              >
                📅 预报
              </button>
            </div>
          </div>

          <CitySearch @select="handleCitySelect" />

          <!-- Quick Select Tags -->
          <div class="mt-4">
            <p class="text-xs text-gray-500 mb-2">Quick select:</p>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="city in quickCities"
                :key="city.ad_code"
                type="button"
                class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-full transition-colors"
                :class="
                  selectedCity?.ad_code === city.ad_code
                    ? 'bg-blue-600 text-white'
                    : 'bg-blue-50 text-blue-700 hover:bg-blue-100'
                "
                @click="handleQuickSelect(city)"
              >
                <span class="mr-1">📍</span>
                {{ city.name }}
                <span v-if="city.name_en" class="ml-1 text-xs opacity-75">{{ city.name_en }}</span>
              </button>
            </div>
          </div>

          <div v-if="selectedCity" class="mt-4 text-sm text-gray-600">
            Selected: <span class="font-medium">{{ selectedCity.display_name }}</span>
            <span class="ml-2 text-xs text-gray-500">
              ({{ weatherMode === 'base' ? '实时天气' : '天气预报' }})
            </span>
          </div>
        </div>

        <!-- Error Message -->
        <div
          v-if="weatherStore.error"
          class="bg-red-50 border border-red-200 rounded-lg p-4 mb-8 flex items-start justify-between"
        >
          <div class="flex items-start">
            <svg
              class="w-5 h-5 text-red-600 mt-0.5 mr-3"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div>
              <h3 class="text-sm font-medium text-red-800">Error Loading Weather</h3>
              <p class="text-sm text-red-700 mt-1">
                {{ weatherStore.error }}
              </p>
            </div>
          </div>
          <button type="button" class="text-red-400 hover:text-red-600" @click="dismissError">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <!-- Loading State -->
        <div v-if="weatherStore.loading" class="flex flex-col items-center justify-center py-12">
          <svg
            class="animate-spin h-12 w-12 text-blue-600 mb-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="4"
            />
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <p class="text-gray-600">Fetching weather data...</p>
        </div>

        <!-- Weather Card -->
        <div v-else-if="weatherStore.hasWeather && weatherStore.weatherData">
          <WeatherCard :weather="weatherStore.weatherData" />

          <!-- Forecast Cards (when mode is 'all' and forecast data exists) -->
          <div
            v-if="weatherMode === 'all' && weatherStore.weatherData.forecast?.casts"
            class="mt-8"
          >
            <h2 class="text-2xl font-bold text-gray-900 mb-4">📅 天气预报 (未来3-4天)</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div
                v-for="cast in weatherStore.weatherData.forecast.casts"
                :key="cast.date"
                class="bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow"
              >
                <!-- Date Header -->
                <div class="text-center mb-3 pb-3 border-b border-gray-200">
                  <div class="text-sm text-gray-500">
                    {{ cast.week }}
                  </div>
                  <div class="text-lg font-semibold text-gray-900">
                    {{ cast.date.split('-').slice(1).join('/') }}
                  </div>
                </div>

                <!-- Day Weather -->
                <div class="mb-3">
                  <div class="flex items-center justify-between mb-2">
                    <span class="text-xs text-gray-500">白天</span>
                    <span class="text-xl">☀️</span>
                  </div>
                  <div class="text-sm font-medium text-gray-900">
                    {{ cast.dayweather }}
                  </div>
                  <div class="flex items-center justify-between mt-1">
                    <span class="text-2xl font-bold text-orange-600">{{ cast.daytemp }}°C</span>
                    <div class="text-xs text-gray-600">
                      <div>{{ cast.daywind }}</div>
                      <div>{{ cast.daypower }}级</div>
                    </div>
                  </div>
                </div>

                <!-- Night Weather -->
                <div class="pt-3 border-t border-gray-100">
                  <div class="flex items-center justify-between mb-2">
                    <span class="text-xs text-gray-500">夜间</span>
                    <span class="text-xl">🌙</span>
                  </div>
                  <div class="text-sm font-medium text-gray-900">
                    {{ cast.nightweather }}
                  </div>
                  <div class="flex items-center justify-between mt-1">
                    <span class="text-2xl font-bold text-blue-600">{{ cast.nighttemp }}°C</span>
                    <div class="text-xs text-gray-600">
                      <div>{{ cast.nightwind }}</div>
                      <div>{{ cast.nightpower }}级</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-else class="bg-white rounded-xl shadow-md p-12 text-center">
          <div class="text-6xl mb-4">🔍</div>
          <h2 class="text-2xl font-semibold text-gray-900 mb-2">No City Selected</h2>
          <p class="text-gray-600">Search for a city above to view current weather conditions</p>
        </div>

        <!-- Info Footer -->
        <div class="mt-8 text-center text-sm text-gray-500">
          <p>Weather data is cached for 1 hour to improve performance.</p>
          <p class="mt-1">Powered by Gaode Weather API</p>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
.weather-page {
  min-height: calc(100vh - 64px); /* Adjust for header height */
}
</style>
