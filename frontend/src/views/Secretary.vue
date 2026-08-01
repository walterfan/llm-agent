<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { useSecretaryStore } from '@/stores/secretary'
import { useLearningStore } from '@/stores/learning'
import AppHeader from '@/components/layout/AppHeader.vue'
import ChatMessage from '@/components/secretary/ChatMessage.vue'
import ChatInput from '@/components/secretary/ChatInput.vue'
import SessionList from '@/components/secretary/SessionList.vue'
import ToolList from '@/components/secretary/ToolList.vue'
import type { ChatSession, ToolInfo, LearningRecordType } from '@/types/secretary'

const secretaryStore = useSecretaryStore()
const learningStore = useLearningStore()

const messagesContainer = ref<HTMLElement | null>(null)
const showSidebar = ref(true)
const showTools = ref(false)

// Transport mode toggle
function toggleTransport() {
  const next = secretaryStore.transport === 'sse' ? 'ws' : 'sse'
  secretaryStore.setTransport(next)
  if (next === 'ws') {
    // WS will auto-fetch sessions on connect
  }
}

// Scroll to bottom when new messages arrive
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// Watch for new messages
watch(
  () => secretaryStore.currentMessages.length,
  () => scrollToBottom()
)

// Watch streaming text
watch(
  () => secretaryStore.streamingText,
  () => scrollToBottom()
)

// Handle sending message — auto-dispatches to SSE or WS
async function handleSend(message: string) {
  const sessionId = secretaryStore.currentSession?.id || null

  try {
    await secretaryStore.sendMessageAuto(
      message,
      sessionId || undefined,
      // onToken (SSE only — WS tokens are handled in store)
      () => {
        scrollToBottom()
      },
      // onToolCall
      (tool, args) => {
        console.log('Tool called:', tool, args)
      },
      // onToolResult
      (tool, result) => {
        console.log('Tool result:', tool, result)
      },
      // onComplete
      () => {
        // Refresh session list
        secretaryStore.listSessionsAuto()
      }
    )
  } catch (err) {
    console.error('Failed to send message:', err)
  }
}

// Handle session selection — auto-dispatch
async function handleSelectSession(session: ChatSession) {
  await secretaryStore.getSessionAuto(session.id)
}

// Handle session deletion — auto-dispatch
async function handleDeleteSession(sessionId: string) {
  await secretaryStore.deleteSessionAuto(sessionId)
}

// Handle new session
function handleNewSession() {
  secretaryStore.startNewSession()
}

// Handle tool selection
function handleSelectTool(tool: ToolInfo) {
  // Generate a prompt based on the tool
  const prompts: Record<string, string> = {
    learn_word: '请帮我学习单词 "example"',
    learn_sentence: '请帮我分析句子 "This is an example sentence."',
    learn_topic: '请帮我学习 "Kubernetes" 这个主题',
    learn_article: '请帮我学习这篇文章: https://example.com/article',
    answer_question: '请回答这个问题: 什么是微服务架构？',
    plan_idea: '请帮我规划这个想法: 构建一个AI助手',
    get_weather: '今天北京的天气怎么样？',
    calculate: '请计算 sqrt(16) + 2 * 3',
    get_datetime: '现在几点了？',
  }

  const prompt = prompts[tool.name] || `使用 ${tool.name} 工具`

  // Don't auto-send, just show a hint
  showTools.value = false
  alert(`提示: 你可以输入类似 "${prompt}" 的消息来使用此工具`)
}

// Expose save learning for future use in template
defineExpose({
  saveLearning: async (
    inputType: LearningRecordType,
    userInput: string,
    responsePayload: Record<string, unknown>
  ) => {
    try {
      await learningStore.saveLearningRecord({
        input_type: inputType,
        user_input: userInput,
        response_payload: responsePayload,
        session_id: secretaryStore.currentSession?.id || undefined,
      })
      alert('学习记录已保存！')
    } catch (err) {
      console.error('Failed to save learning record:', err)
    }
  },
})

