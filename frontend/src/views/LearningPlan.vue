<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import { useCoachStore } from '@/stores/coach'
import type { GoalStatus, Difficulty } from '@/types/coach'

const store = useCoachStore()

// Goal form
const showGoalForm = ref(false)
const goalSubject = ref('')
const goalDescription = ref('')
const goalDailyMinutes = ref(30)
const goalDeadline = ref('')

// Session form
const showSessionForm = ref(false)
const sessionGoalId = ref('')
const sessionMinutes = ref(25)
const sessionNotes = ref('')
const sessionDifficulty = ref<Difficulty | ''>('')

// Selected goal for progress
const selectedProgressGoalId = ref<string | null>(null)

const statusLabels: Record<GoalStatus, { label: string; color: string }> = {
  active: { label: '进行中', color: 'bg-green-100 text-green-700' },
  completed: { label: '已完成', color: 'bg-blue-100 text-blue-700' },
  paused: { label: '已暂停', color: 'bg-yellow-100 text-yellow-700' },
  abandoned: { label: '已放弃', color: 'bg-gray-100 text-gray-500' },
}

const difficultyLabels: Record<Difficulty, string> = {
  easy: '😊 简单',
  medium: '🤔 适中',
  hard: '😤 困难',
}

onMounted(() => {
  store.loadGoals()
  store.loadSessions()
})

async function createGoal() {
  if (!goalSubject.value.trim()) return

  try {
    await store.createGoal({
      subject: goalSubject.value.trim(),
      description: goalDescription.value.trim() || undefined,
      daily_target_minutes: goalDailyMinutes.value,
      deadline: goalDeadline.value || undefined,
    })
    goalSubject.value = ''
    goalDescription.value = ''
    goalDailyMinutes.value = 30
    goalDeadline.value = ''
    showGoalForm.value = false
  } catch (e) {
    // Error handled in store
  }
}

async function updateGoalStatus(goalId: string, status: GoalStatus) {
  try {
    await store.updateGoal(goalId, { status })
  } catch (e) {
    // Error handled in store
  }
}

async function logSession() {
  if (sessionMinutes.value <= 0) return

  try {
    await store.logStudySession({
      goal_id: sessionGoalId.value || undefined,
      duration_minutes: sessionMinutes.value,
      notes: sessionNotes.value.trim() || undefined,
      difficulty: (sessionDifficulty.value as Difficulty) || undefined,
    })
    sessionGoalId.value = ''
    sessionMinutes.value = 25
    sessionNotes.value = ''
    sessionDifficulty.value = ''
    showSessionForm.value = false
  } catch (e) {
    // Error handled in store
  }
}

async function viewProgress(goalId: string) {
  selectedProgressGoalId.value = goalId
  try {
    await store.loadProgress(goalId)
  } catch (e) {
    // Error handled in store
  }
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
  })
}

