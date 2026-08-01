<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useEmailStore } from '@/stores/email'
import AppLayout from '@/components/layout/AppLayout.vue'
import type { EmailPreferencesUpdate } from '@/types/email'

const emailStore = useEmailStore()

// Form state
const preferencesForm = ref<EmailPreferencesUpdate>({
  email_notifications_enabled: false,
  email_send_time: undefined,
  email_additional_recipients: [],
  email_preferred_city: undefined,
})

const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)
const additionalRecipientsInput = ref('')

// Time options (every hour)
const timeOptions = Array.from({ length: 24 }, (_, i) => {
  const hour = i.toString().padStart(2, '0')
  return { value: `${hour}:00`, label: `${hour}:00` }
})

// Load current preferences
onMounted(async () => {
  await loadPreferences()
})

async function loadPreferences() {
  loading.value = true
  error.value = null
  try {
    const prefs = await emailStore.fetchPreferences()
    if (prefs) {
      preferencesForm.value = {
        email_notifications_enabled: prefs.email_notifications_enabled,
        email_send_time: prefs.email_send_time || undefined,
        email_additional_recipients: prefs.email_additional_recipients || [],
        email_preferred_city: prefs.email_preferred_city || undefined,
      }
      additionalRecipientsInput.value = (prefs.email_additional_recipients || []).join(', ')
    }
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to load email preferences'
  } finally {
    loading.value = false
  }
}

function updateAdditionalRecipients() {
  const emails = additionalRecipientsInput.value
    .split(',')
    .map((e) => e.trim())
    .filter((e) => e)
  preferencesForm.value.email_additional_recipients = emails
}

function validateEmails(emails: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  const emailList = emails
    .split(',')
    .map((e) => e.trim())
    .filter((e) => e)
  return emailList.length === 0 || emailList.every((e) => emailRegex.test(e))
}

async function savePreferences() {
  saving.value = true
  error.value = null
  successMessage.value = null

  // Validate emails
  if (additionalRecipientsInput.value && !validateEmails(additionalRecipientsInput.value)) {
    error.value = 'Please enter valid email addresses (comma-separated)'
    saving.value = false
    return
  }

  updateAdditionalRecipients()

  try {
    await emailStore.updatePreferences(preferencesForm.value)
    successMessage.value = '✅ Email preferences updated successfully!'

    setTimeout(() => {
      successMessage.value = null
    }, 3000)
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to update email preferences'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppLayout>
    <div
      class="email-preferences-page min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4"
    >
      <div class="max-w-2xl mx-auto">
        <!-- Header -->
        <div class="text-center mb-8">
          <h1 class="text-4xl font-bold text-gray-900 mb-2">📧 Email Preferences</h1>
          <p class="text-gray-600">Configure your email notification settings</p>
        </div>

        <!-- Form -->
        <div class="bg-white rounded-xl shadow-md p-6">
          <div v-if="loading" class="text-center py-8">
            <div
              class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"
            />
            <p class="mt-2 text-gray-600">Loading preferences...</p>
          </div>

          <form v-else class="space-y-6" @submit.prevent="savePreferences">
            <!-- Enable/Disable Toggle -->
            <div class="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div>
                <label class="text-sm font-medium text-gray-900">Enable Email Notifications</label>
                <p class="text-xs text-gray-500 mt-1">Receive daily AI Recommendations via email</p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input
                  v-model="preferencesForm.email_notifications_enabled"
                  type="checkbox"
                  class="sr-only peer"
                />
                <div
                  class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"
                />
              </label>
            </div>

            <!-- Send Time -->
            <div v-if="preferencesForm.email_notifications_enabled">
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Preferred Send Time
              </label>
              <select
                v-model="preferencesForm.email_send_time"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option :value="null">Select time...</option>
                <option v-for="time in timeOptions" :key="time.value" :value="time.value">
                  {{ time.label }}
                </option>
              </select>
              <p class="mt-1 text-xs text-gray-500">Daily emails will be sent at this time</p>
            </div>

            <!-- Preferred City -->
            <div v-if="preferencesForm.email_notifications_enabled">
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Preferred City for Recommendations
              </label>
              <input
                v-model="preferencesForm.email_preferred_city"
                type="text"
                placeholder="Enter city AD code (e.g., 430100)"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <p class="mt-1 text-xs text-gray-500">City AD code for daily email recommendations</p>
            </div>

            <!-- Additional Recipients -->
            <div v-if="preferencesForm.email_notifications_enabled">
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Additional Email Recipients (Optional)
              </label>
              <input
                v-model="additionalRecipientsInput"
                type="text"
                placeholder="email1@example.com, email2@example.com"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                @blur="updateAdditionalRecipients"
              />
              <p class="mt-1 text-xs text-gray-500">
                Enter comma-separated email addresses to also receive recommendations
              </p>
            </div>

            <!-- Error Message -->
            <div v-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4">
              <p class="text-sm text-red-800">
                {{ error }}
              </p>
            </div>

            <!-- Success Message -->
            <div v-if="successMessage" class="bg-green-50 border border-green-200 rounded-lg p-4">
              <p class="text-sm text-green-800">
                {{ successMessage }}
              </p>
            </div>

            <!-- Save Button -->
            <button
              type="submit"
              :disabled="saving"
              class="w-full bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {{ saving ? '⏳ Saving...' : '💾 Save Preferences' }}
            </button>
          </form>
        </div>

        <!-- Info Box -->
        <div class="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 class="text-sm font-semibold text-blue-900 mb-2">ℹ️ About Email Notifications</h3>
          <ul class="text-sm text-blue-800 space-y-1 list-disc list-inside">
            <li>Daily emails are sent at your preferred time</li>
            <li>Emails include personalized recommendations based on weather and your profile</li>
            <li>You can also manually send emails from the Recommendations page</li>
            <li>All email deliveries are logged for your reference</li>
          </ul>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
.email-preferences-page {
  min-height: calc(100vh - 64px);
}
</style>
