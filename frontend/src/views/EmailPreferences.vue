<template>
  <AppLayout>
    <div class="email-preferences-page max-w-4xl mx-auto">
      <div class="mb-6">
        <h1 class="text-3xl font-bold text-gray-900">Email Preferences</h1>
        <p class="mt-2 text-gray-600">
          Configure when and where to receive your daily AI Recommendations.
        </p>
      </div>

      <!-- Loading state -->
      <div v-if="loading" class="bg-white rounded-lg shadow p-6">
        <div class="animate-pulse space-y-4">
          <div class="h-4 bg-gray-200 rounded w-3/4" />
          <div class="h-4 bg-gray-200 rounded w-1/2" />
        </div>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <p class="text-red-800">
          {{ error }}
        </p>
        <button
          class="mt-2 text-sm text-red-600 hover:text-red-800 underline"
          @click="loadPreferences"
        >
          Retry
        </button>
      </div>

      <!-- Preferences form -->
      <form v-else class="bg-white rounded-lg shadow" @submit.prevent="handleSubmit">
        <div class="p-6 space-y-6">
          <!-- Enable notifications toggle -->
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-medium text-gray-900">Email Notifications</h3>
              <p class="text-sm text-gray-500">Receive daily AI Recommendations via email</p>
            </div>
            <button
              type="button"
              :class="[
                'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                formData.email_notifications_enabled ? 'bg-blue-600' : 'bg-gray-200',
              ]"
              @click="toggleNotifications"
            >
              <span
                :class="[
                  'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                  formData.email_notifications_enabled ? 'translate-x-5' : 'translate-x-0',
                ]"
              />
            </button>
          </div>

          <div
            v-if="formData.email_notifications_enabled"
            class="space-y-6 pt-4 border-t border-gray-200"
          >
            <!-- Send time -->
            <TimePicker
              v-model="formData.email_send_time"
              label="Send Time"
              :minute-step="15"
              hint="Choose when you'd like to receive your daily recommendations"
            />

            <!-- Preferred city -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2"> Preferred City </label>
              <CitySearch
                v-model="formData.email_preferred_city"
                placeholder="Search for a city..."
                :required="formData.email_notifications_enabled"
              />
              <p class="mt-1 text-sm text-gray-500">
                The city for which you'll receive weather-based AI Recommendations
              </p>
            </div>

            <!-- Additional recipients -->
            <RecipientList
              v-model="formData.email_additional_recipients"
              label="Additional Recipients (Optional)"
              hint="Add family members or friends who should also receive your recommendations"
              :max-recipients="5"
            />
          </div>
        </div>

        <!-- Form actions -->
        <div class="bg-gray-50 px-6 py-4 flex items-center justify-between rounded-b-lg">
          <button
            v-if="hasChanges"
            type="button"
            class="px-4 py-2 text-gray-700 hover:text-gray-900"
            @click="resetForm"
          >
            Cancel
          </button>
          <div v-else />

          <button
            type="submit"
            :disabled="submitting || !hasChanges"
            class="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ submitting ? 'Saving...' : 'Save Preferences' }}
          </button>
        </div>
      </form>

      <!-- Success message -->
      <div v-if="showSuccess" class="mt-4 bg-green-50 border border-green-200 rounded-lg p-4">
        <p class="text-green-800">✓ Email preferences saved successfully!</p>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useEmailPreferencesStore } from '@/stores/emailPreferences'
import AppLayout from '@/components/layout/AppLayout.vue'
import TimePicker from '@/components/email/TimePicker.vue'
import RecipientList from '@/components/email/RecipientList.vue'
import CitySearch from '@/components/weather/CitySearch.vue'

const store = useEmailPreferencesStore()

// State
const formData = ref({
  email_notifications_enabled: false,
  email_send_time: '08:00',
  email_additional_recipients: [] as string[],
  email_preferred_city: null as string | null,
})

const originalData = ref({ ...formData.value })
const submitting = ref(false)
const showSuccess = ref(false)

// Computed
const loading = computed(() => store.loading)
const error = computed(() => store.error)
const hasChanges = computed(() => {
  return JSON.stringify(formData.value) !== JSON.stringify(originalData.value)
})

// Methods
function toggleNotifications() {
  formData.value.email_notifications_enabled = !formData.value.email_notifications_enabled
}

async function loadPreferences() {
  await store.fetchPreferences()
  if (store.preferences) {
    formData.value = {
      email_notifications_enabled: store.preferences.email_notifications_enabled,
      email_send_time: store.preferences.email_send_time || '08:00',
      email_additional_recipients: store.preferences.email_additional_recipients || [],
      email_preferred_city: store.preferences.email_preferred_city,
    }
    originalData.value = { ...formData.value }
  }
}

function resetForm() {
  formData.value = { ...originalData.value }
}

async function handleSubmit() {
  submitting.value = true
  showSuccess.value = false

  const success = await store.updatePreferences({
    email_notifications_enabled: formData.value.email_notifications_enabled,
    email_send_time: formData.value.email_notifications_enabled
      ? formData.value.email_send_time
      : null,
    email_additional_recipients: formData.value.email_notifications_enabled
      ? formData.value.email_additional_recipients
      : [],
    email_preferred_city: formData.value.email_notifications_enabled
      ? formData.value.email_preferred_city
      : null,
  })

  if (success) {
    originalData.value = { ...formData.value }
    showSuccess.value = true
    setTimeout(() => {
      showSuccess.value = false
    }, 3000)
  }

  submitting.value = false
}

// Lifecycle
onMounted(() => {
  loadPreferences()
})
</script>

<style scoped>
/* Component styles are in Tailwind classes */
</style>
