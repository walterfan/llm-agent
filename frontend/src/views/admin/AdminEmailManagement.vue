<template>
  <AppLayout>
    <div class="admin-email-management max-w-4xl mx-auto">
      <div class="mb-6">
        <h1 class="text-3xl font-bold text-gray-900">Manage User Email Settings</h1>
        <p class="mt-2 text-gray-600">Configure email notifications for users</p>
      </div>

      <!-- User selector -->
      <div class="bg-white rounded-lg shadow p-6 mb-6">
        <UserSelector @select="handleUserSelect" />
      </div>

      <!-- Preferences form (shown when user selected) -->
      <div v-if="selectedUserId" class="bg-white rounded-lg shadow p-6">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-xl font-semibold">Email Settings for User #{{ selectedUserId }}</h2>
          <button
            :disabled="testEmailLoading"
            class="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
            @click="handleTestEmail"
          >
            {{ testEmailLoading ? 'Sending...' : 'Send Test Email' }}
          </button>
        </div>

        <!-- Success/Error messages -->
        <div v-if="testEmailSuccess" class="mb-4 bg-green-50 border border-green-200 rounded p-3">
          <p class="text-green-800">
            {{ testEmailSuccess }}
          </p>
        </div>
        <div v-if="testEmailError" class="mb-4 bg-red-50 border border-red-200 rounded p-3">
          <p class="text-red-800">
            {{ testEmailError }}
          </p>
        </div>

        <!-- Form (reuse same components as user preferences) -->
        <form class="space-y-6" @submit.prevent="handleSubmit">
          <!-- Enable toggle -->
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium">Email Notifications</span>
            <button
              type="button"
              :class="[
                'relative inline-flex h-6 w-11 rounded-full',
                formData.email_notifications_enabled ? 'bg-blue-600' : 'bg-gray-200',
              ]"
              @click="formData.email_notifications_enabled = !formData.email_notifications_enabled"
            >
              <span
                :class="[
                  'inline-block h-5 w-5 transform rounded-full bg-white',
                  formData.email_notifications_enabled ? 'translate-x-5' : 'translate-x-0',
                ]"
              />
            </button>
          </div>

          <div v-if="formData.email_notifications_enabled" class="space-y-6">
            <TimePicker v-model="formData.email_send_time" label="Send Time" />
            <CitySearch v-model="formData.email_preferred_city" />
            <RecipientList
              v-model="formData.email_additional_recipients"
              label="Additional Recipients"
            />
          </div>

          <button
            type="submit"
            :disabled="submitting"
            class="w-full px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {{ submitting ? 'Saving...' : 'Save Changes' }}
          </button>
        </form>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useEmailPreferencesStore } from '@/stores/emailPreferences'
import AppLayout from '@/components/layout/AppLayout.vue'
import UserSelector from '@/components/admin/UserSelector.vue'
import TimePicker from '@/components/email/TimePicker.vue'
import RecipientList from '@/components/email/RecipientList.vue'
import CitySearch from '@/components/weather/CitySearch.vue'

const store = useEmailPreferencesStore()
const selectedUserId = ref<number | null>(null)
const submitting = ref(false)
const formData = ref({
  email_notifications_enabled: false,
  email_send_time: '08:00',
  email_additional_recipients: [] as string[],
  email_preferred_city: null as string | null,
})

const testEmailLoading = computed(() => store.testEmailLoading)
const testEmailError = computed(() => store.testEmailError)
const testEmailSuccess = computed(() => store.testEmailSuccess)

async function handleUserSelect(user: { id: number } | null) {
  if (!user) {
    selectedUserId.value = null
    return
  }

  selectedUserId.value = user.id
  await store.fetchAdminPreferences(user.id)
  if (store.preferences) {
    formData.value = {
      email_notifications_enabled: store.preferences.email_notifications_enabled,
      email_send_time: store.preferences.email_send_time || '08:00',
      email_additional_recipients: store.preferences.email_additional_recipients || [],
      email_preferred_city: store.preferences.email_preferred_city,
    }
  }
}

async function handleSubmit() {
  if (!selectedUserId.value) return
  submitting.value = true
  await store.updateAdminPreferences(selectedUserId.value, formData.value)
  submitting.value = false
}

async function handleTestEmail() {
  if (!selectedUserId.value) return
  await store.testEmail(selectedUserId.value)
}
</script>
