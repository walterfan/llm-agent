<template>
  <div class="recipient-list">
    <label v-if="label" class="block text-sm font-medium text-gray-700 mb-2">
      {{ label }}
    </label>

    <!-- List of recipients -->
    <div v-if="recipients.length > 0" class="space-y-2 mb-3">
      <div
        v-for="(recipient, index) in recipients"
        :key="index"
        class="flex items-center gap-2 p-2 bg-gray-50 rounded-md"
      >
        <span class="flex-1 text-sm text-gray-700">{{ recipient }}</span>
        <button
          type="button"
          :disabled="disabled"
          class="text-red-600 hover:text-red-800 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Remove"
          @click="removeRecipient(index)"
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
    </div>

    <div v-else class="text-sm text-gray-500 mb-3">No additional recipients</div>

    <!-- Add recipient input -->
    <div class="flex gap-2">
      <input
        v-model="newRecipient"
        type="email"
        placeholder="email@example.com"
        :disabled="disabled"
        class="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
        @keyup.enter="addRecipient"
      />
      <button
        type="button"
        :disabled="disabled || !newRecipient.trim()"
        class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
        @click="addRecipient"
      >
        Add
      </button>
    </div>

    <p v-if="error" class="mt-2 text-sm text-red-600">
      {{ error }}
    </p>
    <p v-if="hint" class="mt-2 text-sm text-gray-500">
      {{ hint }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { isValidEmail } from '@/types/emailPreferences'

interface Props {
  modelValue: string[] | null
  label?: string
  disabled?: boolean
  error?: string
  hint?: string
  maxRecipients?: number
}

const props = withDefaults(defineProps<Props>(), {
  label: '',
  disabled: false,
  error: '',
  hint: '',
  maxRecipients: 10,
})

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

// State
const recipients = ref<string[]>([])
const newRecipient = ref('')
const localError = ref('')

// Initialize from modelValue
watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      recipients.value = [...newValue]
    } else {
      recipients.value = []
    }
  },
  { immediate: true }
)

// Add recipient
function addRecipient() {
  const email = newRecipient.value.trim()
  localError.value = ''

  if (!email) {
    return
  }

  // Validate email
  if (!isValidEmail(email)) {
    localError.value = 'Invalid email format'
    return
  }

  // Check duplicates
  if (recipients.value.includes(email)) {
    localError.value = 'Email already added'
    return
  }

  // Check max recipients
  if (recipients.value.length >= props.maxRecipients) {
    localError.value = `Maximum ${props.maxRecipients} recipients allowed`
    return
  }

  // Add recipient
  recipients.value.push(email)
  newRecipient.value = ''
  emitValue()
}

// Remove recipient
function removeRecipient(index: number) {
  recipients.value.splice(index, 1)
  localError.value = ''
  emitValue()
}

// Emit updated value
function emitValue() {
  emit('update:modelValue', recipients.value)
}
</script>

<style scoped>
/* Component styles are in Tailwind classes */
</style>
