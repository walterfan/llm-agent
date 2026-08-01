<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import type { City } from '@/types/city'
import { useWeatherStore } from '@/stores/weather'

const weatherStore = useWeatherStore()

interface Emits {
  (e: 'select', city: City): void
}

const emit = defineEmits<Emits>()

// State
const searchQuery = ref('')
const cities = ref<City[]>([])
const loading = ref(false)
const showDropdown = ref(false)
const error = ref<string | null>(null)

// Debounced search function
const debouncedSearch = useDebounceFn(async () => {
  if (!searchQuery.value || searchQuery.value.length < 1) {
    cities.value = []
    showDropdown.value = false
    return
  }

  loading.value = true
  error.value = null

  try {
    cities.value = await weatherStore.searchCities(searchQuery.value, 10)
    showDropdown.value = cities.value.length > 0
  } catch (err: any) {
    error.value = err.message || 'Failed to search cities'
    cities.value = []
    showDropdown.value = false
  } finally {
    loading.value = false
  }
}, 300)

// Watch search query
watch(searchQuery, () => {
  debouncedSearch()
})

// Select city
function selectCity(city: City) {
  searchQuery.value = city.display_name
  showDropdown.value = false
  emit('select', city)
}

// Clear search
function clearSearch() {
  searchQuery.value = ''
  cities.value = []
  showDropdown.value = false
  error.value = null
}

// Hide dropdown when clicking outside
function handleBlur() {
  // Delay to allow click event on dropdown items
  setTimeout(() => {
    showDropdown.value = false
  }, 200)
}

const hasResults = computed(() => cities.value.length > 0)
</script>

<template>
  <div class="city-search relative w-full">
    <!-- Search Input -->
    <div class="relative">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search city (e.g., 北京, Beijing, 340100)"
        class="w-full px-4 py-3 pr-12 text-gray-900 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        @focus="showDropdown = hasResults"
        @blur="handleBlur"
      />

      <!-- Loading Spinner -->
      <div v-if="loading" class="absolute right-4 top-1/2 transform -translate-y-1/2">
        <svg
          class="animate-spin h-5 w-5 text-blue-500"
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
      </div>

      <!-- Clear Button -->
      <button
        v-else-if="searchQuery"
        type="button"
        class="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
        @click="clearSearch"
      >
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

    <!-- Dropdown Results -->
    <div
      v-if="showDropdown && hasResults"
      class="absolute z-10 w-full mt-2 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto"
    >
      <ul class="py-1">
        <li
          v-for="city in cities"
          :key="city.ad_code"
          class="px-4 py-2 hover:bg-blue-50 cursor-pointer transition-colors"
          @click="selectCity(city)"
        >
          <div class="flex justify-between items-center">
            <div>
              <div class="font-medium text-gray-900">
                {{ city.location_name_zh }}
                <span v-if="city.location_name_en" class="text-sm text-gray-500 ml-2">
                  {{ city.location_name_en }}
                </span>
              </div>
              <div class="text-sm text-gray-500">{{ city.province_zh }} · {{ city.ad_code }}</div>
            </div>
          </div>
        </li>
      </ul>
    </div>

    <!-- Error Message -->
    <div v-if="error" class="mt-2 text-sm text-red-600">
      {{ error }}
    </div>

    <!-- No Results -->
    <div v-if="searchQuery && !loading && !hasResults && !error" class="mt-2 text-sm text-gray-500">
      No cities found for "{{ searchQuery }}"
    </div>
  </div>
</template>

<style scoped>
/* Custom scrollbar for dropdown */
.overflow-y-auto::-webkit-scrollbar {
  width: 8px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>
