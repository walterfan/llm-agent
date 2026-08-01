import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { LLMSettingsResponse, LLMSettingsUpdate, MaskedKeys } from '@/types/llmSettings'
import llmSettingsService from '@/services/llmSettings.service'

export const useLLMSettingsStore = defineStore('llmSettings', () => {
  const settings = ref<LLMSettingsResponse | null>(null)
  const maskedKeys = ref<MaskedKeys | null>(null)
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const successMessage = ref<string | null>(null)

  const hasSettings = computed(() => settings.value !== null)
  const defaults = computed(() => settings.value?.defaults ?? null)

  async function loadSettings() {
    loading.value = true
    error.value = null
    try {
      settings.value = await llmSettingsService.getSettings()
      maskedKeys.value = await llmSettingsService.getMaskedKeys()
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to load LLM settings'
    } finally {
      loading.value = false
    }
  }

  async function saveSettings(data: LLMSettingsUpdate) {
    saving.value = true
    error.value = null
    successMessage.value = null
    try {
      settings.value = await llmSettingsService.updateSettings(data)
      maskedKeys.value = await llmSettingsService.getMaskedKeys()
      successMessage.value = 'Settings saved successfully'
      setTimeout(() => {
        successMessage.value = null
      }, 3000)
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to save LLM settings'
      throw err
    } finally {
      saving.value = false
    }
  }

  function clearMessages() {
    error.value = null
    successMessage.value = null
  }

  return {
    settings,
    maskedKeys,
    loading,
    saving,
    error,
    successMessage,
    hasSettings,
    defaults,
    loadSettings,
    saveSettings,
    clearMessages,
  }
})
