/**
 * Secretary chat TypeScript interfaces
 */

// ============================================================================
// Chat Types
// ============================================================================

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'tool' | 'system'
  content: string | null
  tool_calls?: ToolCallInfo[] | null
  tool_name?: string | null
  created_at: string
}

export interface ToolCallInfo {
  tool: string
  args: Record<string, any>
  result?: string | null
}

export interface ChatSession {
  id: string
  title: string | null
  message_count: number
  created_at: string
  updated_at: string
}

export interface ChatSessionDetail extends Omit<ChatSession, 'message_count'> {
  messages: ChatMessage[]
}

export interface ChatRequest {
  message: string
  session_id?: string | null
}

export interface ChatResponse {
  session_id: string
  message_id: string
  content: string
  tool_calls: ToolCallInfo[]
  created_at: string
}

export interface SessionListResponse {
  sessions: ChatSession[]
  total: number
  page: number
  page_size: number
}

// ============================================================================
// Tool Types
// ============================================================================

export interface ToolInfo {
  name: string
  description: string
  category: 'learning' | 'utility'
}

export interface ToolListResponse {
  tools: ToolInfo[]
}

// ============================================================================
// Streaming Types
// ============================================================================

export interface StreamTokenEvent {
  type: 'token'
  content: string
}

export interface StreamToolCallEvent {
  type: 'tool_call'
  tool: string
  args: Record<string, any>
}

export interface StreamToolResultEvent {
  type: 'tool_result'
  tool: string
  result: string
}

export interface StreamDoneEvent {
  type: 'done'
  session_id: string
  message_id: string
}

export interface StreamErrorEvent {
  type: 'error'
  content: string
  trace_id?: string
}

export type StreamEvent =
  | StreamTokenEvent
  | StreamToolCallEvent
  | StreamToolResultEvent
  | StreamDoneEvent
  | StreamErrorEvent

// ============================================================================
// Learning Record Types
// ============================================================================

export type LearningRecordType = 'word' | 'sentence' | 'topic' | 'article' | 'question' | 'idea'

export interface LearningRecord {
  id: string
  input_type: LearningRecordType
  user_input: string
  response_payload: Record<string, any>
  session_id?: string | null
  tags: string[]
  is_favorite: boolean
  review_count: number
  last_reviewed_at?: string | null
  created_at: string
  updated_at: string
}

export interface LearningRecordCreate {
  input_type: LearningRecordType
  user_input: string
  response_payload: Record<string, any>
  session_id?: string | null
  tags?: string[] | null
}

export interface LearningRecordUpdate {
  tags?: string[] | null
  is_favorite?: boolean | null
}

export interface LearningRecordListResponse {
  records: LearningRecord[]
  total: number
  page: number
  page_size: number
}

export interface LearningStatistics {
  total: number
  by_type: Record<string, number>
  favorites: number
  total_reviews: number
}
