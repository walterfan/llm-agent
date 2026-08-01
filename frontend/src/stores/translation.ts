/**
 * Translation store for state management
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  translateByUrl as serviceTranslateByUrl,
  translateByFile as serviceTranslateByFile,
  translateByText as serviceTranslateByText,
  streamTranslationByUrl as serviceStreamTranslationByUrl,
  streamTranslationByFile as serviceStreamTranslationByFile,
  streamTranslationByText as serviceStreamTranslationByText,
  type TranslationResponse,
  type OutputMode,
  type StreamEvent,
} from '@/services/translation.service'

export type { TranslationResponse, OutputMode, StreamEvent }

export const useTranslationStore = defineStore('translation', () => {
  // State
  const loading = ref(false)
  const error = ref<string | null>(null)
  const translationResult = ref<TranslationResponse | null>(null)

  // Non-streaming translation methods
  async function translateByUrl(
    url: string,
    outputMode: OutputMode = 'chinese_only'
  ): Promise<TranslationResponse> {
    loading.value = true
    error.value = null

    try {
      const result = await serviceTranslateByUrl(url, outputMode)
      translationResult.value = result
      return result
    } catch (err: any) {
      const message = err.message || 'Translation by URL failed'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function translateByFile(
    file: File,
    outputMode: OutputMode = 'chinese_only'
  ): Promise<TranslationResponse> {
    loading.value = true
    error.value = null

    try {
      const result = await serviceTranslateByFile(file, outputMode)
      translationResult.value = result
      return result
    } catch (err: any) {
      const message = err.message || 'Translation by file failed'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function translateByText(
    text: string,
    outputMode: OutputMode = 'chinese_only'
  ): Promise<TranslationResponse> {
    loading.value = true
    error.value = null

    try {
      const result = await serviceTranslateByText(text, outputMode)
      translationResult.value = result
      return result
    } catch (err: any) {
      const message = err.message || 'Translation by text failed'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  // Streaming translation methods
  async function streamTranslationByUrl(
    url: string,
    outputMode: OutputMode,
    onEvent: (ev: StreamEvent) => void
  ): Promise<void> {
    loading.value = true
    error.value = null

    try {
      await serviceStreamTranslationByUrl(url, outputMode, onEvent)
    } catch (err: any) {
      const message = err.message || 'Stream translation by URL failed'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function streamTranslationByFile(
    file: File,
    outputMode: OutputMode,
    onEvent: (ev: StreamEvent) => void
  ): Promise<void> {
    loading.value = true
    error.value = null

    try {
      await serviceStreamTranslationByFile(file, outputMode, onEvent)
    } catch (err: any) {
      const message = err.message || 'Stream translation by file failed'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  async function streamTranslationByText(
    text: string,
    outputMode: OutputMode,
    onEvent: (ev: StreamEvent) => void
  ): Promise<void> {
    loading.value = true
    error.value = null

    try {
      await serviceStreamTranslationByText(text, outputMode, onEvent)
    } catch (err: any) {
      const message = err.message || 'Stream translation by text failed'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  function clearError(): void {
    error.value = null
  }

  function clearResult(): void {
    translationResult.value = null
  }

  return {
    // State
    loading,
    error,
    translationResult,

    // Actions
    translateByUrl,
    translateByFile,
    translateByText,
    streamTranslationByUrl,
    streamTranslationByFile,
    streamTranslationByText,
    clearError,
    clearResult,
  }
})
