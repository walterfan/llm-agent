<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  modelValue: string
  label: string
  type?: string
  placeholder?: string
  error?: string | null
  required?: boolean
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  type: 'text',
  placeholder: '',
  error: null,
  required: false,
  disabled: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const inputClass = computed(() => {
  const baseClass =
    'block w-full rounded-md border-0 py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset placeholder:text-gray-400 focus:ring-2 focus:ring-inset sm:text-sm sm:leading-6'
  if (props.error) {
    return `${baseClass} ring-red-300 focus:ring-red-500`
  }
  return `${baseClass} ring-gray-300 focus:ring-primary-600`
})
</script>

<template>
  <div class="mb-4">
    <label :for="label" class="block text-sm font-medium leading-6 text-gray-900 mb-1">
      {{ label }}
      <span v-if="required" class="text-red-500">*</span>
    </label>
    <input
      :id="label"
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :required="required"
      :disabled="disabled"
      :class="inputClass"
      @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    />
    <p v-if="error" class="mt-1 text-sm text-red-600">
      {{ error }}
    </p>
  </div>
</template>
