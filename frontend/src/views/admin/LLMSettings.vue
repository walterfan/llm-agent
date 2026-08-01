<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import { useLLMSettingsStore } from '@/stores/llmSettings'
import type { LLMSettingsUpdate } from '@/types/llmSettings'

const store = useLLMSettingsStore()

type TabName = 'chat' | 'embedding' | 'image'
const activeTab = ref<TabName>('chat')

const form = ref<LLMSettingsUpdate>({
  chat_base_url: null,
  chat_api_key: null,
  chat_model: null,
  chat_temperature: null,
  embedding_base_url: null,
  embedding_api_key: null,
  embedding_model: null,
  image_base_url: null,
  image_api_key: null,
  image_model: null,
})

// Track which API key fields the user actively edited (to avoid sending masked keys back)
const chatKeyEdited = ref(false)
const embeddingKeyEdited = ref(false)
const imageKeyEdited = ref(false)

// Visibility toggles for API key fields
const showChatKey = ref(false)
const showEmbeddingKey = ref(false)
const showImageKey = ref(false)

function populateForm() {
  const s = store.settings
  if (!s) return
  form.value = {
    chat_base_url: s.chat_base_url ?? null,
    chat_api_key: null,
    chat_model: s.chat_model ?? null,
    chat_temperature: s.chat_temperature ?? null,
    embedding_base_url: s.embedding_base_url ?? null,
    embedding_api_key: null,
    embedding_model: s.embedding_model ?? null,
    image_base_url: s.image_base_url ?? null,
    image_api_key: null,
    image_model: s.image_model ?? null,
  }
  chatKeyEdited.value = false
  embeddingKeyEdited.value = false
  imageKeyEdited.value = false
}

watch(() => store.settings, populateForm)

async function handleSave() {
  const data: LLMSettingsUpdate = { ...form.value }

  // Only send API keys that were actually edited
  if (!chatKeyEdited.value) delete data.chat_api_key
  if (!embeddingKeyEdited.value) delete data.embedding_api_key
  if (!imageKeyEdited.value) delete data.image_api_key

  await store.saveSettings(data)
  chatKeyEdited.value = false
  embeddingKeyEdited.value = false
  imageKeyEdited.value = false
}

function handleReset() {
  populateForm()
  store.clearMessages()
}

onMounted(async () => {
  await store.loadSettings()
})
</script>

