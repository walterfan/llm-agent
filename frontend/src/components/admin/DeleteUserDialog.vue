<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
    @click.self="close"
  >
    <div class="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
      <h2 class="mb-4 text-xl font-semibold text-gray-900">Delete User</h2>

      <p class="mb-6 text-gray-600">
        Are you sure you want to delete user
        <span class="font-semibold">{{ user?.email }}</span
        >? This action cannot be undone.
      </p>

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
          type="button"
          :disabled="loading"
          class="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          @click="handleDelete"
        >
          {{ loading ? 'Deleting...' : 'Delete User' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { User } from '@/types/rbac'

const props = defineProps<{
  isOpen: boolean
  user: User | null
}>()

const emit = defineEmits<{
  close: []
  confirm: [userId: number]
}>()

const loading = ref(false)
const error = ref<string | null>(null)

function close() {
  error.value = null
  emit('close')
}

async function handleDelete() {
  if (!props.user) return

  loading.value = true
  error.value = null

  try {
    emit('confirm', props.user.id)
  } catch (err: any) {
    error.value = err.message || 'Failed to delete user'
  } finally {
    loading.value = false
  }
}
</script>
