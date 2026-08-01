/**
 * Pinia store for the Medical Paper Writing Assistant.
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import medicalPaperService from '@/services/medicalPaper.service'
import type {
  CreateTaskRequest,
  PaperTask,
  RevisionRequest,
  StreamEvent,
  TemplateInfo,
} from '@/types/medicalPaper'

export const useMedicalPaperStore = defineStore('medicalPaper', () => {
  // ========================================================================
  // State
  // ========================================================================

  const tasks = ref<PaperTask[]>([])
  const currentTask = ref<PaperTask | null>(null)
  const templates = ref<TemplateInfo[]>([])
  const total = ref(0)

  const loading = ref(false)
  const error = ref<string | null>(null)

  // Streaming state
  const isStreaming = ref(false)
  const streamingText = ref('')
  const streamEvents = ref<StreamEvent[]>([])
  const currentAgent = ref<string | null>(null)

  // ========================================================================
  // Computed
  // ========================================================================

  const hasTasks = computed(() => tasks.value.length > 0)
  const activeTasks = computed(() =>
    tasks.value.filter((t) => t.status === 'running' || t.status === 'pending')
  )
  const completedTasks = computed(() => tasks.value.filter((t) => t.status === 'completed'))

  // ========================================================================
  // Actions
  // ========================================================================

  async function createTask(request: CreateTaskRequest) {
    loading.value = true
    error.value = null

    try {
      const task = await medicalPaperService.createTask(request)
      tasks.value.unshift(task)
      currentTask.value = task
      return task
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to create task'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function getTask(taskId: string) {
    loading.value = true
    error.value = null

    try {
      currentTask.value = await medicalPaperService.getTask(taskId)
      return currentTask.value
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to get task'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function listTasks(page = 1, pageSize = 20) {
    loading.value = true
    error.value = null

    try {
      const response = await medicalPaperService.listTasks(page, pageSize)
      tasks.value = response.tasks
      total.value = response.total
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to list tasks'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function reviseTask(taskId: string, request: RevisionRequest) {
    loading.value = true
    error.value = null

    try {
      const task = await medicalPaperService.reviseTask(taskId, request)
      currentTask.value = task
      // Update in list
      const idx = tasks.value.findIndex((t) => t.id === taskId)
      if (idx >= 0) tasks.value[idx] = task
      return task
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to revise task'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function loadTemplates() {
    try {
      const response = await medicalPaperService.listTemplates()
      templates.value = response.templates
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to load templates'
    }
  }

  async function streamTaskProgress(taskId: string, token: string) {
    isStreaming.value = true
    streamingText.value = ''
    streamEvents.value = []
    currentAgent.value = null
    error.value = null

    try {
      for await (const event of medicalPaperService.streamTask(taskId, token)) {
        streamEvents.value.push(event as StreamEvent)

        switch (event.type) {
          case 'token':
            streamingText.value += event.content || ''
            break
          case 'agent_start':
            currentAgent.value = event.agent || null
            break
          case 'agent_end':
            currentAgent.value = null
            break
          case 'done':
            // Refresh task to get final results
            await getTask(taskId)
            break
          case 'error':
            error.value = event.content || 'Streaming error'
            break
        }
      }
    } catch (err: any) {
      error.value = err.message || 'Streaming failed'
    } finally {
      isStreaming.value = false
      currentAgent.value = null
    }
  }

  function clearError() {
    error.value = null
  }

  // ========================================================================
  // Return
  // ========================================================================

  return {
    // State
    tasks,
    currentTask,
    templates,
    total,
    loading,
    error,
    isStreaming,
    streamingText,
    streamEvents,
    currentAgent,

    // Computed
    hasTasks,
    activeTasks,
    completedTasks,

    // Actions
    createTask,
    getTask,
    listTasks,
    reviseTask,
    loadTemplates,
    streamTaskProgress,
    clearError,
  }
})
