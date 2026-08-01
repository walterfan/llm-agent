/**
 * Translation API: POST /translation (JSON or multipart), POST /translation/stream (SSE).
 */

const BASE = '/api/v1/translation'

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

export interface TranslationResponse {
  translated_markdown: string
  explanation: string
  summary: string
  source_truncated: boolean
}

export type OutputMode = 'chinese_only' | 'bilingual'

/**
 * Translate from URL (JSON body).
 */
export async function translateByUrl(
  url: string,
  outputMode: OutputMode = 'chinese_only'
): Promise<TranslationResponse> {
  const res = await fetch(`${getBaseUrl()}${BASE}/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: getAuthHeader(),
    },
    body: JSON.stringify({ url: url.trim(), output_mode: outputMode }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || String(err) || res.statusText)
  }
  return res.json()
}

/**
 * Translate from pasted text (JSON body).
 */
export async function translateByText(
  text: string,
  outputMode: OutputMode = 'chinese_only'
): Promise<TranslationResponse> {
  const res = await fetch(`${getBaseUrl()}${BASE}/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: getAuthHeader(),
    },
    body: JSON.stringify({ text: text.trim(), output_mode: outputMode }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || String(err) || res.statusText)
  }
  return res.json()
}

/**
 * Translate from uploaded file (multipart).
 */
export async function translateByFile(
  file: File,
  outputMode: OutputMode = 'chinese_only'
): Promise<TranslationResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('output_mode', outputMode)
  const res = await fetch(`${getBaseUrl()}${BASE}/`, {
    method: 'POST',
    headers: {
      Authorization: getAuthHeader(),
    },
    body: form,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || String(err) || res.statusText)
  }
  return res.json()
}

export interface StreamEvent {
  event:
    | 'token'
    | 'explanation_token'
    | 'explanation'
    | 'summary_token'
    | 'summary'
    | 'done'
    | 'error'
  data?: string
  source_truncated?: boolean
}

/**
 * Stream translation (SSE) from URL.
 */
export async function streamTranslationByUrl(
  url: string,
  outputMode: OutputMode,
  onEvent: (ev: StreamEvent) => void
): Promise<void> {
  const res = await fetch(`${getBaseUrl()}${BASE}/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: getAuthHeader(),
    },
    body: JSON.stringify({ url: url.trim(), output_mode: outputMode }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || String(err) || res.statusText)
  }
  await consumeSSE(res, onEvent)
}

/**
 * Stream translation (SSE) from pasted text.
 */
export async function streamTranslationByText(
  text: string,
  outputMode: OutputMode,
  onEvent: (ev: StreamEvent) => void
): Promise<void> {
  const res = await fetch(`${getBaseUrl()}${BASE}/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: getAuthHeader(),
    },
    body: JSON.stringify({ text: text.trim(), output_mode: outputMode }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || String(err) || res.statusText)
  }
  await consumeSSE(res, onEvent)
}

/**
 * Stream translation (SSE) from file.
 */
export async function streamTranslationByFile(
  file: File,
  outputMode: OutputMode,
  onEvent: (ev: StreamEvent) => void
): Promise<void> {
  const form = new FormData()
  form.append('file', file)
  form.append('output_mode', outputMode)
  const res = await fetch(`${getBaseUrl()}${BASE}/stream`, {
    method: 'POST',
    headers: {
      Authorization: getAuthHeader(),
    },
    body: form,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || String(err) || res.statusText)
  }
  await consumeSSE(res, onEvent)
}

async function consumeSSE(response: Response, onEvent: (ev: StreamEvent) => void): Promise<void> {
  const reader = response.body?.getReader()
  if (!reader) {
    onEvent({ event: 'error', data: 'No response body' })
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
      // SSE events are separated by double newline; split so payloads with \n in JSON are safe
      const parts = buffer.split('\n\n')
      buffer = parts.pop() ?? ''
      for (const part of parts) {
        const line = part.trim()
        if (line.startsWith('data: ')) {
          try {
            const ev = JSON.parse(line.slice(6)) as StreamEvent
            onEvent(ev)
          } catch {
            // skip malformed
          }
        }
      }
    }
    if (buffer.trim().startsWith('data: ')) {
      try {
        const ev = JSON.parse(buffer.trim().slice(6)) as StreamEvent
        onEvent(ev)
      } catch {
        // skip
      }
    }
  } finally {
    reader.releaseLock()
  }
}
