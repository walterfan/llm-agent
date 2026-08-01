/**
 * Secretary API service
 */

import api from './api'
import type {
  ChatRequest,
  ChatResponse,
  ChatSessionDetail,
  SessionListResponse,
  ToolListResponse,
} from '@/types/secretary'

const BASE_PATH = '/secretary'

/**
 * Send a chat message (non-streaming)
 */
async function chat(request: ChatRequest): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>(`${BASE_PATH}/chat`, request)
  return response.data
}

/**
 * Create a streaming event source for chat
 * Returns an EventSource that streams tokens
 */
function createStreamingEventSource(
  message: string,
  _token: string,
  sessionId?: string | null
): EventSource {
  const params = new URLSearchParams()
  params.append('message', message)
  if (sessionId) {
    params.append('session_id', sessionId)
  }

  // Use fetch with ReadableStream for better control
  const url = `/api/v1${BASE_PATH}/chat/stream`

  // EventSource doesn't support POST, so we need a workaround
  // We'll use a custom approach with fetch
  const eventSource = new EventSource(`${url}?${params.toString()}`, { withCredentials: false })

  // Note: The actual implementation uses POST with SSE response
  // EventSource only supports GET, so we need to handle this differently
  return eventSource
}

/**
 * Stream chat using fetch API with ReadableStream
 */
async function* chatStream(
  request: ChatRequest,
  token: string
): AsyncGenerator<any, void, unknown> {
  const response = await fetch(`/api/v1${BASE_PATH}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(request),
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
              yield JSON.parse(data)
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

/**
 * List chat sessions
 */
async function listSessions(page: number = 1, pageSize: number = 20): Promise<SessionListResponse> {
  const response = await api.get<SessionListResponse>(`${BASE_PATH}/sessions`, {
    params: { page, page_size: pageSize },
  })
  return response.data
}

/**
 * Get a session with messages
 */
async function getSession(sessionId: string): Promise<ChatSessionDetail> {
  const response = await api.get<ChatSessionDetail>(`${BASE_PATH}/sessions/${sessionId}`)
  return response.data
}

/**
 * Delete a session
 */
async function deleteSession(sessionId: string): Promise<void> {
  await api.delete(`${BASE_PATH}/sessions/${sessionId}`)
}

/**
 * List available tools
 */
async function listTools(): Promise<ToolListResponse> {
  const response = await api.get<ToolListResponse>(`${BASE_PATH}/tools`)
  return response.data
}

export default {
  chat,
  chatStream,
  createStreamingEventSource,
  listSessions,
  getSession,
  deleteSession,
  listTools,
}
