<template>
  <div class="time-picker">
    <label v-if="label" class="block text-sm font-medium text-gray-700 mb-1">
      {{ label }}
      <span v-if="showTimezone" class="text-xs text-gray-500">(GMT+8)</span>
    </label>
    <div class="flex gap-2 items-center">
      <select
        :value="hour"
        class="block w-20 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
        :disabled="disabled"
        @change="updateHour"
      >
        <option v-for="h in 24" :key="h - 1" :value="h - 1">
          {{ String(h - 1).padStart(2, '0') }}
        </option>
      </select>
      <span class="text-gray-500">:</span>
      <select
        :value="minute"
        class="block w-20 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
        :disabled="disabled"
        @change="updateMinute"
      >
        <option v-for="m in minutes" :key="m" :value="m">
          {{ String(m).padStart(2, '0') }}
        </option>
      </select>
    </div>
    <p v-if="error" class="mt-1 text-sm text-red-600">
      {{ error }}
    </p>
    <p v-if="hint" class="mt-1 text-sm text-gray-500">
      {{ hint }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { parseTime, formatTime } from '@/types/emailPreferences'

interface Props {
  modelValue: string | null
  label?: string
  showTimezone?: boolean
  disabled?: boolean
  error?: string
  hint?: string
  minuteStep?: number // Step for minutes (e.g., 15 for 00, 15, 30, 45)
}

const props = withDefaults(defineProps<Props>(), {
  label: '',
  showTimezone: true,
  disabled: false,
  error: '',
  hint: '',
  minuteStep: 1,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

// State
const hour = ref(8) // Default 08:00
const minute = ref(0)

// Computed
const minutes = computed(() => {
  const result = []
  for (let i = 0; i < 60; i += props.minuteStep) {
    result.push(i)
  }
  return result
})

// Initialize from modelValue
watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      const parsed = parseTime(newValue)
      if (parsed) {
        hour.value = parsed.hour
        minute.value = parsed.minute
      }
    }
  },
  { immediate: true }
)

// Update handlers
function updateHour(event: Event) {
  const target = event.target as HTMLSelectElement
  hour.value = parseInt(target.value, 10)
  emitValue()
}

function updateMinute(event: Event) {
  const target = event.target as HTMLSelectElement
  minute.value = parseInt(target.value, 10)
  emitValue()
}

function emitValue() {
  const timeStr = formatTime(hour.value, minute.value)
  emit('update:modelValue', timeStr)
}
</script>

<style scoped>
.time-picker select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");
  background-position: right 0.5rem center;
  background-repeat: no-repeat;
  background-size: 1.5em 1.5em;
  padding-right: 2.5rem;
}
</style>