<template>
  <AppLayout>
    <div class="max-w-4xl mx-auto">
      <!-- Header -->
      <div class="mb-6">
        <h1 class="text-3xl font-bold text-gray-900">LLM Settings</h1>
        <p class="mt-1 text-gray-600">
          Configure LLM providers for text generation, embeddings, and image generation. Empty
          fields fall back to server defaults.
        </p>
      </div>

      <!-- Alert Messages -->
      <Transition name="fade">
        <div
          v-if="store.error"
          class="mb-4 bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-2"
        >
          <span class="text-red-500 flex-shrink-0">&#x274C;</span>
          <span class="text-red-800 text-sm">{{ store.error }}</span>
        </div>
      </Transition>
      <Transition name="fade">
        <div
          v-if="store.successMessage"
          class="mb-4 bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-2"
        >
          <span class="text-green-500 flex-shrink-0">&#x2705;</span>
          <span class="text-green-800 text-sm">{{ store.successMessage }}</span>
        </div>
      </Transition>

      <!-- Loading -->
      <div v-if="store.loading" class="flex items-center justify-center py-20">
        <svg class="animate-spin h-8 w-8 text-blue-500" fill="none" viewBox="0 0 24 24">
          <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
          />
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      </div>

      <template v-else>
        <!-- Tabs -->
        <div class="flex gap-1 mb-6 bg-gray-100 p-1 rounded-lg w-fit">
          <button
            v-for="tab in ['chat', 'embedding', 'image'] as const"
            :key="tab"
            :class="[
              'px-5 py-2.5 rounded-md text-sm font-medium transition-all',
              activeTab === tab
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900',
            ]"
            @click="activeTab = tab"
          >
            <span v-if="tab === 'chat'">Text Generation</span>
            <span v-else-if="tab === 'embedding'">Embedding</span>
            <span v-else>Image Generation</span>
          </button>
        </div>

        <form @submit.prevent="handleSave">
          <!-- ===== Text Generation Tab ===== -->
          <div v-show="activeTab === 'chat'" class="bg-white rounded-lg shadow p-6 space-y-5">
            <div>
              <h2 class="text-lg font-semibold text-gray-900 mb-1">Text Generation (Chat)</h2>
              <p class="text-sm text-gray-500">
                Configure the LLM used for chat, coaching, translation, and other text generation
                tasks.
              </p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div class="md:col-span-2">
                <label class="block text-sm font-medium text-gray-700 mb-1">API Base URL</label>
                <input
                  v-model="form.chat_base_url"
                  type="url"
                  :placeholder="store.defaults?.chat_base_url || 'https://api.openai.com/v1'"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <p class="mt-1 text-xs text-gray-400">
                  OpenAI-compatible endpoint. Supports OpenAI, DeepSeek, Ollama, vLLM, etc.
                </p>
              </div>

              <div class="md:col-span-2">
                <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                <div class="relative">
                  <input
                    v-model="form.chat_api_key"
                    :type="showChatKey ? 'text' : 'password'"
                    :placeholder="
                      store.settings?.chat_api_key_set
                        ? '(key is set — leave blank to keep current)'
                        : 'sk-...'
                    "
                    class="w-full border border-gray-300 rounded-lg px-3 py-2.5 pr-20 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    @input="chatKeyEdited = true"
                  />
                  <button
                    type="button"
                    class="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-500 hover:text-gray-700 px-2 py-1"
                    @click="showChatKey = !showChatKey"
                  >
                    {{ showChatKey ? 'Hide' : 'Show' }}
                  </button>
                </div>
                <p v-if="store.maskedKeys?.chat_api_key" class="mt-1 text-xs text-gray-400">
                  Current:
                  <code class="bg-gray-100 px-1 rounded">{{ store.maskedKeys.chat_api_key }}</code>
                </p>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Model</label>
                <input
                  v-model="form.chat_model"
                  type="text"
                  :placeholder="store.defaults?.chat_model || 'gpt-3.5-turbo'"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <p class="mt-1 text-xs text-gray-400">
                  e.g. gpt-4o, deepseek-chat, llama3.1, qwen2.5
                </p>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Temperature</label>
                <div class="flex items-center gap-3">
                  <input
                    v-model.number="form.chat_temperature"
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    class="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                  />
                  <input
                    v-model.number="form.chat_temperature"
                    type="number"
                    min="0"
                    max="2"
                    step="0.1"
                    class="w-20 border border-gray-300 rounded-lg px-2 py-2 text-sm text-center focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <p class="mt-1 text-xs text-gray-400">
                  0 = deterministic, 1 = balanced, 2 = creative
                </p>
              </div>
            </div>
          </div>

          <!-- ===== Embedding Tab ===== -->
          <div v-show="activeTab === 'embedding'" class="bg-white rounded-lg shadow p-6 space-y-5">
            <div>
              <h2 class="text-lg font-semibold text-gray-900 mb-1">Embedding Model</h2>
              <p class="text-sm text-gray-500">
                Configure the embedding model used for the RAG knowledge base and semantic search.
                Leave empty to use text generation settings.
              </p>
            </div>

            <div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <p class="text-sm text-blue-800">
                <strong>Tip:</strong> Many chat APIs (e.g. DeepSeek) don't provide embedding
                endpoints. You can point embeddings to a different provider like OpenAI.
              </p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div class="md:col-span-2">
                <label class="block text-sm font-medium text-gray-700 mb-1">API Base URL</label>
                <input
                  v-model="form.embedding_base_url"
                  type="url"
                  :placeholder="
                    store.defaults?.embedding_base_url || 'Falls back to Chat API Base URL'
                  "
                  class="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div class="md:col-span-2">
                <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                <div class="relative">
                  <input
                    v-model="form.embedding_api_key"
                    :type="showEmbeddingKey ? 'text' : 'password'"
                    :placeholder="
                      store.settings?.embedding_api_key_set
                        ? '(key is set — leave blank to keep current)'
                        : 'Falls back to Chat API Key'
                    "
                    class="w-full border border-gray-300 rounded-lg px-3 py-2.5 pr-20 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    @input="embeddingKeyEdited = true"
                  />
                  <button
                    type="button"
                    class="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-500 hover:text-gray-700 px-2 py-1"
                    @click="showEmbeddingKey = !showEmbeddingKey"
                  >
                    {{ showEmbeddingKey ? 'Hide' : 'Show' }}
                  </button>
                </div>
                <p v-if="store.maskedKeys?.embedding_api_key" class="mt-1 text-xs text-gray-400">
                  Current:
                  <code class="bg-gray-100 px-1 rounded">{{
                    store.maskedKeys.embedding_api_key
                  }}</code>
                </p>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Model</label>
                <input
                  v-model="form.embedding_model"
                  type="text"
                  :placeholder="store.defaults?.embedding_model || 'text-embedding-3-small'"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <p class="mt-1 text-xs text-gray-400">
                  e.g. text-embedding-3-small, text-embedding-ada-002
                </p>
              </div>
            </div>
          </div>

          <!-- ===== Image Generation Tab ===== -->
          <div v-show="activeTab === 'image'" class="bg-white rounded-lg shadow p-6 space-y-5">
            <div>
              <h2 class="text-lg font-semibold text-gray-900 mb-1">Image Generation</h2>
              <p class="text-sm text-gray-500">
                Configure the image generation model (optional). Used for AI-powered image creation
                tasks.
              </p>
            </div>

            <div class="bg-amber-50 border border-amber-200 rounded-lg p-3">
              <p class="text-sm text-amber-800">
                <strong>Note:</strong> Image generation is not yet integrated into agents. Configure
                now for future use.
              </p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div class="md:col-span-2">
                <label class="block text-sm font-medium text-gray-700 mb-1">API Base URL</label>
                <input
                  v-model="form.image_base_url"
                  type="url"
                  placeholder="https://api.openai.com/v1"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div class="md:col-span-2">
                <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                <div class="relative">
                  <input
                    v-model="form.image_api_key"
                    :type="showImageKey ? 'text' : 'password'"
                    :placeholder="
                      store.settings?.image_api_key_set
                        ? '(key is set — leave blank to keep current)'
                        : 'sk-...'
                    "
                    class="w-full border border-gray-300 rounded-lg px-3 py-2.5 pr-20 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    @input="imageKeyEdited = true"
                  />
                  <button
                    type="button"
                    class="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-500 hover:text-gray-700 px-2 py-1"
                    @click="showImageKey = !showImageKey"
                  >
                    {{ showImageKey ? 'Hide' : 'Show' }}
                  </button>
                </div>
                <p v-if="store.maskedKeys?.image_api_key" class="mt-1 text-xs text-gray-400">
                  Current:
                  <code class="bg-gray-100 px-1 rounded">{{ store.maskedKeys.image_api_key }}</code>
                </p>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Model</label>
                <input
                  v-model="form.image_model"
                  type="text"
                  placeholder="dall-e-3"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <p class="mt-1 text-xs text-gray-400">e.g. dall-e-3, stable-diffusion-xl, flux</p>
              </div>
            </div>
          </div>

          <!-- Server Defaults Info -->
          <div v-if="store.defaults" class="mt-6 bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h3 class="text-sm font-medium text-gray-700 mb-2">Server Defaults (from .env)</h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 text-xs text-gray-500">
              <div>
                Chat Base URL:
                <code class="text-gray-700">{{ store.defaults.chat_base_url || '—' }}</code>
              </div>
              <div>
                Chat Model:
                <code class="text-gray-700">{{ store.defaults.chat_model || '—' }}</code>
              </div>
              <div>
                Embedding Base URL:
                <code class="text-gray-700">{{ store.defaults.embedding_base_url || '—' }}</code>
              </div>
              <div>
                Embedding Model:
                <code class="text-gray-700">{{ store.defaults.embedding_model || '—' }}</code>
              </div>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="mt-6 flex items-center gap-3">
            <button
              type="submit"
              :disabled="store.saving"
              class="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition-colors"
            >
              {{ store.saving ? 'Saving...' : 'Save Settings' }}
            </button>
            <button
              type="button"
              :disabled="store.saving"
              class="px-6 py-2.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 text-sm font-medium transition-colors"
              @click="handleReset"
            >
              Reset
            </button>
          </div>
        </form>
      </template>
    </div>
  </AppLayout>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
