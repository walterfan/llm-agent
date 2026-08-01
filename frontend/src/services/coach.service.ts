/**
 * AI Coach API service
 */

import api from './api'
import type {
  CoachChatRequest,
  CoachChatResponse,
  CoachMode,
  CoachStreamEvent,
  LearningGoal,
  GoalCreate,
  GoalUpdate,
  StudySession,
  SessionCreate,
  ProgressReport,
} from '@/types/coach'

const BASE_PATH = '/coach'

// ============================================================================
// Learning Goals
// ============================================================================

/**
 * Create a new learning goal
 */
async function createGoal(data: GoalCreate): Promise<LearningGoal> {
  const response = await api.post<LearningGoal>(`${BASE_PATH}/goals`, data)
  return response.data
}

/**
 * List learning goals (optionally filter by status)
 */
async function listGoals(status?: string): Promise<LearningGoal[]> {
  const params: Record<string, string> = {}
  if (status) {
    params.status = status
  }
  const response = await api.get<LearningGoal[]>(`${BASE_PATH}/goals`, { params })
  return response.data
}

/**
 * Update a learning goal
 */
async function updateGoal(goalId: string, data: GoalUpdate): Promise<LearningGoal> {
  const response = await api.patch<LearningGoal>(`${BASE_PATH}/goals/${goalId}`, data)
  return response.data
}

// ============================================================================
// Study Sessions
// ============================================================================

/**
 * Log a study session
 */
async function logSession(data: SessionCreate): Promise<StudySession> {
  const response = await api.post<StudySession>(`${BASE_PATH}/sessions`, data)
  return response.data
}

/**
 * List study sessions (optionally filter by goal)
 */
async function listSessions(goalId?: string): Promise<StudySession[]> {
  const params: Record<string, string> = {}
  if (goalId) {
    params.goal_id = goalId
  }
  const response = await api.get<StudySession[]>(`${BASE_PATH}/sessions`, { params })
  return response.data
}

// ============================================================================
// Progress
// ============================================================================

/**
 * Get progress report for a learning goal
 */
async function getProgress(goalId: string): Promise<ProgressReport> {
  const response = await api.get<ProgressReport>(`${BASE_PATH}/progress/${goalId}`)
  return response.data
}

// ============================================================================
// Coach Chat
// ============================================================================

/**
 * Send a coach chat message (non-streaming)
 */
async function chat(request: CoachChatRequest): Promise<CoachChatResponse> {
  const response = await api.post<CoachChatResponse>(`${BASE_PATH}/chat`, request)
  return response.data
}

/**
 * Stream coach chat using fetch API with ReadableStream (SSE)
 *
 * Uses GET /coach/chat/stream with query parameters.
 */
async function* chatStream(
  message: string,
  mode: CoachMode,
  token: string,
  sessionId?: string | null,
  goalId?: string | null
): AsyncGenerator<CoachStreamEvent, void, unknown> {
  const params = new URLSearchParams()
  params.append('message', message)
  params.append('mode', mode)
  if (sessionId) {
    params.append('session_id', sessionId)
  }
  if (goalId) {
    params.append('goal_id', goalId)
  }

  const url = `/api/v1${BASE_PATH}/chat/stream?${params.toString()}`

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('No response body')
  }

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // Process SSE events
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data.trim()) {
            try {
              yield JSON.parse(data) as CoachStreamEvent
            } catch (e) {
              console.error('Failed to parse SSE data:', data)
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export default {
  // Goals
  createGoal,
  listGoals,
  updateGoal,
  // Sessions
  logSession,
  listSessions,
  // Progress
  getProgress,
  // Chat
  chat,
  chatStream,
}
