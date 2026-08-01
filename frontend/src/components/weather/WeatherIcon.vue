<script setup lang="ts">
import { computed } from 'vue'
import type { WeatherCondition } from '@/types/weather'

interface Props {
  condition: WeatherCondition
  size?: 'small' | 'medium' | 'large'
}

const props = withDefaults(defineProps<Props>(), {
  size: 'medium',
})

// Weather icon mapping (emoji-based)
const iconMap: Record<string, string> = {
  晴: '☀️',
  多云: '⛅',
  阴: '☁️',
  雨: '🌧️',
  小雨: '🌦️',
  中雨: '🌧️',
  大雨: '⛈️',
  暴雨: '⛈️',
  雪: '❄️',
  小雪: '🌨️',
  中雪: '❄️',
  大雪: '❄️',
  雾: '🌫️',
  霾: '😶‍🌫️',
  沙尘暴: '🌪️',
  风: '💨',
}

const icon = computed(() => {
  const condition = props.condition.trim()

  // Direct match
  if (iconMap[condition]) {
    return iconMap[condition]
  }

  // Fuzzy match for partial conditions
  for (const [key, value] of Object.entries(iconMap)) {
    if (condition.includes(key)) {
      return value
    }
  }

  // Default icon
  return '🌤️'
})

const sizeClass = computed(() => {
  switch (props.size) {
    case 'small':
      return 'text-2xl'
    case 'medium':
      return 'text-4xl'
    case 'large':
      return 'text-6xl'
    default:
      return 'text-4xl'
  }
})
</script>

<template>
  <div class="weather-icon inline-flex items-center justify-center">
    <span :class="sizeClass" role="img" :aria-label="condition">
      {{ icon }}
    </span>
  </div>
</template>

<style scoped>
.weather-icon {
  user-select: none;
}
</style>
