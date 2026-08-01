<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import type { UserProfileUpdate } from '@/types/user'
import AppLayout from '@/components/layout/AppLayout.vue'
import ButtonComponent from '@/components/forms/ButtonComponent.vue'

const authStore = useAuthStore()

// Form state
const profileForm = ref<UserProfileUpdate>({
  gender: null,
  age: null,
  identity: null,
  style: null,
  temperature_sensitivity: null,
  activity_context: null,
  other_preferences: null,
})

const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)

// Options for select fields
const genderOptions = ['男', '女', '其他']
const identityOptions = ['大学生', '上班族', '退休人员', '自由职业', '其他']
const styleOptions = ['舒适优先', '时尚优先', '运动风', '商务风', '休闲风', '其他']
const temperatureSensitivityOptions = ['非常怕冷', '怕冷', '正常', '怕热', '非常怕热']
const activityContextOptions = ['工作日', '周末', '假期', '出游', '居家', '运动', '其他']

// Load current profile
onMounted(async () => {
  await loadProfile()
})

async function loadProfile() {
  loading.value = true
  error.value = null
  try {
    await authStore.loadUser()
    const user = authStore.currentUser

    // Populate form with existing data
    if (user) {
      profileForm.value = {
        gender: user.gender || null,
        age: user.age || null,
        identity: user.identity || null,
        style: user.style || null,
        temperature_sensitivity: user.temperature_sensitivity || null,
        activity_context: user.activity_context || null,
        other_preferences: user.other_preferences || null,
      }
    }
  } catch (err: any) {
    error.value = err.message || 'Failed to load profile'
  } finally {
    loading.value = false
  }
}

async function saveProfile() {
  saving.value = true
  error.value = null
  successMessage.value = null

  try {
    await authStore.updateDressProfile(profileForm.value)

    successMessage.value = '✅ Profile updated successfully!'

    // Clear success message after 3 seconds
    setTimeout(() => {
      successMessage.value = null
    }, 3000)
  } catch (err: any) {
    error.value = err.message || 'Failed to update profile'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppLayout>
    <div class="max-w-4xl mx-auto py-8 px-4">
      <!-- Header -->
      <div class="mb-8 flex justify-between items-start">
        <div>
          <h1 class="text-3xl font-bold text-gray-900 mb-2">穿衣偏好设置</h1>
          <p class="text-gray-600">
            Tell us about your preferences to get personalized AI Recommendations
          </p>
        </div>
        <RouterLink
          to="/profile/email-preferences"
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 shadow-sm"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5 mr-2"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
            />
          </svg>
          Email Preferences
        </RouterLink>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="flex justify-center items-center py-12">
        <svg
          class="animate-spin h-12 w-12 text-blue-600"
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

      <!-- Form -->
      <form v-else class="space-y-6" @submit.prevent="saveProfile">
        <!-- Success Message -->
        <div
          v-if="successMessage"
          class="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center"
        >
          <svg class="w-5 h-5 text-green-600 mr-3" fill="currentColor" viewBox="0 0 20 20">
            <path
              fill-rule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clip-rule="evenodd"
            />
          </svg>
          <span class="text-green-800">{{ successMessage }}</span>
        </div>

        <!-- Error Message -->
        <div v-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start">
          <svg class="w-5 h-5 text-red-600 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
            <path
              fill-rule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clip-rule="evenodd"
            />
          </svg>
          <span class="text-red-800">{{ error }}</span>
        </div>

        <!-- Form Fields -->
        <div class="bg-white shadow rounded-lg p-6 space-y-6">
          <!-- Gender & Age Row -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2"> 性别 Gender </label>
              <select
                v-model="profileForm.gender"
                class="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option :value="null">Select...</option>
                <option v-for="option in genderOptions" :key="option" :value="option">
                  {{ option }}
                </option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2"> 年龄 Age </label>
              <input
                v-model.number="profileForm.age"
                type="number"
                min="0"
                max="150"
                class="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                placeholder="Enter your age"
              />
            </div>
          </div>

          <!-- Identity -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2"> 身份 Identity </label>
            <select
              v-model="profileForm.identity"
              class="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              <option :value="null">Select...</option>
              <option v-for="option in identityOptions" :key="option" :value="option">
                {{ option }}
              </option>
            </select>
          </div>

          <!-- Style -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              穿衣风格 Style Preference
            </label>
            <select
              v-model="profileForm.style"
              class="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              <option :value="null">Select...</option>
              <option v-for="option in styleOptions" :key="option" :value="option">
                {{ option }}
              </option>
            </select>
          </div>

          <!-- Temperature Sensitivity -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              温度敏感度 Temperature Sensitivity
            </label>
            <select
              v-model="profileForm.temperature_sensitivity"
              class="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              <option :value="null">Select...</option>
              <option v-for="option in temperatureSensitivityOptions" :key="option" :value="option">
                {{ option }}
              </option>
            </select>
          </div>

          <!-- Activity Context -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              活动场景 Activity Context
            </label>
            <select
              v-model="profileForm.activity_context"
              class="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              <option :value="null">Select...</option>
              <option v-for="option in activityContextOptions" :key="option" :value="option">
                {{ option }}
              </option>
            </select>
          </div>

          <!-- Other Preferences -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              其他偏好 Other Preferences
            </label>
            <textarea
              v-model="profileForm.other_preferences"
              rows="4"
              class="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              placeholder="Any other clothing preferences or notes (e.g., favorite colors, brands, etc.)"
            />
            <p class="mt-1 text-sm text-gray-500">
              Optional: Share any specific preferences that will help us make better recommendations
            </p>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex justify-end space-x-4">
          <button
            type="button"
            class="px-6 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            :disabled="saving"
            @click="loadProfile"
          >
            Reset
          </button>
          <ButtonComponent type="submit" :loading="saving">
            {{ saving ? 'Saving...' : 'Save Profile' }}
          </ButtonComponent>
        </div>
      </form>
    </div>
  </AppLayout>
</template>
