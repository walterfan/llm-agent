/**
 * Philosophy Master API: POST /philosophy/chat, POST /philosophy/chat/stream (SSE).
 */

const BASE = '/api/v1/philosophy'

function getAuthHeader(): string {
  const token = localStorage.getItem('access_token')
  return token ? `Bearer ${token}` : ''
}

function getBaseUrl(): string {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  return ''
}

export type School =
  | 'eastern'
  | 'western'
  | 'zen'
  | 'confucian'
  | 'stoic'
  | 'existential'
  | 'kant'
  | 'nietzsche'
  | 'schopenhauer'
  | 'idealism'
  | 'materialism'
  | 'mixed'

export type Tone = 'gentle' | 'direct' | 'rigorous' | 'zen'
export type Depth = 'shallow' | 'medium' | 'deep'
export type Mode = 'advice' | 'story' | 'compare' | 'daily_practice'

export interface PhilosophyPreset {
  school?: School
  tone?: Tone
  depth?: Depth
  mode?: Mode
  multi_perspective?: boolean
}

export interface PhilosophyChatRequest {
  message: string
  preset?: PhilosophyPreset
  context?: string
}

export interface PhilosophyChatResponse {
  content: string
  sections?: Record<string, unknown> | null
}

export type PhilosophyStreamEvent =
  | { type: 'meta'; preset?: PhilosophyPreset }
  | { type: 'token'; content: string }
  | { type: 'done' }
  | { type: 'error'; content: string }

export async function chat(req: PhilosophyChatRequest): Promise<PhilosophyChatResponse> {
  const res = await fetch(`${getBaseUrl()}${BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: getAuthHeader(),
    },
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || String(err) || res.statusText)
  }
  return res.json()
}

export async function chatStream(
  req: PhilosophyChatRequest,
  onEvent: (ev: PhilosophyStreamEvent) => void
): Promise<void> {
  const res = await fetch(`${getBaseUrl()}${BASE}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: getAuthHeader(),
    },
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || String(err) || res.statusText)
  }
  await consumeSSE(res, onEvent)
}

async function consumeSSE(
  response: Response,
  onEvent: (ev: PhilosophyStreamEvent) => void
): Promise<void> {
  const reader = response.body?.getReader()
  if (!reader) {
    onEvent({ type: 'error', content: 'No response body' })
    return
  }
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    // eslint-disable-next-line no-constant-condition
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() ?? ''
      for (const part of parts) {
        const line = part.trim()
        if (line.startsWith('data: ')) {
          try {
            const ev = JSON.parse(line.slice(6)) as PhilosophyStreamEvent
            onEvent(ev)
          } catch {
            // ignore
          }
        }
      }
    }
    if (buffer.trim().startsWith('data: ')) {
      try {
        const ev = JSON.parse(buffer.trim().slice(6)) as PhilosophyStreamEvent
        onEvent(ev)
      } catch {
        // ignore
      }
    }
  } finally {
    reader.releaseLock()
  }
}
