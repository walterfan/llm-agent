<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import { useSecretaryStore } from '@/stores/secretary'

const secretaryStore = useSecretaryStore()

const timezone = ref('Asia/Shanghai')
const result = ref<string | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const timezones = [
  'Asia/Shanghai',
  'Asia/Tokyo',
  'Asia/Singapore',
  'America/New_York',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Paris',
  'UTC',
]

async function getDateTime() {
  loading.value = true
  error.value = null
  result.value = null

  try {
    const response = await secretaryStore.getDateTime(`现在${timezone.value}时区的时间是？`)
    result.value = response
  } catch (err: any) {
    error.value = err.message || 'Failed to get datetime'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  getDateTime()
})
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <AppHeader />

    <div class="max-w-2xl mx-auto px-4 py-8">
      <h1 class="text-2xl font-bold text-gray-800 mb-2">🕐 Date & Time Tool</h1>
      <p class="text-gray-600 mb-6">Get the current date and time for different timezones.</p>

      <!-- Input -->
      <div class="bg-white rounded-lg shadow p-6 mb-6">
        <label class="block text-sm font-medium text-gray-700 mb-2"> Timezone </label>
        <div class="flex gap-2">
          <select
            v-model="timezone"
            class="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option v-for="tz in timezones" :key="tz" :value="tz">
              {{ tz }}
            </option>
          </select>
          <button
            type="button"
            :disabled="loading"
            class="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            @click="getDateTime"
          >
            {{ loading ? 'Loading...' : 'Get Time' }}
          </button>
        </div>
      </div>

      <!-- Result -->
      <div v-if="result || error" class="bg-white rounded-lg shadow p-6">
        <h3 class="text-sm font-medium text-gray-500 mb-2">Result</h3>
        <div v-if="error" class="text-red-600">
          {{ error }}
        </div>
        <div v-else class="text-lg text-gray-800 whitespace-pre-wrap">
          {{ result }}
        </div>
      </div>
    </div>
  </div>
</template>
