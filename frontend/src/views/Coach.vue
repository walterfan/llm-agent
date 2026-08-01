<script setup lang="ts">
import { computed, ref, nextTick, onMounted } from 'vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import { useCoachStore } from '@/stores/coach'
import type { CoachMode } from '@/types/coach'

const store = useCoachStore()

const input = ref('')
const chatContainer = ref<HTMLElement | null>(null)

const modes: { value: CoachMode; label: string; icon: string; desc: string }[] = [
  { value: 'coach', label: '学习教练', icon: '🎯', desc: '激励与规划' },
  { value: 'tutor', label: '知识导师', icon: '📖', desc: '深入讲解' },
  { value: 'quiz', label: '测验模式', icon: '📝', desc: '出题测验' },
]

const canSend = computed(() => !!input.value.trim() && !store.isStreaming && !store.loading)

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

async function send() {
  if (!canSend.value) return
  const message = input.value.trim()
  input.value = ''
  store.clearError()

  scrollToBottom()

  try {
    await store.sendMessageStream(
      message,
      () => scrollToBottom(),
      () => scrollToBottom()
    )
  } catch (e) {
    // Error is handled in store
  }
}

function selectMode(mode: CoachMode) {
  store.setMode(mode)
}

function newChat() {
  store.startNewChat()
}

onMounted(() => {
  store.loadGoals()
})
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <AppHeader />
    <main class="mx-auto max-w-5xl px-4 py-8">
      <!-- Header -->
      <div class="mb-6 flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">🎓 AI 学习教练</h1>
          <p class="text-gray-600 mt-1">你的个人学习伙伴 — 教练激励、导师讲解、测验巩固</p>
        </div>
        <button
          class="px-3 py-2 rounded-md bg-gray-200 text-gray-700 text-sm hover:bg-gray-300"
          @click="newChat"
        >
          ✨ 新对话
        </button>
      </div>

      <!-- Mode Selector -->
      <div class="bg-white rounded-lg shadow p-4 mb-6">
        <label class="block text-sm font-medium text-gray-700 mb-3">选择模式</label>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <button
            v-for="m in modes"
            :key="m.value"
            class="flex items-center gap-3 p-3 rounded-lg border-2 transition-colors text-left"
            :class="
              store.currentMode === m.value
                ? 'border-primary-500 bg-primary-50'
                : 'border-gray-200 hover:border-gray-300'
            "
            @click="selectMode(m.value)"
          >
            <span class="text-2xl">{{ m.icon }}</span>
            <div>
              <div class="font-medium text-gray-900">
                {{ m.label }}
              </div>
              <div class="text-xs text-gray-500">
                {{ m.desc }}
              </div>
            </div>
          </button>
        </div>

        <!-- Goal selector -->
        <div v-if="store.activeGoals.length > 0" class="mt-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">关联学习目标（可选）</label>
          <select
            :value="store.selectedGoalId || ''"
            class="w-full border rounded-md px-3 py-2 text-sm"
            @change="store.setSelectedGoal(($event.target as HTMLSelectElement).value || null)"
          >
            <option value="">不关联目标</option>
            <option v-for="g in store.activeGoals" :key="g.id" :value="g.id">
              {{ g.subject }}
            </option>
          </select>
        </div>
      </div>

      <!-- Chat Area -->
      <div class="bg-white rounded-lg shadow">
        <div ref="chatContainer" class="p-4 space-y-3 max-h-[500px] overflow-y-auto">
          <!-- Empty state -->
          <div
            v-if="!store.hasMessages && !store.streamingText"
            class="text-center py-12 text-gray-400"
          >
            <div class="text-4xl mb-3">
              {{ modes.find((m) => m.value === store.currentMode)?.icon }}
            </div>
            <p>{{ store.modeLabel }} 模式已就绪</p>
            <p class="text-sm mt-1">输入你的问题开始对话</p>
          </div>

          <!-- Messages -->
          <div v-for="(msg, idx) in store.messages" :key="idx" class="flex">
            <div
              class="max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap"
              :class="
                msg.role === 'user'
                  ? 'ml-auto bg-primary-600 text-white'
                  : 'mr-auto bg-gray-100 text-gray-900'
              "
            >
              {{ msg.content }}
              <!-- Sources -->
              <div
                v-if="msg.sources && msg.sources.length > 0"
                class="mt-2 pt-2 border-t border-gray-200 text-xs text-gray-500"
              >
                📚 参考来源:
                <span v-for="(s, si) in msg.sources" :key="si" class="ml-1">
                  {{ s.title }}({{ (s.score * 100).toFixed(0) }}%)
                </span>
              </div>
            </div>
          </div>

          <!-- Streaming text -->
          <div v-if="store.streamingText" class="flex">
            <div
              class="mr-auto max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap bg-gray-100 text-gray-900"
            >
              {{ store.streamingText }}
              <span class="inline-block w-2 h-4 bg-primary-500 animate-pulse ml-0.5" />
            </div>
          </div>
        </div>

        <!-- Error -->
        <div
          v-if="store.error"
          class="mx-4 mb-4 p-3 rounded border border-red-200 bg-red-50 text-red-700 text-sm"
        >
          {{ store.error }}
        </div>

        <!-- Input -->
        <div class="border-t p-4 flex gap-2">
          <input
            v-model="input"
            type="text"
            class="flex-1 border rounded-md px-3 py-2 text-sm"
            :placeholder="store.currentMode === 'quiz' ? '输入答案或请求出题…' : '输入你的问题…'"
            @keydown.enter="send"
          />
          <button
            class="px-4 py-2 rounded-md bg-primary-600 text-white text-sm disabled:opacity-50"
            :disabled="!canSend"
            @click="send"
          >
            {{ store.isStreaming ? '⏳' : '发送' }}
          </button>
        </div>
      </div>
    </main>
  </div>
</template>
