/**
 * AI Coach TypeScript interfaces
 */

// ============================================================================
// Coach Chat Types
// ============================================================================

export type CoachMode = 'coach' | 'tutor' | 'quiz'

export interface CoachChatRequest {
  message: string
  mode: CoachMode
  session_id?: string | null
  goal_id?: string | null
}

export interface CoachChatResponse {
  content: string
  sources: CoachSource[]
  session_id: string
  mode: string
}

export interface CoachSource {
  title: string
  score: number
  doc_id: string
}

// ============================================================================
// Streaming Types
// ============================================================================

export interface CoachStreamStartEvent {
  type: 'start'
  session_id: string
}

export interface CoachStreamTokenEvent {
  type: 'token'
  content: string
}

export interface CoachStreamDoneEvent {
  type: 'done'
  session_id: string
}

export interface CoachStreamErrorEvent {
  type: 'error'
  content: string
}

export type CoachStreamEvent =
  | CoachStreamStartEvent
  | CoachStreamTokenEvent
  | CoachStreamDoneEvent
  | CoachStreamErrorEvent

// ============================================================================
// Learning Goal Types
// ============================================================================

export type GoalStatus = 'active' | 'completed' | 'paused' | 'abandoned'

export interface LearningGoal {
  id: string
  user_id: number
  subject: string
  description: string | null
  status: GoalStatus
  daily_target_minutes: number
  deadline: string | null
  created_at: string
  completed_at: string | null
}

export interface GoalCreate {
  subject: string
  description?: string
  daily_target_minutes?: number
  deadline?: string
}

export interface GoalUpdate {
  subject?: string
  description?: string
  status?: GoalStatus
  daily_target_minutes?: number
  deadline?: string
}

// ============================================================================
// Study Session Types
// ============================================================================

export type Difficulty = 'easy' | 'medium' | 'hard'

export interface StudySession {
  id: string
  user_id: number
  goal_id: string | null
  duration_minutes: number
  notes: string | null
  difficulty: Difficulty | null
  created_at: string
}

export interface SessionCreate {
  goal_id?: string
  duration_minutes: number
  notes?: string
  difficulty?: Difficulty
}

// ============================================================================
// Progress Types
// ============================================================================

export interface ProgressReport {
  goal: LearningGoal
  total_sessions: number
  total_minutes: number
  avg_minutes_per_session: number
  current_streak_days: number
  longest_streak_days: number
  completion_percentage: number
  days_remaining: number | null
  ai_feedback: string | null
}
