<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  variant?: 'primary' | 'secondary' | 'danger'
  type?: 'button' | 'submit' | 'reset'
  disabled?: boolean
  loading?: boolean
  fullWidth?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  type: 'button',
  disabled: false,
  loading: false,
  fullWidth: false,
})

const buttonClass = computed(() => {
  const baseClass =
    'rounded-md px-4 py-2 text-sm font-semibold shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed'
  const widthClass = props.fullWidth ? 'w-full' : ''

  const variantClasses = {
    primary: 'bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-600',
    secondary: 'bg-gray-600 text-white hover:bg-gray-700 focus:ring-gray-600',
    danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-600',
  }

  return `${baseClass} ${variantClasses[props.variant]} ${widthClass}`
})
</script>

<template>
  <button :type="type" :disabled="disabled || loading" :class="buttonClass">
    <span v-if="loading" class="inline-block animate-spin mr-2">⏳</span>
    <slot />
  </button>
</template>
