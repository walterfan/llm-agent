<script setup lang="ts">
import { computed, ref, nextTick } from 'vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import {
  usePhilosophyStore,
  type PhilosophyPreset,
  type PhilosophyStreamEvent,
} from '@/stores/philosophy'

const philosophyStore = usePhilosophyStore()

type ChatMsg = { role: 'user' | 'assistant'; content: string }

const messages = ref<ChatMsg[]>([])
const input = ref('')
const context = ref('')
const streamingText = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

const preset = ref<PhilosophyPreset>({
  school: 'mixed',
  tone: 'gentle',
  depth: 'medium',
  mode: 'advice',
  multi_perspective: false,
})

const canSend = computed(() => !!input.value.trim() && !loading.value)

async function send() {
  if (!canSend.value) return
  const message = input.value.trim()
  input.value = ''
  error.value = null
  streamingText.value = ''
  loading.value = true

  messages.value.push({ role: 'user', content: message })

  const onEvent = (ev: PhilosophyStreamEvent) => {
    if (ev.type === 'token') {
      streamingText.value += ev.content ?? ''
    } else if (ev.type === 'error') {
      error.value = ev.content || 'Error'
    } else if (ev.type === 'done') {
      if (streamingText.value.trim()) {
        messages.value.push({ role: 'assistant', content: streamingText.value })
      }
      streamingText.value = ''
      loading.value = false
    }
    nextTick(() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }))
  }

  try {
    await philosophyStore.chatStream(
      {
        message,
        preset: preset.value,
        context: context.value?.trim() ? context.value.trim() : undefined,
      },
      onEvent
    )
  } catch (e) {
    loading.value = false
    error.value = e instanceof Error ? e.message : String(e)
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <AppHeader />
    <main class="mx-auto max-w-5xl px-4 py-8">
      <div class="mb-6">
        <h1 class="text-2xl font-bold text-gray-900">🧠 Philosophy Master</h1>
        <p class="text-gray-600 mt-1">
          从不同哲学流派与角度，帮你澄清困惑、辨析价值，并给出可执行的建议与练习。
        </p>
      </div>

      <!-- Presets -->
      <div class="bg-white rounded-lg shadow p-4 mb-6">
        <div class="grid grid-cols-1 md:grid-cols-5 gap-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">School</label>
            <select v-model="preset.school" class="w-full border rounded-md px-3 py-2 text-sm">
              <option value="mixed">Mixed</option>
              <option value="eastern">Eastern</option>
              <option value="western">Western</option>
              <option value="zen">Zen</option>
              <option value="confucian">Confucian</option>
              <option value="stoic">Stoic</option>
              <option value="existential">Existential</option>
              <option value="kant">Kant</option>
              <option value="nietzsche">Nietzsche</option>
              <option value="schopenhauer">Schopenhauer</option>
              <option value="idealism">Idealism</option>
              <option value="materialism">Materialism</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Tone</label>
            <select v-model="preset.tone" class="w-full border rounded-md px-3 py-2 text-sm">
              <option value="gentle">Gentle</option>
              <option value="direct">Direct</option>
              <option value="rigorous">Rigorous</option>
              <option value="zen">Zen</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Depth</label>
            <select v-model="preset.depth" class="w-full border rounded-md px-3 py-2 text-sm">
              <option value="shallow">Shallow</option>
              <option value="medium">Medium</option>
              <option value="deep">Deep</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Mode</label>
            <select v-model="preset.mode" class="w-full border rounded-md px-3 py-2 text-sm">
              <option value="advice">Advice</option>
              <option value="compare">Compare</option>
              <option value="story">Story</option>
              <option value="daily_practice">Daily practice</option>
            </select>
          </div>
          <div class="flex items-end">
            <label class="flex items-center gap-2 text-sm text-gray-700">
              <input
                v-model="preset.multi_perspective"
                type="checkbox"
                class="rounded text-primary-600"
              />
              多视角
            </label>
          </div>
        </div>

        <div class="mt-3">
          <label class="block text-sm font-medium text-gray-700 mb-1">Context (optional)</label>
          <textarea
            v-model="context"
            rows="2"
            class="w-full border rounded-md px-3 py-2 text-sm"
            placeholder="补充背景（可选），例如：关系、时间线、限制条件…"
          />
        </div>
      </div>

      <!-- Chat -->
      <div class="bg-white rounded-lg shadow p-4">
        <div class="space-y-3">
          <div v-for="(m, idx) in messages" :key="idx" class="flex">
            <div
              class="max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap"
              :class="
                m.role === 'user'
                  ? 'ml-auto bg-primary-600 text-white'
                  : 'mr-auto bg-gray-100 text-gray-900'
              "
            >
              {{ m.content }}
            </div>
          </div>

          <div v-if="streamingText" class="flex">
            <div
              class="mr-auto max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap bg-gray-100 text-gray-900"
            >
              {{ streamingText }}
            </div>
          </div>
        </div>

        <div
          v-if="error"
          class="mt-4 p-3 rounded border border-red-200 bg-red-50 text-red-700 text-sm"
        >
          {{ error }}
        </div>

        <div class="mt-4 flex gap-2">
          <input
            v-model="input"
            type="text"
            class="flex-1 border rounded-md px-3 py-2 text-sm"
            placeholder="说说你的烦恼或困惑…"
            @keydown.enter="send"
          />
          <button
            class="px-4 py-2 rounded-md bg-primary-600 text-white text-sm disabled:opacity-50"
            :disabled="!canSend"
            @click="send"
          >
            {{ loading ? '…' : 'Send' }}
          </button>
        </div>
      </div>
    </main>
  </div>
</template>
