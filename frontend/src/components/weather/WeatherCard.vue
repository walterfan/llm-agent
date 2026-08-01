<script setup lang="ts">
import { computed } from 'vue'
import type { WeatherData } from '@/types/weather'
import WeatherIcon from './WeatherIcon.vue'

interface Props {
  weather: WeatherData
}

const props = defineProps<Props>()

const formattedTime = computed(() => {
  try {
    const date = new Date(props.weather.report_time)
    return date.toLocaleString('zh-CN', {
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return props.weather.report_time
  }
})

const temperatureLabel = computed(() => {
  return `${props.weather.temperature}°C`
})

const humidityLabel = computed(() => {
  return `${props.weather.humidity}%`
})
</script>

<template>
  <div class="weather-card bg-white rounded-xl shadow-lg p-6 space-y-6">
    <!-- Header with City Info -->
    <div class="flex justify-between items-start">
      <div>
        <h2 class="text-2xl font-bold text-gray-900">
          {{ weather.city }}
        </h2>
        <p v-if="weather.province" class="text-sm text-gray-500 mt-1">
          {{ weather.province }}
        </p>
      </div>
      <div v-if="weather.cached" class="flex items-center text-xs text-gray-500">
        <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        Cached
      </div>
    </div>

    <!-- Main Weather Info -->
    <div class="flex items-center justify-between py-4">
      <div class="flex items-center space-x-4">
        <WeatherIcon :condition="weather.weather" size="large" />
        <div>
          <div class="text-5xl font-bold text-gray-900">
            {{ temperatureLabel }}
          </div>
          <div class="text-lg text-gray-600 mt-1">
            {{ weather.weather }}
          </div>
        </div>
      </div>
    </div>

    <!-- Weather Details Grid -->
    <div class="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200">
      <!-- Humidity -->
      <div class="flex items-center space-x-3">
        <div
          class="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center"
        >
          <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
            />
          </svg>
        </div>
        <div>
          <div class="text-sm text-gray-500">Humidity</div>
          <div class="text-lg font-semibold text-gray-900">
            {{ humidityLabel }}
          </div>
        </div>
      </div>

      <!-- Wind -->
      <div class="flex items-center space-x-3">
        <div
          class="flex-shrink-0 w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center"
        >
          <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M14 5l7 7m0 0l-7 7m7-7H3"
            />
          </svg>
        </div>
        <div>
          <div class="text-sm text-gray-500">Wind</div>
          <div class="text-lg font-semibold text-gray-900">
            {{ weather.wind_direction }} {{ weather.wind_power }}
          </div>
        </div>
      </div>
    </div>

    <!-- Footer with Report Time -->
    <div class="pt-4 border-t border-gray-200">
      <p class="text-xs text-gray-500 text-center">Updated: {{ formattedTime }}</p>
    </div>
  </div>
</template>

<style scoped>
.weather-card {
  min-height: 300px;
}
</style>
