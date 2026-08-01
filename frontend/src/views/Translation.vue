<script setup lang="ts">
import { ref, computed } from 'vue'
import { marked } from 'marked'
import AppHeader from '@/components/layout/AppHeader.vue'
import {
  useTranslationStore,
  type TranslationResponse,
  type OutputMode,
  type StreamEvent,
} from '@/stores/translation'

const translationStore = useTranslationStore()

marked.setOptions({ breaks: true, gfm: true })

const urlInput = ref('')
const pastedText = ref('')
const fileInput = ref<File | null>(null)
const outputMode = ref<OutputMode>('chinese_only')
const useStreaming = ref(true)
const loading = ref(false)
const error = ref<string | null>(null)

const translatedMarkdown = ref('')
const explanation = ref('')
const summary = ref('')
const sourceTruncated = ref(false)

const hasUrl = computed(() => !!urlInput.value?.trim())
const hasPastedText = computed(() => !!pastedText.value?.trim())
const hasFile = computed(() => !!fileInput.value)
const canSubmit = computed(
  () =>
    (hasUrl.value && !hasFile.value && !hasPastedText.value) ||
    (hasFile.value && !hasUrl.value && !hasPastedText.value) ||
    (hasPastedText.value && !hasUrl.value && !hasFile.value)
)

function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  fileInput.value = target.files?.[0] ?? null
}

function clearResult() {
  translatedMarkdown.value = ''
  explanation.value = ''
  summary.value = ''
  sourceTruncated.value = false
  error.value = null
}

function buildFullMarkdown(): string {
  const parts: string[] = []
  const hr = '\n\n---\n\n'
  if (translatedMarkdown.value) {
    parts.push('# 翻译\n\n', translatedMarkdown.value)
  }
  if (explanation.value) {
    parts.push(hr, '# 解释\n\n', explanation.value)
  }
  if (summary.value) {
    parts.push(hr, '# 总结\n\n', summary.value)
  }
  return parts.join('')
}

const fullMarkdownHtml = computed(() => {
  const md = buildFullMarkdown()
  return md ? marked(md) : ''
})

function downloadMarkdown() {
  const md = buildFullMarkdown()
  if (!md) return
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'translation.md'
  a.click()
  URL.revokeObjectURL(a.href)
}

async function runNonStreaming() {
  clearResult()
  loading.value = true
  error.value = null
  try {
    let res: TranslationResponse
    if (hasUrl.value) {
      res = await translationStore.translateByUrl(urlInput.value.trim(), outputMode.value)
    } else if (hasPastedText.value) {
      res = await translationStore.translateByText(pastedText.value.trim(), outputMode.value)
    } else if (fileInput.value) {
      res = await translationStore.translateByFile(fileInput.value, outputMode.value)
    } else {
      throw new Error('Provide URL, pasted text, or file')
    }
    translatedMarkdown.value = res.translated_markdown
    explanation.value = res.explanation
    summary.value = res.summary
    sourceTruncated.value = res.source_truncated
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function runStreaming() {
  clearResult()
  loading.value = true
  error.value = null
  try {
    const onEvent = (ev: StreamEvent) => {
      if (ev.event === 'token' && ev.data !== undefined) {
        translatedMarkdown.value += ev.data
      } else if (ev.event === 'explanation_token' && ev.data !== undefined) {
        explanation.value += ev.data
      } else if (ev.event === 'explanation' && ev.data !== undefined) {
        explanation.value = ev.data
      } else if (ev.event === 'summary_token' && ev.data !== undefined) {
        summary.value += ev.data
      } else if (ev.event === 'summary' && ev.data !== undefined) {
        summary.value = ev.data
      } else if (ev.event === 'done') {
        if (ev.source_truncated) sourceTruncated.value = true
      } else if (ev.event === 'error' && ev.data) {
        error.value = ev.data
      }
    }
    if (hasUrl.value) {
      await translationStore.streamTranslationByUrl(
        urlInput.value.trim(),
        outputMode.value,
        onEvent
      )
    } else if (hasPastedText.value) {
      await translationStore.streamTranslationByText(
        pastedText.value.trim(),
        outputMode.value,
        onEvent
      )
    } else if (fileInput.value) {
      await translationStore.streamTranslationByFile(fileInput.value, outputMode.value, onEvent)
    } else {
      throw new Error('Provide URL, pasted text, or file')
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!canSubmit.value) return
  if (useStreaming.value) {
    await runStreaming()
  } else {
    await runNonStreaming()
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <AppHeader />
    <main class="mx-auto max-w-4xl px-4 py-8">
      <h1 class="text-2xl font-bold text-gray-900 mb-6">翻译 (Translation)</h1>
      <p class="text-gray-600 mb-6">
        输入文章 URL、粘贴文本，或上传 PDF / 文本 / Markdown 文件，获取中文翻译、解释与总结。
      </p>

      <!-- Input -->
      <div class="bg-white rounded-lg shadow p-6 mb-6">
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">URL</label>
            <input
              v-model="urlInput"
              type="url"
              placeholder="https://example.com/article"
              class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
              :disabled="!!fileInput || !!pastedText?.trim()"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">或粘贴文本</label>
            <textarea
              v-model="pastedText"
              rows="6"
              placeholder="将英文内容粘贴到此处…"
              class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
              :disabled="!!fileInput || !!urlInput?.trim()"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1"
              >或上传文件 (PDF / .txt / .md)</label
            >
            <input
              type="file"
              accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
              class="w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-primary-50 file:text-primary-700"
              @change="onFileChange"
            />
            <p v-if="fileInput" class="mt-1 text-sm text-gray-500">
              {{ fileInput.name }}
            </p>
          </div>
          <div class="flex flex-wrap items-center gap-4">
            <div class="flex items-center gap-2">
              <label class="text-sm font-medium text-gray-700">输出模式</label>
              <select
                v-model="outputMode"
                class="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
              >
                <option value="chinese_only">仅中文</option>
                <option value="bilingual">中英对照</option>
              </select>
            </div>
            <label class="flex items-center gap-2 cursor-pointer">
              <input v-model="useStreaming" type="checkbox" class="rounded text-primary-600" />
              <span class="text-sm text-gray-700">实时流式输出</span>
            </label>
          </div>
          <button
            type="button"
            :disabled="!canSubmit || loading"
            class="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            @click="handleSubmit"
          >
            {{ loading ? '翻译中…' : '开始翻译' }}
          </button>
        </div>
        <p
          v-if="!canSubmit && (hasUrl || hasFile || hasPastedText)"
          class="mt-2 text-sm text-amber-600"
        >
          请只选择一种输入方式：URL、粘贴文本或上传文件，不能同时使用多种。
        </p>
      </div>

      <!-- Error -->
      <div v-if="error" class="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
        {{ error }}
      </div>

      <!-- Result -->
      <div
        v-if="translatedMarkdown || explanation || summary"
        class="bg-white rounded-lg shadow p-6"
      >
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-lg font-semibold text-gray-900">翻译结果</h2>
          <button
            type="button"
            class="text-sm text-primary-600 hover:text-primary-700"
            @click="downloadMarkdown"
          >
            下载为 .md
          </button>
        </div>
        <p v-if="sourceTruncated" class="text-sm text-amber-600 mb-2">（原文已截断）</p>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div class="prose prose-sm max-w-none translation-result" v-html="fullMarkdownHtml" />
      </div>
    </main>
  </div>
</template>
