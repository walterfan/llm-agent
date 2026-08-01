/**
 * Philosophy store for state management
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  chat as philosophyServiceChat,
  chatStream as philosophyServiceChatStream,
} from '@/services/philosophy.service'
import type { PhilosophyStreamEvent, PhilosophyPreset } from '@/services/philosophy.service'

export type { PhilosophyStreamEvent, PhilosophyPreset }

export const usePhilosophyStore = defineStore('philosophy', () => {
  // State
  const loading = ref(false)
  const error = ref<string | null>(null)
  const response = ref<string | null>(null)

  // Actions
  async function chat(message: string, preset?: PhilosophyPreset, context?: string): Promise<any> {
    loading.value = true
    error.value = null

    try {
      const result = await philosophyServiceChat({ message, preset, context })
      response.value = result.content
      return result
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Philosophy chat failed'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function chatStream(
    request: { message: string; preset?: PhilosophyPreset; context?: string },
    onEvent: (event: PhilosophyStreamEvent) => void
  ): Promise<void> {
    loading.value = true
    error.value = null

    try {
      await philosophyServiceChatStream(request, onEvent)
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Philosophy chat stream failed'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  function clearError(): void {
    error.value = null
  }

  function clearResponse(): void {
    response.value = null
  }

  return {
    // State
    loading,
    error,
    response,

    // Actions
    chat,
    chatStream,
    clearError,
    clearResponse,
  }
})
