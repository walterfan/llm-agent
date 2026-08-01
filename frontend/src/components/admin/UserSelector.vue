<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import type { User } from '@/types/user'
import axios from 'axios'

// Remove unused props since we're emitting 'select' event instead of using v-model
const emit = defineEmits<{
  (e: 'select', user: User | null): void
}>()

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const searchQuery = ref<string>('')
const users = ref<User[]>([])
const loading = ref<boolean>(false)
const showDropdown = ref<boolean>(false)
const selectedUser = ref<User | null>(null)

// Debounce helper function
function debounce<T extends (...args: any[]) => any>(fn: T, delay: number) {
  let timeoutId: ReturnType<typeof setTimeout> | null = null
  return function (this: any, ...args: Parameters<T>) {
    if (timeoutId) clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn.apply(this, args), delay)
  }
}

// Search users with debounce
const searchUsers = debounce(async (query: string) => {
  if (query.length < 2) {
    users.value = []
    return
  }

  loading.value = true
  const token = localStorage.getItem('access_token')

  try {
    const response = await axios.get<{ items: User[]; total: number }>(
      `${API_BASE_URL}/api/v1/admin/users`,
      {
        headers: { Authorization: `Bearer ${token}` },
        params: {
          search: query,
          limit: 20,
        },
      }
    )
    users.value = response.data.items
  } catch (error) {
    console.error('Failed to search users:', error)
    users.value = []
  } finally {
    loading.value = false
  }
}, 300)

watch(searchQuery, (newQuery) => {
  searchUsers(newQuery)
})

function selectUser(user: User) {
  selectedUser.value = user
  searchQuery.value = `${user.full_name || user.email} (ID: ${user.id})`
  showDropdown.value = false
  emit('select', user)
}

function clearSelection() {
  selectedUser.value = null
  searchQuery.value = ''
  users.value = []
  emit('select', null)
}

function handleFocus() {
  showDropdown.value = true
  if (searchQuery.value.length >= 2) {
    searchUsers(searchQuery.value)
  }
}

function handleBlur() {
  // Delay to allow click on dropdown items
  setTimeout(() => {
    showDropdown.value = false
  }, 200)
}

// Load initial users
onMounted(async () => {
  const token = localStorage.getItem('access_token')
  try {
    const response = await axios.get<{ items: User[]; total: number }>(
      `${API_BASE_URL}/api/v1/admin/users`,
      {
        headers: { Authorization: `Bearer ${token}` },
        params: { limit: 10 },
      }
    )
    users.value = response.data.items
  } catch (error) {
    console.error('Failed to load users:', error)
  }
})
</script>

<template>
  <div class="user-selector relative">
    <label class="block text-sm font-medium text-gray-700 mb-2"> 选择用户 </label>

    <div class="relative">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索用户（姓名或邮箱）"
        class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        @focus="handleFocus"
        @blur="handleBlur"
      />

      <button
        v-if="selectedUser"
        class="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600"
        type="button"
        @click="clearSelection"
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

      <!-- Loading Spinner -->
      <div v-if="loading" class="absolute right-3 top-2.5">
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
    </div>

    <!-- Dropdown -->
    <div
      v-if="showDropdown && users.length > 0"
      class="absolute z-10 mt-1 w-full bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-auto"
    >
      <ul class="py-1">
        <li
          v-for="user in users"
          :key="user.id"
          class="px-4 py-2 hover:bg-blue-50 cursor-pointer transition-colors"
          @click="selectUser(user)"
        >
          <div class="flex items-center justify-between">
            <div>
              <div class="font-medium text-gray-900">
                {{ user.full_name || user.email }}
              </div>
              <div class="text-sm text-gray-500">
                {{ user.email }}
              </div>
            </div>
            <span class="text-xs text-gray-400">ID: {{ user.id }}</span>
          </div>
        </li>
      </ul>
    </div>

    <!-- No results -->
    <div
      v-if="showDropdown && !loading && searchQuery.length >= 2 && users.length === 0"
      class="absolute z-10 mt-1 w-full bg-white border border-gray-300 rounded-lg shadow-lg p-4 text-center text-gray-500"
    >
      未找到匹配的用户
    </div>
  </div>
</template>

<style scoped>
/* Add custom scrollbar for dropdown */
.overflow-auto::-webkit-scrollbar {
  width: 6px;
}

.overflow-auto::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 10px;
}

.overflow-auto::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 10px;
}

.overflow-auto::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>
