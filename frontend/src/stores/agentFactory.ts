/**
 * AI Agent Factory Store (Pinia)
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { agentFactoryService } from '@/services/agentFactory.service'
import type {
  AgentSpec,
  SpecSummary,
  SpecResponse,
  ToolCapability,
  RunResponse,
  SpecStatus,
} from '@/types/agentFactory'

export const useAgentFactoryStore = defineStore('agentFactory', () => {
  // State
  const specs = ref<SpecSummary[]>([])
  const currentSpec = ref<SpecResponse | null>(null)
  const tools = ref<ToolCapability[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const runResult = ref<RunResponse | null>(null)

  // Actions
  async function compile(oneLiner: string) {
    loading.value = true
    error.value = null
    try {
      const result = await agentFactoryService.compile(oneLiner)
      currentSpec.value = result
      await loadSpecs() // Refresh list
      return result
    } catch (err: any) {
      console.error('Compile error details:', err)
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to compile spec'
      error.value = `Compile failed: ${errorMsg}`
      throw err
    } finally {
      loading.value = false
    }
  }

  async function loadSpecs(status?: SpecStatus) {
    loading.value = true
    error.value = null
    try {
      specs.value = await agentFactoryService.listSpecs(status)
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to load specs'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function loadSpec(id: string) {
    loading.value = true
    error.value = null
    try {
      currentSpec.value = await agentFactoryService.getSpec(id)
      return currentSpec.value
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to load spec'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateSpec(id: string, updates: Partial<AgentSpec>) {
    loading.value = true
    error.value = null
    try {
      const result = await agentFactoryService.updateSpec(id, updates)
      currentSpec.value = result
      await loadSpecs() // Refresh list
      return result
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to update spec'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function approveSpec(id: string) {
    loading.value = true
    error.value = null
    try {
      const result = await agentFactoryService.approveSpec(id)
      currentSpec.value = result
      await loadSpecs() // Refresh list
      return result
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to approve spec'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function publishSpec(id: string) {
    loading.value = true
    error.value = null
    try {
      const result = await agentFactoryService.publishSpec(id)
      currentSpec.value = result
      await loadSpecs() // Refresh list
      return result
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to publish spec'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function runAgent(specId: string, input: string) {
    loading.value = true
    error.value = null
    try {
      runResult.value = await agentFactoryService.runAgent(specId, input)
      return runResult.value
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to run agent'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function loadTools() {
    loading.value = true
    error.value = null
    try {
      tools.value = await agentFactoryService.listTools()
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to load tools'
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  function clearRunResult() {
    runResult.value = null
  }

  async function deleteSpec(id: string) {
    loading.value = true
    error.value = null
    try {
      await agentFactoryService.deleteSpec(id)
      // Clear current spec if it was deleted
      if (currentSpec.value?.id === id) {
        currentSpec.value = null
      }
      // Refresh list
      await loadSpecs()
    } catch (err: any) {
      console.error('Delete error details:', err)
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to delete spec'
      error.value = `Delete failed: ${errorMsg}`
      throw err
    } finally {
      loading.value = false
    }
  }

  // Memory actions
  async function getMemories(agentId: string, limit: number = 10) {
    return await agentFactoryService.getMemories(agentId, limit)
  }

  async function searchMemories(agentId: string, query: string, limit: number = 5) {
    return await agentFactoryService.searchMemories(agentId, query, limit)
  }

  async function countMemories(agentId: string) {
    return await agentFactoryService.countMemories(agentId)
  }

  async function clearMemories(agentId: string) {
    await agentFactoryService.clearMemories(agentId)
  }

  return {
    // State
    specs,
    currentSpec,
    tools,
    loading,
    error,
    runResult,

    // Actions
    compile,
    loadSpecs,
    loadSpec,
    updateSpec,
    approveSpec,
    publishSpec,
    runAgent,
    loadTools,
    deleteSpec,
    clearError,
    clearRunResult,

    // Memory actions
    getMemories,
    searchMemories,
    countMemories,
    clearMemories,
  }
})
