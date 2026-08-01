<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
    @click.self="close"
  >
    <div class="w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto">
      <h2 class="mb-4 text-xl font-semibold text-gray-900">Edit User Profile</h2>
      <p class="mb-6 text-sm text-gray-600">
        Editing preferences for: <span class="font-medium">{{ user?.email }}</span>
      </p>

      <form @submit.prevent="handleSubmit">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Gender -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Gender</label>
            <select
              v-model="formData.gender"
              class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option :value="null">Select...</option>
              <option v-for="option in genderOptions" :key="option" :value="option">
                {{ option }}
              </option>
            </select>
          </div>

          <!-- Age -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Age</label>
            <input
              v-model.number="formData.age"
              type="number"
              min="0"
              max="150"
              class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <!-- Identity -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Identity</label>
            <select
              v-model="formData.identity"
              class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option :value="null">Select...</option>
              <option v-for="option in identityOptions" :key="option" :value="option">
                {{ option }}
              </option>
            </select>
          </div>

          <!-- Style -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Style Preference</label>
            <select
              v-model="formData.style"
              class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option :value="null">Select...</option>
              <option v-for="option in styleOptions" :key="option" :value="option">
                {{ option }}
              </option>
            </select>
          </div>

          <!-- Temperature Sensitivity -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2"
              >Temperature Sensitivity</label
            >
            <select
              v-model="formData.temperature_sensitivity"
              class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option :value="null">Select...</option>
              <option v-for="option in temperatureSensitivityOptions" :key="option" :value="option">
                {{ option }}
              </option>
            </select>
          </div>

          <!-- Activity Context -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Activity Context</label>
            <select
              v-model="formData.activity_context"
              class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option :value="null">Select...</option>
              <option v-for="option in activityContextOptions" :key="option" :value="option">
                {{ option }}
              </option>
            </select>
          </div>
        </div>

        <!-- Other Preferences -->
        <div class="mt-6">
          <label class="block text-sm font-medium text-gray-700 mb-2">Other Preferences</label>
          <textarea
            v-model="formData.other_preferences"
            rows="3"
            class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="Any other notes..."
          />
        </div>

        <!-- Error Message -->
        <div v-if="error" class="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          {{ error }}
        </div>

        <!-- Actions -->
        <div class="mt-6 flex justify-end space-x-3">
          <button
            type="button"
            class="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            @click="close"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="loading"
            class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {{ loading ? 'Saving...' : 'Save Changes' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { User, UserAdminUpdate } from '@/types/rbac'

const props = defineProps<{
  isOpen: boolean
  user: User | null
}>()

const emit = defineEmits<{
  close: []
  submit: [userId: number, userData: UserAdminUpdate]
}>()

// Options
const genderOptions = ['男', '女', '其他']
const identityOptions = ['大学生', '上班族', '退休人员', '自由职业', '其他']
const styleOptions = ['舒适优先', '时尚优先', '运动风', '商务风']
const temperatureSensitivityOptions = ['非常怕冷', '怕冷', '正常', '怕热', '非常怕热']
const activityContextOptions = ['工作日', '周末', '假期', '出游', '居家']

// Form data matches UserAdminUpdate structure but only for profile fields
const formData = ref({
  gender: null as string | null,
  age: null as number | null,
  identity: null as string | null,
  style: null as string | null,
  temperature_sensitivity: null as string | null,
  activity_context: null as string | null,
  other_preferences: null as string | null,
})

const loading = ref(false)
const error = ref<string | null>(null)

// Populate form when dialog opens
watch(
  () => [props.isOpen, props.user] as const,
  ([isOpen, user]) => {
    if (isOpen && user && typeof user === 'object') {
      // Cast to any because User type might not have profile fields defined in frontend yet
      const u = user as any
      formData.value = {
        gender: u.gender || null,
        age: u.age || null,
        identity: u.identity || null,
        style: u.style || null,
        temperature_sensitivity: u.temperature_sensitivity || null,
        activity_context: u.activity_context || null,
        other_preferences: u.other_preferences || null,
      }
      error.value = null
    }
  },
  { deep: true }
)

function close() {
  emit('close')
}

async function handleSubmit() {
  if (!props.user) return

  loading.value = true
  error.value = null

  try {
    // Create update object with only profile fields
    const updateData: UserAdminUpdate = {
      ...formData.value,
    }

    emit('submit', props.user.id, updateData)
  } catch (err: any) {
    error.value = err.message || 'Failed to update profile'
  } finally {
    loading.value = false
  }
}
</script>
