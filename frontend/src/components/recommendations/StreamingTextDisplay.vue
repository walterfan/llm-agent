<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'

const props = defineProps<{
  text: string
  isStreaming: boolean
}>()

const showCursor = ref(true)

// Blinking cursor effect
let cursorInterval: number | undefined
if (props.isStreaming) {
  cursorInterval = setInterval(() => {
    showCursor.value = !showCursor.value
  }, 500)
}

onUnmounted(() => {
  if (cursorInterval) {
    clearInterval(cursorInterval)
  }
})

const displayText = computed(() => props.text || '')
</script>

<template>
  <div class="streaming-text-display">
    <div class="text-content whitespace-pre-wrap">
      {{ displayText }}
      <span v-if="isStreaming && showCursor" class="cursor">▋</span>
    </div>
  </div>
</template>

<style scoped>
.streaming-text-display {
  min-height: 100px;
  padding: 1rem;
  background-color: #f9fafb;
  border-radius: 0.5rem;
  font-size: 1rem;
  line-height: 1.6;
  color: #1f2937;
}

.text-content {
  position: relative;
}

.cursor {
  display: inline-block;
  color: #3b82f6;
  font-weight: bold;
  margin-left: 2px;
}
</style>
