<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  disabled?: boolean
  placeholder?: string
}>()

const emit = defineEmits<{
  (e: 'send', message: string): void
}>()

const message = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)

function handleSend() {
  const trimmed = message.value.trim()
  if (trimmed && !props.disabled) {
    emit('send', trimmed)
    message.value = ''
    // Reset textarea height
    if (textareaRef.value) {
      textareaRef.value.style.height = 'auto'
    }
  }
}

function handleKeydown(event: KeyboardEvent) {
  // Send on Enter (without Shift)
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

// Auto-resize textarea
function handleInput() {
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
    textareaRef.value.style.height = `${Math.min(textareaRef.value.scrollHeight, 200)}px`
  }
}

// Focus on mount
watch(
  textareaRef,
  (el) => {
    if (el) {
      el.focus()
    }
  },
  { immediate: true }
)
</script>

<template>
  <div class="border-t border-gray-200 bg-white p-4">
    <div class="flex items-end gap-3">
      <textarea
        ref="textareaRef"
        v-model="message"
        :placeholder="placeholder || '输入消息... (按 Enter 发送，Shift+Enter 换行)'"
        :disabled="disabled"
        class="flex-1 resize-none border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
        rows="1"
        @keydown="handleKeydown"
        @input="handleInput"
      />
      <button
        type="button"
        :disabled="disabled || !message.trim()"
        class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        @click="handleSend"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
          />
        </svg>
      </button>
    </div>

    <!-- Hint -->
    <div class="mt-2 text-xs text-gray-400">
      提示: 可以问我任何问题，学习英语单词/句子，或者了解新技术
    </div>
  </div>
</template>
