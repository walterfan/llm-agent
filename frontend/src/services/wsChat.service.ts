/**
 * WebSocket Chat Service.
 *
 * Provides a real-time bidirectional connection to the AI chat server.
 * Handles connection lifecycle, reconnection, heartbeat, and message routing.
 *
 * Usage:
 *   const ws = new WsChatService()
 *   ws.on('token', (data) => { ... })
 *   ws.on('done', (data) => { ... })
 *   ws.connect()
 *   ws.sendChat('Hello', sessionId)
 */

export type WsMessageType =
  | 'connected'
  | 'token'
  | 'tool_call'
  | 'tool_result'
  | 'agent_start'
  | 'agent_end'
  | 'done'
  | 'error'
  | 'pong'
  | 'session_created'
  | 'session_deleted'
  | 'sessions'
  | 'session_detail'

export interface WsMessage {
  type: WsMessageType
  [key: string]: any
}

type WsEventHandler = (data: WsMessage) => void

export interface WsChatOptions {
  /** Auto-reconnect on disconnect (default: true) */
  autoReconnect?: boolean
  /** Max reconnect attempts (default: 5) */
  maxReconnectAttempts?: number
  /** Base reconnect delay in ms (default: 1000, exponential backoff) */
  reconnectDelay?: number
  /** Heartbeat interval in ms (default: 30000) */
  heartbeatInterval?: number
}

const DEFAULT_OPTIONS: Required<WsChatOptions> = {
  autoReconnect: true,
  maxReconnectAttempts: 5,
  reconnectDelay: 1000,
  heartbeatInterval: 30000,
}

export class WsChatService {
  private ws: WebSocket | null = null
  private options: Required<WsChatOptions>
  private handlers: Map<string, WsEventHandler[]> = new Map()
  private reconnectAttempts = 0
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private _isConnected = false
  private _isConnecting = false

  constructor(options?: WsChatOptions) {
    this.options = { ...DEFAULT_OPTIONS, ...options }
  }

  // ========== Connection State ==========

  get isConnected(): boolean {
    return this._isConnected
  }

  get isConnecting(): boolean {
    return this._isConnecting
  }

  // ========== Event System ==========

  /**
   * Register an event handler.
   *
   * @param type - Message type to listen for, or '*' for all messages
   * @param handler - Callback function
   */
  on(type: string, handler: WsEventHandler): void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, [])
    }
    this.handlers.get(type)!.push(handler)
  }

  /**
   * Remove an event handler.
   */
  off(type: string, handler: WsEventHandler): void {
    const handlers = this.handlers.get(type)
    if (handlers) {
      const idx = handlers.indexOf(handler)
      if (idx >= 0) handlers.splice(idx, 1)
    }
  }

  /**
   * Remove all handlers for a type, or all handlers if no type given.
   */
  offAll(type?: string): void {
    if (type) {
      this.handlers.delete(type)
    } else {
      this.handlers.clear()
    }
  }

  private emit(data: WsMessage): void {
    // Type-specific handlers
    const typeHandlers = this.handlers.get(data.type)
    if (typeHandlers) {
      for (const h of typeHandlers) {
        try {
          h(data)
        } catch (e) {
          console.error(`WS handler error [${data.type}]:`, e)
        }
      }
    }
    // Wildcard handlers
    const wildcardHandlers = this.handlers.get('*')
    if (wildcardHandlers) {
      for (const h of wildcardHandlers) {
        try {
          h(data)
        } catch (e) {
          console.error('WS wildcard handler error:', e)
        }
      }
    }
  }

  // ========== Connection Lifecycle ==========

  /**
   * Connect to the WebSocket chat server.
   */
  connect(): void {
    if (this._isConnected || this._isConnecting) return

    const token = localStorage.getItem('access_token')
    if (!token) {
      this.emit({ type: 'error', content: 'No access token found' })
      return
    }

    this._isConnecting = true

    // Build WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/api/v1/ws/chat?token=${encodeURIComponent(token)}`

    try {
      this.ws = new WebSocket(url)
    } catch (e) {
      this._isConnecting = false
      this.emit({ type: 'error', content: `Failed to create WebSocket: ${e}` })
      return
    }

    this.ws.onopen = () => {
      this._isConnected = true
      this._isConnecting = false
      this.reconnectAttempts = 0
      this.startHeartbeat()
      console.log('[WS] Connected')
    }

    this.ws.onmessage = (event) => {
      try {
        const data: WsMessage = JSON.parse(event.data)
        this.emit(data)
      } catch (e) {
        console.error('[WS] Failed to parse message:', event.data)
      }
    }

    this.ws.onclose = (event) => {
      this._isConnected = false
      this._isConnecting = false
      this.stopHeartbeat()
      console.log(`[WS] Disconnected: code=${event.code} reason=${event.reason}`)

      // Emit disconnect event
      this.emit({ type: 'error', content: `Disconnected (code: ${event.code})` })

      // Auto-reconnect (unless auth failure or intentional close)
      if (
        this.options.autoReconnect &&
        event.code !== 4001 && // Auth failure
        event.code !== 1000 // Normal close
      ) {
        this.scheduleReconnect()
      }
    }

    this.ws.onerror = (event) => {
      console.error('[WS] Error:', event)
      // onclose will fire after onerror
    }
  }

  /**
   * Disconnect from the server.
   */
  disconnect(): void {
    this.stopHeartbeat()
    this.cancelReconnect()
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
    this._isConnected = false
    this._isConnecting = false
  }

  // ========== Send Messages ==========

  private send(data: Record<string, any>): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[WS] Cannot send — not connected')
      return false
    }
    this.ws.send(JSON.stringify(data))
    return true
  }

  /**
   * Send a chat message.
   */
  sendChat(message: string, sessionId?: string): boolean {
    return this.send({
      type: 'chat',
      message,
      session_id: sessionId || null,
    })
  }

  /**
   * Request a new session.
   */
  sendNewSession(): boolean {
    return this.send({ type: 'new_session' })
  }

  /**
   * Request session list.
   */
  sendListSessions(page = 1, pageSize = 20): boolean {
    return this.send({ type: 'list_sessions', page, page_size: pageSize })
  }

  /**
   * Request session detail with messages.
   */
  sendGetSession(sessionId: string): boolean {
    return this.send({ type: 'get_session', session_id: sessionId })
  }

  /**
   * Delete a session.
   */
  sendDeleteSession(sessionId: string): boolean {
    return this.send({ type: 'delete_session', session_id: sessionId })
  }

  /**
   * Send a ping (heartbeat).
   */
  sendPing(): boolean {
    return this.send({ type: 'ping' })
  }

  // ========== Heartbeat ==========

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      this.sendPing()
    }, this.options.heartbeatInterval)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  // ========== Reconnection ==========

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
      console.warn('[WS] Max reconnect attempts reached')
      this.emit({
        type: 'error',
        content: 'Connection lost. Please refresh the page.',
      })
      return
    }

    const delay = this.options.reconnectDelay * Math.pow(2, this.reconnectAttempts)
    this.reconnectAttempts++

    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)

    this.reconnectTimer = setTimeout(() => {
      this.connect()
    }, delay)
  }

  private cancelReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.reconnectAttempts = 0
  }
}

/**
 * Singleton instance for the app.
 */
let _instance: WsChatService | null = null

export function getWsChatService(options?: WsChatOptions): WsChatService {
  if (!_instance) {
    _instance = new WsChatService(options)
  }
  return _instance
}