// Initialize
onMounted(async () => {
  // Load sessions
  await secretaryStore.listSessionsAuto()

  // Load tools
  await secretaryStore.loadTools()

  // Start with a new session if none selected
  if (!secretaryStore.currentSession) {
    secretaryStore.startNewSession()
  }
})
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Top Navigation -->
    <AppHeader />

    <!-- Chat Interface -->
    <div class="flex h-[calc(100vh-64px)] bg-gray-100">
      <!-- Sidebar -->
      <aside v-show="showSidebar" class="w-64 bg-white border-r border-gray-200 flex-shrink-0">
        <SessionList
          :sessions="secretaryStore.sessions"
          :current-session-id="secretaryStore.currentSession?.id"
          :loading="secretaryStore.loading"
          @select="handleSelectSession"
          @delete="handleDeleteSession"
          @new="handleNewSession"
        />
      </aside>

      <!-- Main chat area -->
      <main class="flex-1 flex flex-col min-w-0">
        <!-- Header -->
        <header
          class="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between"
        >
          <div class="flex items-center gap-3">
            <button
              type="button"
              class="p-2 hover:bg-gray-100 rounded-lg lg:hidden"
              @click="showSidebar = !showSidebar"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </button>

            <h1 class="text-lg font-semibold text-gray-800">
              {{ secretaryStore.currentSession?.title || '个人秘书' }}
            </h1>
          </div>

          <div class="flex items-center gap-2">
            <!-- Transport Mode Toggle -->
            <button
              type="button"
              class="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg transition-all"
              :class="
                secretaryStore.transport === 'ws'
                  ? secretaryStore.wsConnected
                    ? 'bg-green-100 text-green-700 hover:bg-green-200'
                    : 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              "
              :title="
                secretaryStore.transport === 'ws'
                  ? `WebSocket ${secretaryStore.wsConnected ? '已连接' : '连接中...'} (${secretaryStore.wsOnlineCount} 在线)`
                  : 'SSE 模式 (点击切换到 WebSocket)'
              "
              @click="toggleTransport"
            >
              <span
                v-if="secretaryStore.transport === 'ws'"
                class="w-2 h-2 rounded-full"
                :class="secretaryStore.wsConnected ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'"
              />
              <span v-else class="w-2 h-2 rounded-full bg-gray-400" />
              {{ secretaryStore.transport === 'ws' ? 'WS' : 'SSE' }}
              <span
                v-if="secretaryStore.transport === 'ws' && secretaryStore.wsConnected"
                class="text-[10px] opacity-70"
              >
                ({{ secretaryStore.wsOnlineCount }})
              </span>
            </button>

            <router-link
              to="/learning"
              class="px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            >
              学习记录
            </router-link>

            <button
              type="button"
              class="p-2 hover:bg-gray-100 rounded-lg"
              :class="{ 'bg-blue-100': showTools }"
              title="工具列表"
              @click="showTools = !showTools"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
            </button>
          </div>
        </header>

        <!-- Messages -->
        <div ref="messagesContainer" class="flex-1 overflow-y-auto">
          <!-- Empty state -->
          <div
            v-if="secretaryStore.currentMessages.length === 0 && !secretaryStore.streamingText"
            class="flex flex-col items-center justify-center h-full text-gray-500"
          >
            <div class="text-6xl mb-4">🤖</div>
            <h2 class="text-xl font-medium mb-2">你好！我是你的个人秘书</h2>
            <p class="text-sm">我可以帮你学习英语、了解新技术、回答问题等</p>
            <div class="mt-4 flex flex-wrap gap-2 justify-center max-w-md">
              <button
                v-for="suggestion in [
                  '学习单词 scamper',
                  '今天天气怎么样',
                  '什么是微服务',
                  '计算 2+2*3',
                ]"
                :key="suggestion"
                type="button"
                class="px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-full hover:bg-gray-50 transition-colors"
                @click="handleSend(suggestion)"
              >
                {{ suggestion }}
              </button>
            </div>
          </div>

          <!-- Messages list -->
          <div v-else>
            <ChatMessage
              v-for="msg in secretaryStore.currentMessages"
              :key="msg.id"
              :message="msg"
            />

            <!-- Streaming message -->
            <ChatMessage
              v-if="secretaryStore.isStreaming && secretaryStore.streamingText"
              :message="{
                id: 'streaming',
                role: 'assistant',
                content: secretaryStore.streamingText,
                tool_calls: secretaryStore.streamingToolCalls,
                created_at: new Date().toISOString(),
              }"
              :is-streaming="true"
            />
          </div>
        </div>

        <!-- Error display -->
        <div
          v-if="secretaryStore.error"
          class="px-4 py-2 bg-red-50 border-t border-red-200 text-red-600 text-sm"
        >
          {{ secretaryStore.error }}
          <button type="button" class="ml-2 underline" @click="secretaryStore.clearError()">
            关闭
          </button>
        </div>

        <!-- Input -->
        <ChatInput :disabled="secretaryStore.isStreaming" @send="handleSend" />
      </main>

      <!-- Tools sidebar -->
      <aside
        v-show="showTools"
        class="w-72 bg-white border-l border-gray-200 flex-shrink-0 overflow-y-auto"
      >
        <ToolList :tools="secretaryStore.tools" @select="handleSelectTool" />
      </aside>
    </div>
  </div>
</template>
