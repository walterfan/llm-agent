<script setup lang="ts">
import { ref } from 'vue'
import type { DailyRecommendation } from '@/types/recommendation'

// Props are used in the template
defineProps<{
  dailyRecommendations: DailyRecommendation[]
}>()

const activeTab = ref<number>(0)

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    month: 'long',
    day: 'numeric',
  })
}
</script>

<template>
  <div class="multi-day-display">
    <!-- Tab Navigation -->
    <div class="border-b border-gray-200 mb-6">
      <nav class="flex space-x-4" aria-label="Tabs">
        <button
          v-for="(day, index) in dailyRecommendations"
          :key="index"
          :class="[
            'px-4 py-3 text-sm font-medium border-b-2 transition-colors',
            activeTab === index
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
          @click="activeTab = index"
        >
          <div class="text-center">
            <div class="font-bold">
              {{ day.date_label }}
            </div>
            <div class="text-xs mt-1">
              {{ formatDate(day.date) }}
            </div>
          </div>
        </button>
      </nav>
    </div>

    <!-- Tab Content -->
    <div
      v-for="(day, index) in dailyRecommendations"
      v-show="activeTab === index"
      :key="index"
      class="tab-content"
    >
      <div class="bg-white rounded-xl shadow-lg p-6">
        <!-- Weather Summary -->
        <div class="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 mb-6">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-xl font-bold text-gray-900 mb-1">
                {{ day.date_label }} · {{ formatDate(day.date) }}
              </h3>
              <p class="text-gray-600">
                {{ day.weather_summary }}
              </p>
            </div>
            <div class="text-4xl">
              {{ day.recommendation.emoji_summary || '👔' }}
            </div>
          </div>
        </div>

        <!-- Clothing Items -->
        <div class="mb-6">
          <h4 class="text-lg font-semibold text-gray-800 mb-3 flex items-center">
            <span class="mr-2">👔</span>
            推荐穿搭
          </h4>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="(item, idx) in day.recommendation.clothing_items"
              :key="idx"
              class="inline-flex items-center px-4 py-2 rounded-full text-sm font-medium bg-blue-100 text-blue-800"
            >
              {{ item }}
            </span>
          </div>
        </div>

        <!-- Advice -->
        <div class="mb-6">
          <h4 class="text-lg font-semibold text-gray-800 mb-3 flex items-center">
            <span class="mr-2">💡</span>
            穿搭建议
          </h4>
          <div class="bg-gray-50 rounded-lg p-4">
            <p class="text-gray-700 leading-relaxed whitespace-pre-wrap">
              {{ day.recommendation.advice }}
            </p>
          </div>
        </div>

        <!-- Weather Warnings -->
        <div
          v-if="
            day.recommendation.weather_warnings && day.recommendation.weather_warnings.length > 0
          "
          class="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded"
        >
          <div class="flex items-start">
            <span class="text-2xl mr-3">⚠️</span>
            <div>
              <h4 class="text-sm font-semibold text-yellow-800 mb-2">特别提醒</h4>
              <p class="text-sm text-yellow-700">
                {{ day.recommendation.weather_warnings }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="dailyRecommendations.length === 0" class="text-center py-12 text-gray-500">
      <p>暂无推荐数据</p>
    </div>
  </div>
</template>

<style scoped>
.tab-content {
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
