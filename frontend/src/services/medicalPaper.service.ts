/**
 * API service for the Medical Paper Writing Assistant.
 */

import api from './api'
import type {
  CreateTaskRequest,
  PaperTask,
  RevisionRequest,
  TaskListResponse,
  TemplateListResponse,
} from '@/types/medicalPaper'

const BASE_PATH = '/medical-paper'

export default {
  /**
   * Create a new medical paper writing task.
   */
  async createTask(request: CreateTaskRequest): Promise<PaperTask> {
    const response = await api.post<PaperTask>(`${BASE_PATH}/create`, request)
    return response.data
  },

  /**
   * Get task status and results.
   */
  async getTask(taskId: string): Promise<PaperTask> {
    const response = await api.get<PaperTask>(`${BASE_PATH}/${taskId}`)
    return response.data
  },

  /**
   * List the current user's paper tasks.
   */
  async listTasks(page = 1, pageSize = 20): Promise<TaskListResponse> {
    const response = await api.get<TaskListResponse>(BASE_PATH, {
      params: { page, page_size: pageSize },
    })
    return response.data
  },

  /**
   * Submit revision feedback for a task.
   */
  async reviseTask(taskId: string, request: RevisionRequest): Promise<PaperTask> {
    const response = await api.post<PaperTask>(`${BASE_PATH}/${taskId}/revise`, request)
    return response.data
  },

  /**
   * List available paper type templates.
   */
  async listTemplates(): Promise<TemplateListResponse> {
    const response = await api.get<TemplateListResponse>(`${BASE_PATH}/templates`)
    return response.data
  },

  /**
   * Stream task progress via SSE.
   */
  async *streamTask(taskId: string, token: string): AsyncGenerator<any, void, unknown> {
    const response = await fetch(`${api.defaults.baseURL}${BASE_PATH}/${taskId}/stream`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'text/event-stream',
      },
    })

    if (!response.ok) {
      throw new Error(`Stream failed: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) throw new Error('No reader available')

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            yield data
          } catch {
            // Skip malformed events
          }
        }
      }
    }
  },
}
