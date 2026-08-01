/**
 * AI Coach Pinia store
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import coachService from '@/services/coach.service'
import type {
  CoachMode,
  CoachStreamEvent,
  LearningGoal,
  GoalCreate,
  GoalUpdate,
  StudySession,
  SessionCreate,
  ProgressReport,
  CoachSource,
} from '@/types/coach'

export interface CoachMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: CoachSource[]
  mode?: CoachMode
  created_at: string
}

export const useCoachStore = defineStore('coach', () => {
  // ============================================================================
  // State
  // ============================================================================

  // Chat state
  const messages = ref<CoachMessage[]>([])
  const currentMode = ref<CoachMode>('coach')
  const sessionId = ref<string | null>(null)
  const selectedGoalId = ref<string | null>(null)

  // Streaming state
  const isStreaming = ref(false)
  const streamingText = ref('')

  // Goals & sessions
  const goals = ref<LearningGoal[]>([])
  const sessions = ref<StudySession[]>([])
  const currentProgress = ref<ProgressReport | null>(null)

  // UI state
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ============================================================================
  // Computed
  // ============================================================================

  const hasMessages = computed(() => messages.value.length > 0)
  const activeGoals = computed(() => goals.value.filter((g) => g.status === 'active'))
  const completedGoals = computed(() => goals.value.filter((g) => g.status === 'completed'))
  const totalStudyMinutes = computed(() =>
    sessions.value.reduce((sum, s) => sum + s.duration_minutes, 0)
  )
  const modeLabel = computed(() => {
    const labels: Record<CoachMode, string> = {
      coach: '🎯 学习教练',
      tutor: '📖 知识导师',
      quiz: '📝 测验模式',
    }
    return labels[currentMode.value]
  })

  // ============================================================================
  // Chat Actions
  // ============================================================================

  /**
   * Send a message to the coach (non-streaming)
   */
  async function sendMessage(message: string) {
    loading.value = true
    error.value = null

    // Add user message
    messages.value.push({
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
      mode: currentMode.value,
      created_at: new Date().toISOString(),
    })

    try {
      const response = await coachService.chat({
        message,
        mode: currentMode.value,
        session_id: sessionId.value,
        goal_id: selectedGoalId.value,
      })

      sessionId.value = response.session_id

      // Add assistant message
      messages.value.push({
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.content,
        sources: response.sources,
        mode: currentMode.value,
        created_at: new Date().toISOString(),
      })

      return response
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || '发送消息失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Send a message with streaming
   */
  async function sendMessageStream(
    message: string,
    onToken?: (token: string) => void,
    onComplete?: (sid: string) => void
  ): Promise<void> {
    isStreaming.value = true
    streamingText.value = ''
    error.value = null

    // Add user message
    messages.value.push({
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
      mode: currentMode.value,
      created_at: new Date().toISOString(),
    })

    const token = localStorage.getItem('access_token') || ''

    try {
      for await (const event of coachService.chatStream(
        message,
        currentMode.value,
        token,
        sessionId.value,
        selectedGoalId.value
      )) {
        const data = event as CoachStreamEvent

        switch (data.type) {
          case 'start':
            // Session started
            break

          case 'token':
            streamingText.value += data.content
            onToken?.(data.content)
            break

          case 'done':
            sessionId.value = data.session_id

            // Add assistant message
            messages.value.push({
              id: `assistant-${Date.now()}`,
              role: 'assistant',
              content: streamingText.value,
              mode: currentMode.value,
              created_at: new Date().toISOString(),
            })

            onComplete?.(data.session_id)
            break

          case 'error':
            error.value = data.content
            break
        }
      }
    } catch (err: any) {
      error.value = err.message || '流式传输失败'
      throw err
    } finally {
      isStreaming.value = false
    }
  }

  /**
   * Start a new chat session
   */
  function startNewChat() {
    messages.value = []
    sessionId.value = null
    streamingText.value = ''
    error.value = null
  }

  /**
   * Set coaching mode
   */
  function setMode(mode: CoachMode) {
    currentMode.value = mode
  }

  /**
   * Set selected goal for coaching context
   */
  function setSelectedGoal(goalId: string | null) {
    selectedGoalId.value = goalId
  }

  // ============================================================================
  // Goal Actions
  // ============================================================================

  /**
   * Load all goals
   */
  async function loadGoals(status?: string) {
    loading.value = true
    error.value = null

    try {
      goals.value = await coachService.listGoals(status)
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || '加载目标失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Create a new goal
   */
  async function createGoal(data: GoalCreate) {
    loading.value = true
    error.value = null

    try {
      const goal = await coachService.createGoal(data)
      goals.value.unshift(goal)
      return goal
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || '创建目标失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Update a goal
   */
  async function updateGoal(goalId: string, data: GoalUpdate) {
    loading.value = true
    error.value = null

    try {
      const updated = await coachService.updateGoal(goalId, data)
      const idx = goals.value.findIndex((g) => g.id === goalId)
      if (idx >= 0) {
        goals.value[idx] = updated
      }
      return updated
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || '更新目标失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  // ============================================================================
  // Session Actions
  // ============================================================================

  /**
   * Log a study session
   */
  async function logStudySession(data: SessionCreate) {
    loading.value = true
    error.value = null

    try {
      const session = await coachService.logSession(data)
      sessions.value.unshift(session)
      return session
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || '记录学习失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Load study sessions
   */
  async function loadSessions(goalId?: string) {
    loading.value = true
    error.value = null

    try {
      sessions.value = await coachService.listSessions(goalId)
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || '加载学习记录失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  // ============================================================================
  // Progress Actions
  // ============================================================================

  /**
   * Load progress report for a goal
   */
  async function loadProgress(goalId: string) {
    loading.value = true
    error.value = null

    try {
      currentProgress.value = await coachService.getProgress(goalId)
      return currentProgress.value
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || '加载进度失败'
      throw err
    } finally {
      loading.value = false
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

  return {
    // State
    messages,
    currentMode,
    sessionId,
    selectedGoalId,
    isStreaming,
    streamingText,
    goals,
    sessions,
    currentProgress,
    loading,
    error,

    // Computed
    hasMessages,
    activeGoals,
    completedGoals,
    totalStudyMinutes,
    modeLabel,

    // Chat Actions
    sendMessage,
    sendMessageStream,
    startNewChat,
    setMode,
    setSelectedGoal,

    // Goal Actions
    loadGoals,
    createGoal,
    updateGoal,

    // Session Actions
    logStudySession,
    loadSessions,

    // Progress Actions
    loadProgress,

    // Utility
    clearError,
    stopStreaming,
  }
})
