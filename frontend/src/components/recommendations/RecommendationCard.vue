<script setup lang="ts">
import { computed } from 'vue'
import type { RecommendationResponse } from '@/types/recommendation'

const props = defineProps<{
  recommendation: RecommendationResponse
}>()

const formattedDate = computed(() => {
  const date = new Date(props.recommendation.created_at)
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
})

const temperatureDisplay = computed(() => {
  return `${props.recommendation.weather_data.temperature}°C`
})
</script>

<template>
  <div class="recommendation-card bg-white rounded-xl shadow-lg p-6 mb-6">
    <!-- Header -->
    <div class="flex items-start justify-between mb-4">
      <div>
        <h3 class="text-2xl font-bold text-gray-900">
          {{ recommendation.weather_data.city }}
        </h3>
        <p class="text-sm text-gray-500">
          {{ formattedDate }}
        </p>
      </div>
      <div class="text-right">
        <div class="text-3xl font-bold text-blue-600">
          {{ temperatureDisplay }}
        </div>
        <p class="text-sm text-gray-600">
          {{ recommendation.weather_data.weather }}
        </p>
      </div>
    </div>

    <!-- Weather Info -->
    <div class="bg-blue-50 rounded-lg p-4 mb-4">
      <div class="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span class="text-gray-600">Humidity:</span>
          <span class="ml-2 font-medium">{{ recommendation.weather_data.humidity }}%</span>
        </div>
        <div>
          <span class="text-gray-600">Wind:</span>
          <span class="ml-2 font-medium">
            {{ recommendation.weather_data.wind_direction }}
            {{ recommendation.weather_data.wind_power }}级
          </span>
        </div>
      </div>
    </div>

    <!-- Clothing Items -->
    <div class="mb-4">
      <h4 class="text-lg font-semibold text-gray-800 mb-2">推荐穿搭</h4>
      <div class="flex flex-wrap gap-2">
        <span
          v-for="(item, index) in recommendation.clothing_items"
          :key="index"
          class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800"
        >
          {{ item }}
        </span>
      </div>
    </div>

    <!-- Advice -->
    <div class="mb-4">
      <h4 class="text-lg font-semibold text-gray-800 mb-2">穿衣建议</h4>
      <p class="text-gray-700 leading-relaxed whitespace-pre-wrap">
        {{ recommendation.advice }}
      </p>
    </div>

    <!-- Weather Warnings -->
    <div v-if="recommendation.weather_warnings" class="mb-4">
      <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded">
        <div class="flex items-start">
          <svg class="w-5 h-5 text-yellow-400 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
            <path
              fill-rule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clip-rule="evenodd"
            />
          </svg>
          <p class="text-sm text-yellow-700">
            {{ recommendation.weather_warnings }}
          </p>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-between text-sm text-gray-500 pt-4 border-t">
      <div class="flex items-center space-x-4">
        <span v-if="recommendation.emoji_summary" class="text-2xl">
          {{ recommendation.emoji_summary }}
        </span>
        <span v-if="recommendation.cached" class="text-blue-600"> (Cached) </span>
      </div>
      <div v-if="recommendation.cost_estimate">
        <span class="text-gray-400">Cost:</span>
        <span class="ml-1 font-medium">${{ recommendation.cost_estimate.toFixed(4) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.recommendation-card {
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}

.recommendation-card:hover {
  transform: translateY(-2px);
  box-shadow:
    0 20px 25px -5px rgb(0 0 0 / 0.1),
    0 8px 10px -6px rgb(0 0 0 / 0.1);
}
</style>