function formatDateTime(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <AppHeader />
    <main class="mx-auto max-w-5xl px-4 py-8">
      <!-- Header -->
      <div class="mb-6">
        <h1 class="text-2xl font-bold text-gray-900">📅 学习计划</h1>
        <p class="text-gray-600 mt-1">设定目标、记录学习、追踪进度</p>
      </div>

      <!-- Quick Stats -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white rounded-lg shadow p-4 text-center">
          <div class="text-2xl font-bold text-primary-600">
            {{ store.activeGoals.length }}
          </div>
          <div class="text-sm text-gray-500">进行中目标</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4 text-center">
          <div class="text-2xl font-bold text-green-600">
            {{ store.completedGoals.length }}
          </div>
          <div class="text-sm text-gray-500">已完成目标</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4 text-center">
          <div class="text-2xl font-bold text-blue-600">
            {{ store.sessions.length }}
          </div>
          <div class="text-sm text-gray-500">学习次数</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4 text-center">
          <div class="text-2xl font-bold text-purple-600">
            {{ store.totalStudyMinutes }}
          </div>
          <div class="text-sm text-gray-500">总学习分钟</div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex gap-3 mb-6">
        <button
          class="px-4 py-2 rounded-md bg-primary-600 text-white text-sm hover:bg-primary-700"
          @click="showGoalForm = !showGoalForm"
        >
          🎯 {{ showGoalForm ? '取消' : '新建目标' }}
        </button>
        <button
          class="px-4 py-2 rounded-md bg-green-600 text-white text-sm hover:bg-green-700"
          @click="showSessionForm = !showSessionForm"
        >
          ⏱️ {{ showSessionForm ? '取消' : '记录学习' }}
        </button>
      </div>

      <!-- Goal Form -->
      <div v-if="showGoalForm" class="bg-white rounded-lg shadow p-6 mb-6">
        <h2 class="text-lg font-semibold mb-4">新建学习目标</h2>
        <div class="space-y-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">学习主题 *</label>
            <input
              v-model="goalSubject"
              type="text"
              class="w-full border rounded-md px-3 py-2 text-sm"
              placeholder="例如: Python 进阶、机器学习基础"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <textarea
              v-model="goalDescription"
              rows="2"
              class="w-full border rounded-md px-3 py-2 text-sm"
              placeholder="详细描述你的学习目标…"
            />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">每日目标（分钟）</label>
              <input
                v-model.number="goalDailyMinutes"
                type="number"
                min="5"
                max="480"
                class="w-full border rounded-md px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">截止日期</label>
              <input
                v-model="goalDeadline"
                type="date"
                class="w-full border rounded-md px-3 py-2 text-sm"
              />
            </div>
          </div>
          <button
            class="px-4 py-2 rounded-md bg-primary-600 text-white text-sm disabled:opacity-50"
            :disabled="!goalSubject.trim() || store.loading"
            @click="createGoal"
          >
            创建目标
          </button>
        </div>
      </div>

      <!-- Session Form -->
      <div v-if="showSessionForm" class="bg-white rounded-lg shadow p-6 mb-6">
        <h2 class="text-lg font-semibold mb-4">记录学习</h2>
        <div class="space-y-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">关联目标</label>
            <select v-model="sessionGoalId" class="w-full border rounded-md px-3 py-2 text-sm">
              <option value="">不关联</option>
              <option v-for="g in store.activeGoals" :key="g.id" :value="g.id">
                {{ g.subject }}
              </option>
            </select>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">学习时长（分钟）*</label>
              <input
                v-model.number="sessionMinutes"
                type="number"
                min="1"
                max="480"
                class="w-full border rounded-md px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">难度</label>
              <select
                v-model="sessionDifficulty"
                class="w-full border rounded-md px-3 py-2 text-sm"
              >
                <option value="">不选择</option>
                <option value="easy">😊 简单</option>
                <option value="medium">🤔 适中</option>
                <option value="hard">😤 困难</option>
              </select>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">笔记</label>
            <textarea
              v-model="sessionNotes"
              rows="2"
              class="w-full border rounded-md px-3 py-2 text-sm"
              placeholder="今天学了什么…"
            />
          </div>
          <button
            class="px-4 py-2 rounded-md bg-green-600 text-white text-sm disabled:opacity-50"
            :disabled="sessionMinutes <= 0 || store.loading"
            @click="logSession"
          >
            记录
          </button>
        </div>
      </div>

      <!-- Goals List -->
      <div class="bg-white rounded-lg shadow mb-6">
        <div class="p-4 border-b">
          <h2 class="text-lg font-semibold">🎯 学习目标</h2>
        </div>

        <div v-if="store.goals.length === 0" class="p-8 text-center text-gray-400">
          还没有学习目标，点击"新建目标"开始
        </div>

        <div v-else class="divide-y">
          <div v-for="goal in store.goals" :key="goal.id" class="p-4">
            <div class="flex items-center justify-between">
              <div class="flex-1">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-gray-900">{{ goal.subject }}</span>
                  <span
                    class="text-xs px-2 py-0.5 rounded-full"
                    :class="statusLabels[goal.status].color"
                  >
                    {{ statusLabels[goal.status].label }}
                  </span>
                </div>
                <div class="text-sm text-gray-500 mt-1">
                  每日 {{ goal.daily_target_minutes }} 分钟
                  <span v-if="goal.deadline"> · 截止 {{ formatDate(goal.deadline) }}</span>
                  <span v-if="goal.description"> · {{ goal.description }}</span>
                </div>
              </div>
              <div class="flex gap-2 ml-4">
                <button
                  class="text-sm text-primary-600 hover:text-primary-800"
                  @click="viewProgress(goal.id)"
                >
                  📊 进度
                </button>
                <button
                  v-if="goal.status === 'active'"
                  class="text-sm text-green-600 hover:text-green-800"
                  @click="updateGoalStatus(goal.id, 'completed')"
                >
                  ✅ 完成
                </button>
                <button
                  v-if="goal.status === 'active'"
                  class="text-sm text-yellow-600 hover:text-yellow-800"
                  @click="updateGoalStatus(goal.id, 'paused')"
                >
                  ⏸️ 暂停
                </button>
                <button
                  v-if="goal.status === 'paused'"
                  class="text-sm text-green-600 hover:text-green-800"
                  @click="updateGoalStatus(goal.id, 'active')"
                >
                  ▶️ 恢复
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Progress Report -->
      <div v-if="store.currentProgress" class="bg-white rounded-lg shadow mb-6">
        <div class="p-4 border-b">
          <h2 class="text-lg font-semibold">
            📊 进度报告: {{ store.currentProgress.goal.subject }}
          </h2>
        </div>
        <div class="p-4">
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="text-center">
              <div class="text-xl font-bold text-primary-600">
                {{ store.currentProgress.total_sessions }}
              </div>
              <div class="text-xs text-gray-500">学习次数</div>
            </div>
            <div class="text-center">
              <div class="text-xl font-bold text-blue-600">
                {{ store.currentProgress.total_minutes }}
              </div>
              <div class="text-xs text-gray-500">总分钟数</div>
            </div>
            <div class="text-center">
              <div class="text-xl font-bold text-green-600">
                {{ store.currentProgress.current_streak_days }} 🔥
              </div>
              <div class="text-xs text-gray-500">当前连续天数</div>
            </div>
            <div class="text-center">
              <div class="text-xl font-bold text-purple-600">
                {{ store.currentProgress.longest_streak_days }}
              </div>
              <div class="text-xs text-gray-500">最长连续天数</div>
            </div>
          </div>
          <div class="mt-4">
            <div class="flex items-center justify-between text-sm mb-1">
              <span class="text-gray-600">完成进度</span>
              <span class="font-medium">{{ store.currentProgress.completion_percentage }}%</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
              <div
                class="bg-primary-600 h-2 rounded-full transition-all"
                :style="{ width: `${Math.min(100, store.currentProgress.completion_percentage)}%` }"
              />
            </div>
            <div
              v-if="store.currentProgress.days_remaining !== null"
              class="text-xs text-gray-500 mt-1"
            >
              剩余 {{ store.currentProgress.days_remaining }} 天
            </div>
          </div>
        </div>
      </div>

      <!-- Recent Sessions -->
      <div class="bg-white rounded-lg shadow">
        <div class="p-4 border-b">
          <h2 class="text-lg font-semibold">⏱️ 最近学习记录</h2>
        </div>

        <div v-if="store.sessions.length === 0" class="p-8 text-center text-gray-400">
          还没有学习记录
        </div>

        <div v-else class="divide-y">
          <div
            v-for="s in store.sessions.slice(0, 20)"
            :key="s.id"
            class="p-3 flex items-center gap-3"
          >
            <div class="text-sm text-gray-500 w-24">
              {{ formatDateTime(s.created_at) }}
            </div>
            <div class="font-medium text-primary-600 w-16">{{ s.duration_minutes }} 分钟</div>
            <div v-if="s.difficulty" class="text-sm">
              {{ difficultyLabels[s.difficulty] }}
            </div>
            <div v-if="s.notes" class="text-sm text-gray-600 truncate flex-1">
              {{ s.notes }}
            </div>
          </div>
        </div>
      </div>

      <!-- Error -->
      <div
        v-if="store.error"
        class="mt-4 p-3 rounded border border-red-200 bg-red-50 text-red-700 text-sm"
      >
        {{ store.error }}
      </div>
    </main>
  </div>
</template>
