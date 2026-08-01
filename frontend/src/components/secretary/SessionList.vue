<script setup lang="ts">
import type { ChatSession } from '@/types/secretary'

defineProps<{
  sessions: ChatSession[]
  currentSessionId?: string
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'select', session: ChatSession): void
  (e: 'delete', sessionId: string): void
  (e: 'new'): void
}>()

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) {
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
    })
  } else if (days === 1) {
    return '昨天'
  } else if (days < 7) {
    return `${days}天前`
  } else {
    return date.toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
    })
  }
}

function handleDelete(event: Event, sessionId: string) {
  event.stopPropagation()
  if (confirm('确定要删除这个会话吗？')) {
    emit('delete', sessionId)
  }
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="p-4 border-b border-gray-200">
      <button
        type="button"
        class="w-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center justify-center gap-2"
        @click="emit('new')"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 4v16m8-8H4"
          />
        </svg>
        新对话
      </button>
    </div>

    <!-- Session list -->
    <div class="flex-1 overflow-y-auto">
      <div v-if="loading" class="p-4 text-center text-gray-500">加载中...</div>

      <div v-else-if="sessions.length === 0" class="p-4 text-center text-gray-500">暂无会话</div>

      <div v-else class="divide-y divide-gray-100">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="p-3 cursor-pointer hover:bg-gray-50 transition-colors group"
          :class="{
            'bg-blue-50 border-r-2 border-blue-500': session.id === currentSessionId,
          }"
          @click="emit('select', session)"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-gray-800 truncate">
                {{ session.title || '新对话' }}
              </div>
              <div class="flex items-center gap-2 mt-1 text-xs text-gray-500">
                <span>{{ session.message_count }} 条消息</span>
                <span>·</span>
                <span>{{ formatDate(session.updated_at) }}</span>
              </div>
            </div>

            <!-- Delete button -->
            <button
              type="button"
              class="p-1 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
              title="删除会话"
              @click="handleDelete($event, session.id)"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
