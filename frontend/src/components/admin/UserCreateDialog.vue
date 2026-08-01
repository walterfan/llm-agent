<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
    @click.self="close"
  >
    <div class="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
      <h2 class="mb-4 text-xl font-semibold text-gray-900">Create New User</h2>

      <form @submit.prevent="handleSubmit">
        <!-- Email -->
        <div class="mb-4">
          <label for="email" class="mb-1 block text-sm font-medium text-gray-700">Email *</label>
          <input
            id="email"
            v-model="formData.email"
            type="email"
            required
            class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="user@example.com"
          />
        </div>

        <!-- Password -->
        <div class="mb-4">
          <label for="password" class="mb-1 block text-sm font-medium text-gray-700"
            >Password *</label
          >
          <input
            id="password"
            v-model="formData.password"
            type="password"
            required
            minlength="8"
            class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="Minimum 8 characters"
          />
        </div>

        <!-- Full Name -->
        <div class="mb-4">
          <label for="full_name" class="mb-1 block text-sm font-medium text-gray-700"
            >Full Name</label
          >
          <input
            id="full_name"
            v-model="formData.full_name"
            type="text"
            class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="John Doe"
          />
        </div>

        <!-- Role -->
        <div class="mb-4">
          <label for="role" class="mb-1 block text-sm font-medium text-gray-700">Role</label>
          <select
            id="role"
            v-model="formData.role"
            class="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option :value="UserRole.USER">User</option>
            <option :value="UserRole.ADMIN">Admin</option>
            <option :value="UserRole.SUPER_ADMIN">Super Admin</option>
            <option :value="UserRole.GUEST">Guest</option>
          </select>
        </div>

        <!-- Active Status -->
        <div class="mb-6 flex items-center">
          <input
            id="is_active"
            v-model="formData.is_active"
            type="checkbox"
            class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <label for="is_active" class="ml-2 text-sm text-gray-700">Active account</label>
        </div>

        <!-- Error Message -->
        <div v-if="error" class="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          {{ error }}
        </div>

        <!-- Actions -->
        <div class="flex justify-end space-x-3">
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
            {{ loading ? 'Creating...' : 'Create User' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { UserRole } from '@/types/rbac'
import type { UserAdminCreate } from '@/types/rbac'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  close: []
  submit: [userData: UserAdminCreate]
}>()

const formData = ref<UserAdminCreate>({
  email: '',
  password: '',
  full_name: null,
  role: UserRole.USER,
  is_active: true,
})

const loading = ref(false)
const error = ref<string | null>(null)

// Reset form when dialog opens
watch(
  () => props.isOpen,
  (isOpen) => {
    if (isOpen) {
      formData.value = {
        email: '',
        password: '',
        full_name: null,
        role: UserRole.USER,
        is_active: true,
      }
      error.value = null
    }
  }
)

function close() {
  emit('close')
}

async function handleSubmit() {
  loading.value = true
  error.value = null

  try {
    emit('submit', formData.value)
  } catch (err: any) {
    error.value = err.message || 'Failed to create user'
  } finally {
    loading.value = false
  }
}
</script>
