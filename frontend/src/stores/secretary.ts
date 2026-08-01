/**
 * Secretary chat Pinia store
 *
 * Supports two transport modes:
 *   1. SSE (Server-Sent Events) — default, via HTTP POST /chat/stream
 *   2. WebSocket — real-time bidirectional, via ws:///api/v1/ws/chat
 *
 * Toggle with `setTransport('ws' | 'sse')`.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import secretaryService from '@/services/secretary.service'
import { WsChatService, type WsMessage } from '@/services/wsChat.service'
import type {
  ChatSession,
  ChatSessionDetail,
  ChatRequest,
  ToolInfo,
  StreamEvent,
} from '@/types/secretary'

export type TransportMode = 'sse' | 'ws'

export const useSecretaryStore = defineStore('secretary', () => {
  // ============================================================================
  // State
  // ============================================================================

  const sessions = ref<ChatSession[]>([])
  const currentSession = ref<ChatSessionDetail | null>(null)
  const tools = ref<ToolInfo[]>([])

  const loading = ref(false)
  const error = ref<string | null>(null)

  // Transport mode
  const transport = ref<TransportMode>('sse')
  const wsConnected = ref(false)
  const wsOnlineCount = ref(0)

  // WebSocket service instance
  let wsService: WsChatService | null = null

  // Streaming state
  const isStreaming = ref(false)
  const streamingText = ref('')
  const streamingToolCalls = ref<
    Array<{
      tool: string
      args: Record<string, any>
      result?: string
    }>
  >([])

  // ============================================================================
  // Computed
  // ============================================================================

  const hasSessions = computed(() => sessions.value.length > 0)

  const currentMessages = computed(() => currentSession.value?.messages || [])

  const learningTools = computed(() => tools.value.filter((t) => t.category === 'learning'))

  const utilityTools = computed(() => tools.value.filter((t) => t.category === 'utility'))

  // ============================================================================
  // Actions
  // ============================================================================

  /**
   * Send a chat message (non-streaming)
   */
  async function sendMessage(message: string, sessionId?: string | null) {
    loading.value = true
    error.value = null

    try {
      const request: ChatRequest = {
        message,
        session_id: sessionId,
      }

      const response = await secretaryService.chat(request)

      // If we have a current session, add the messages to it
      if (currentSession.value && currentSession.value.id === response.session_id) {
        // Add user message
        currentSession.value.messages.push({
          id: `user-${Date.now()}`,
          role: 'user',
          content: message,
          created_at: new Date().toISOString(),
        })

        // Add assistant message
        currentSession.value.messages.push({
          id: response.message_id,
          role: 'assistant',
          content: response.content,
          tool_calls: response.tool_calls,
          created_at: response.created_at,
        })
      } else {
        // Fetch the session to get full details
        await getSession(response.session_id)
      }

      return response
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to send message'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Send a chat message with streaming
   */
  async function sendMessageStream(
    message: string,
    sessionId?: string | null,
    onToken?: (token: string) => void,
    onToolCall?: (tool: string, args: Record<string, any>) => void,
    onToolResult?: (tool: string, result: string) => void,
    onComplete?: (sessionId: string, messageId: string) => void
  ): Promise<void> {
    isStreaming.value = true
    streamingText.value = ''
    streamingToolCalls.value = []
    error.value = null

    // Add user message to current session immediately
    if (currentSession.value) {
      currentSession.value.messages.push({
        id: `user-${Date.now()}`,
        role: 'user',
        content: message,
        created_at: new Date().toISOString(),
      })
    }

    const token = localStorage.getItem('access_token') || ''
    const request: ChatRequest = {
      message,
      session_id: sessionId,
    }

    try {
      for await (const event of secretaryService.chatStream(request, token)) {
        const data = event as StreamEvent

        switch (data.type) {
          case 'token':
            streamingText.value += data.content
            onToken?.(data.content)
            break

          case 'tool_call':
            streamingToolCalls.value.push({
              tool: data.tool,
              args: data.args,
            })
            onToolCall?.(data.tool, data.args)
            break

          case 'tool_result': {
            // Update the tool call with result
            const toolCall = streamingToolCalls.value.find((tc) => tc.tool === data.tool)
            if (toolCall) {
              toolCall.result = data.result
            }
            onToolResult?.(data.tool, data.result)
            break
          }

          case 'done':
            // Add assistant message to current session
            if (currentSession.value) {
              currentSession.value.messages.push({
                id: data.message_id,
                role: 'assistant',
                content: streamingText.value,
                tool_calls:
                  streamingToolCalls.value.length > 0 ? streamingToolCalls.value : undefined,
                created_at: new Date().toISOString(),
              })

              // Update session ID if new
              if (!sessionId && data.session_id) {
                currentSession.value.id = data.session_id
              }
            }

            onComplete?.(data.session_id, data.message_id)
            break

          case 'error':
            error.value = data.content
            break
        }
      }
    } catch (err: any) {
      error.value = err.message || 'Streaming failed'
      throw err
    } finally {
      isStreaming.value = false
    }
  }

  /**
   * List chat sessions
   */
  async function listSessions(page: number = 1, pageSize: number = 20) {
    loading.value = true
    error.value = null

    try {
      const response = await secretaryService.listSessions(page, pageSize)
      sessions.value = response.sessions
      return response
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to list sessions'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Get a session with messages
   */
  async function getSession(sessionId: string) {
    loading.value = true
    error.value = null

    try {
      currentSession.value = await secretaryService.getSession(sessionId)
      return currentSession.value
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to get session'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Delete a session
   */
  async function deleteSession(sessionId: string) {
    loading.value = true
    error.value = null

    try {
      await secretaryService.deleteSession(sessionId)

      // Remove from list
      sessions.value = sessions.value.filter((s) => s.id !== sessionId)

      // Clear current if it was the deleted one
      if (currentSession.value?.id === sessionId) {
        currentSession.value = null
      }
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to delete session'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Start a new session
   */
  function startNewSession() {
    currentSession.value = {
      id: '',
      title: null,
      messages: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    streamingText.value = ''
    streamingToolCalls.value = []
  }

  /**
   * Load available tools
   */
  async function loadTools() {
    try {
      const response = await secretaryService.listTools()
      tools.value = response.tools
    } catch (err: any) {
      console.error('Failed to load tools:', err)
    }
  }

  /**
   * Clear error
   */
  function clearError() {
    error.value = null
  }

  /**
   * Stop streaming
   */
  function stopStreaming() {
    isStreaming.value = false
  }

  // ============================================================================
  // WebSocket Transport
  // ============================================================================

  /**
   * Switch transport mode between SSE and WebSocket.
   */
  function setTransport(mode: TransportMode) {
    if (transport.value === mode) return

    // Disconnect old WS if switching away
    if (transport.value === 'ws' && wsService) {
      wsService.disconnect()
      wsService.offAll()
      wsService = null
      wsConnected.value = false
    }

    transport.value = mode

    // Connect WS if switching to it
    if (mode === 'ws') {
      connectWebSocket()
    }
  }

  /**
   * Connect to WebSocket chat server.
   */
  function connectWebSocket() {
    if (wsService?.isConnected) return

    wsService = new WsChatService({
      autoReconnect: true,
      maxReconnectAttempts: 10,
      heartbeatInterval: 30000,
    })

    // --- Wire up event handlers ---

    wsService.on('connected', (data: WsMessage) => {
      wsConnected.value = true
      wsOnlineCount.value = data.online_count || 0
      console.log('[WS Store] Connected, online:', data.online_count)
    })

    wsService.on('session_created', (data: WsMessage) => {
      if (currentSession.value) {
        currentSession.value.id = data.session_id
        currentSession.value.title = data.title
      }
    })

    wsService.on('token', (data: WsMessage) => {
      isStreaming.value = true
      streamingText.value += data.content || ''
    })

    wsService.on('tool_call', (data: WsMessage) => {
      streamingToolCalls.value.push({
        tool: data.tool,
        args: data.args || {},
      })
    })

    wsService.on('tool_result', (data: WsMessage) => {
      const tc = streamingToolCalls.value.find((t) => t.tool === data.tool)
      if (tc) tc.result = data.result
    })

    wsService.on('done', (data: WsMessage) => {
      // Finalize: add assistant message to current session
      if (currentSession.value) {
        currentSession.value.messages.push({
          id: data.message_id || `ws-${Date.now()}`,
          role: 'assistant',
          content: streamingText.value,
          tool_calls: streamingToolCalls.value.length > 0 ? streamingToolCalls.value : undefined,
          created_at: new Date().toISOString(),
        })

        if (data.session_id) {
          currentSession.value.id = data.session_id
        }
      }

      isStreaming.value = false
      // Refresh session list
      if (wsService) wsService.sendListSessions()
    })

    wsService.on('sessions', (data: WsMessage) => {
      sessions.value = (data.sessions || []).map((s: any) => ({
        id: s.id,
        title: s.title,
        message_count: s.message_count,
        created_at: s.created_at,
        updated_at: s.updated_at,
      }))
    })

    wsService.on('session_detail', (data: WsMessage) => {
      const s = data.session
      if (s) {
        currentSession.value = {
          id: s.id,
          title: s.title,
          messages: s.messages || [],
          created_at: s.created_at,
          updated_at: s.updated_at,
        }
      }
      loading.value = false
    })

    wsService.on('session_deleted', (data: WsMessage) => {
      sessions.value = sessions.value.filter((s) => s.id !== data.session_id)
      if (currentSession.value?.id === data.session_id) {
        currentSession.value = null
      }
    })

    wsService.on('error', (data: WsMessage) => {
      if (data.content?.includes('Disconnected')) {
        wsConnected.value = false
      } else {
        error.value = data.content || 'WebSocket error'
        isStreaming.value = false
      }
    })

    wsService.connect()
  }

  /**
   * Disconnect WebSocket.
   */
  function disconnectWebSocket() {
    if (wsService) {
      wsService.disconnect()
      wsService.offAll()
      wsService = null
    }
    wsConnected.value = false
  }

  /**
   * Send a chat message via WebSocket.
   */
  function sendMessageWs(message: string, sessionId?: string | null) {
    if (!wsService?.isConnected) {
      error.value = 'WebSocket not connected'
      return
    }

    // Reset streaming state
    streamingText.value = ''
    streamingToolCalls.value = []
    isStreaming.value = true
    error.value = null

    // Add user message to current session immediately
    if (currentSession.value) {
      currentSession.value.messages.push({
        id: `user-${Date.now()}`,
        role: 'user',
        content: message,
        created_at: new Date().toISOString(),
      })
    }

    wsService.sendChat(message, sessionId || undefined)
  }

  /**
   * Unified send — dispatches to SSE or WS based on current transport.
   */
  async function sendMessageAuto(
    message: string,
    sessionId?: string | null,
    onToken?: (token: string) => void,
    onToolCall?: (tool: string, args: Record<string, any>) => void,
    onToolResult?: (tool: string, result: string) => void,
    onComplete?: (sessionId: string, messageId: string) => void
  ) {
    if (transport.value === 'ws') {
      sendMessageWs(message, sessionId)
    } else {
      await sendMessageStream(message, sessionId, onToken, onToolCall, onToolResult, onComplete)
    }
  }

  /**
   * Unified list sessions.
   */
  async function listSessionsAuto(page = 1, pageSize = 20): Promise<void> {
    if (transport.value === 'ws' && wsService?.isConnected) {
      wsService.sendListSessions(page, pageSize)
    } else {
      await listSessions(page, pageSize)
    }
  }

  /**
   * Unified get session.
   */
  async function getSessionAuto(sessionId: string): Promise<void> {
    if (transport.value === 'ws' && wsService?.isConnected) {
      loading.value = true
      wsService.sendGetSession(sessionId)
    } else {
      await getSession(sessionId)
    }
  }

  /**
   * Unified delete session.
   */
  async function deleteSessionAuto(sessionId: string): Promise<void> {
    if (transport.value === 'ws' && wsService?.isConnected) {
      wsService.sendDeleteSession(sessionId)
    } else {
      await deleteSession(sessionId)
    }
  }

  // ============================================================================
  // Tool Helper Methods (for views to avoid direct API calls)
  // ============================================================================

  /**
   * Calculate an expression using the calculator tool
   */
  async function calculate(expression: string): Promise<string> {
    loading.value = true
    error.value = null

    try {
      const request: ChatRequest = {
        message: `计算 ${expression}`,
      }
      const response = await secretaryService.chat(request)
      return response.content
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Calculation failed'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  /**
   * Create or manage a task
   */
  async function manageTask(instruction: string): Promise<string> {
    loading.value = true
    error.value = null

    try {
      const request: ChatRequest = {
        message: instruction,
      }
      const response = await secretaryService.chat(request)
      return response.content
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Task operation failed'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  /**
   * Create or manage a reminder
   */
  async function manageReminder(instruction: string): Promise<string> {
    loading.value = true
    error.value = null

    try {
      const request: ChatRequest = {
        message: instruction,
      }
      const response = await secretaryService.chat(request)
      return response.content
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Reminder operation failed'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  /**
   * Create or manage a note
   */
  async function manageNote(instruction: string): Promise<string> {
    loading.value = true
    error.value = null

    try {
      const request: ChatRequest = {
        message: instruction,
      }
      const response = await secretaryService.chat(request)
      return response.content
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Note operation failed'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  /**
   * Get date/time information
   */
  async function getDateTime(query: string): Promise<string> {
    loading.value = true
    error.value = null

    try {
      const request: ChatRequest = {
        message: query,
      }
      const response = await secretaryService.chat(request)
      return response.content
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'DateTime query failed'
      error.value = message
      throw new Error(message)
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    sessions,
    currentSession,
    tools,
    loading,
    error,
    isStreaming,
    streamingText,
    streamingToolCalls,
    transport,
    wsConnected,
    wsOnlineCount,

    // Computed
    hasSessions,
    currentMessages,
    learningTools,
    utilityTools,

    // Actions — SSE (original)
    sendMessage,
    sendMessageStream,
    listSessions,
    getSession,
    deleteSession,
    startNewSession,
    loadTools,
    clearError,
    stopStreaming,

    // Actions — WebSocket
    setTransport,
    connectWebSocket,
    disconnectWebSocket,
    sendMessageWs,

    // Actions — Unified (auto-dispatch based on transport)
    sendMessageAuto,
    listSessionsAuto,
    getSessionAuto,
    deleteSessionAuto,

    // Actions — Tool Helpers (avoid direct API calls from views)
    calculate,
    manageTask,
    manageReminder,
    manageNote,
    getDateTime,
  }
})
