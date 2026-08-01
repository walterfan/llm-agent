<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import { useKnowledgeStore } from '@/stores/knowledge'

const store = useKnowledgeStore()

// Upload form
const showUploadForm = ref(false)
const uploadTitle = ref('')
const uploadContent = ref('')
const uploadTags = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

// Query
const queryText = ref('')

onMounted(() => {
  store.loadDocuments()
  store.loadStats()
})

async function uploadText() {
  if (!uploadTitle.value.trim() || !uploadContent.value.trim()) return

  try {
    await store.uploadDocument({
      title: uploadTitle.value.trim(),
      content: uploadContent.value.trim(),
      tags: uploadTags.value
        ? uploadTags.value
            .split(',')
            .map((t) => t.trim())
            .filter(Boolean)
        : [],
    })
    uploadTitle.value = ''
    uploadContent.value = ''
    uploadTags.value = ''
    showUploadForm.value = false
    store.loadStats()
  } catch (e) {
    // Error handled in store
  }
}

async function uploadFile(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  try {
    await store.uploadFile(file)
    target.value = ''
    await store.loadDocuments()
    await store.loadStats()
  } catch (e) {
    // Error handled in store
  }
}

async function deleteDoc(docId: string) {
  if (!confirm('确定要删除这个文档吗？')) return
  try {
    await store.deleteDocument(docId)
    store.loadStats()
  } catch (e) {
    // Error handled in store
  }
}

async function search() {
  if (!queryText.value.trim()) return
  try {
    await store.queryKnowledge(queryText.value.trim())
  } catch (e) {
    // Error handled in store
  }
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric',
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
      <div class="mb-6 flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">📚 知识库</h1>
          <p class="text-gray-600 mt-1">
            上传文档，构建你的个人知识库，AI 教练会基于这些内容回答问题
          </p>
        </div>
        <button
          class="px-3 py-2 rounded-md bg-primary-600 text-white text-sm hover:bg-primary-700"
          @click="showUploadForm = !showUploadForm"
        >
          {{ showUploadForm ? '取消' : '➕ 添加文档' }}
        </button>
      </div>

      <!-- Stats -->
      <div v-if="store.stats" class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white rounded-lg shadow p-4 text-center">
          <div class="text-2xl font-bold text-primary-600">
            {{ store.stats.total_documents }}
          </div>
          <div class="text-sm text-gray-500">文档数</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4 text-center">
          <div class="text-2xl font-bold text-primary-600">
            {{ store.stats.total_words.toLocaleString() }}
          </div>
          <div class="text-sm text-gray-500">总字数</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4 text-center">
          <div class="text-2xl font-bold text-primary-600">
            {{ store.stats.total_chunks }}
          </div>
          <div class="text-sm text-gray-500">知识块</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4 text-center">
          <div class="text-2xl font-bold text-primary-600">
            {{ Object.keys(store.stats.tags || {}).length }}
          </div>
          <div class="text-sm text-gray-500">标签数</div>
        </div>
      </div>

      <!-- Upload Form -->
      <div v-if="showUploadForm" class="bg-white rounded-lg shadow p-6 mb-6">
        <h2 class="text-lg font-semibold mb-4">添加文档</h2>

        <!-- File upload -->
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">上传文件 (PDF/TXT/MD)</label>
          <input
            ref="fileInput"
            type="file"
            accept=".pdf,.txt,.md,.markdown"
            class="w-full border rounded-md px-3 py-2 text-sm"
            @change="uploadFile"
          />
        </div>

        <div class="text-center text-gray-400 text-sm my-3">— 或者手动输入 —</div>

        <!-- Text upload -->
        <div class="space-y-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">标题</label>
            <input
              v-model="uploadTitle"
              type="text"
              class="w-full border rounded-md px-3 py-2 text-sm"
              placeholder="文档标题"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">内容</label>
            <textarea
              v-model="uploadContent"
              rows="6"
              class="w-full border rounded-md px-3 py-2 text-sm"
              placeholder="粘贴文档内容…"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">标签（逗号分隔）</label>
            <input
              v-model="uploadTags"
              type="text"
              class="w-full border rounded-md px-3 py-2 text-sm"
              placeholder="例如: python, 机器学习, 深度学习"
            />
          </div>
          <button
            class="px-4 py-2 rounded-md bg-primary-600 text-white text-sm disabled:opacity-50"
            :disabled="!uploadTitle.trim() || !uploadContent.trim() || store.uploading"
            @click="uploadText"
          >
            {{ store.uploading ? '上传中…' : '提交' }}
          </button>
        </div>
      </div>

      <!-- Search -->
      <div class="bg-white rounded-lg shadow p-4 mb-6">
        <label class="block text-sm font-medium text-gray-700 mb-2">🔍 语义搜索</label>
        <div class="flex gap-2">
          <input
            v-model="queryText"
            type="text"
            class="flex-1 border rounded-md px-3 py-2 text-sm"
            placeholder="输入问题，搜索知识库…"
            @keydown.enter="search"
          />
          <button
            class="px-4 py-2 rounded-md bg-primary-600 text-white text-sm disabled:opacity-50"
            :disabled="!queryText.trim() || store.querying"
            @click="search"
          >
            {{ store.querying ? '搜索中…' : '搜索' }}
          </button>
        </div>

        <!-- Query message (e.g. RAG unavailable) -->
        <div
          v-if="store.queryMessage"
          class="mt-4 p-3 rounded border border-amber-200 bg-amber-50 text-amber-800 text-sm"
        >
          {{ store.queryMessage }}
        </div>

        <!-- Query Results -->
        <div v-if="store.hasQueryResults" class="mt-4 space-y-3">
          <h3 class="text-sm font-medium text-gray-700">
            搜索结果 ({{ store.queryResults.length }})
          </h3>
          <div v-for="(r, idx) in store.queryResults" :key="idx" class="border rounded-lg p-3">
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm font-medium text-gray-900">
                {{ r.metadata?.title || '未知文档' }}
              </span>
              <span class="text-xs text-gray-500"> 相关度: {{ (r.score * 100).toFixed(0) }}% </span>
            </div>
            <p class="text-sm text-gray-600 whitespace-pre-wrap">
              {{ r.content }}
            </p>
          </div>
        </div>
      </div>

      <!-- Document List -->
      <div class="bg-white rounded-lg shadow">
        <div class="p-4 border-b">
          <h2 class="text-lg font-semibold">文档列表</h2>
        </div>

        <div v-if="store.loading && !store.hasDocuments" class="p-8 text-center text-gray-400">
          加载中…
        </div>

        <div v-else-if="!store.hasDocuments" class="p-8 text-center text-gray-400">
          <div class="text-4xl mb-3">📄</div>
          <p>还没有文档，点击"添加文档"开始构建知识库</p>
        </div>

        <div v-else class="divide-y">
          <div
            v-for="doc in store.documents.filter(Boolean)"
            :key="doc.id"
            class="p-4 flex items-center justify-between hover:bg-gray-50"
          >
            <div class="flex-1 min-w-0">
              <div class="font-medium text-gray-900 truncate">
                {{ doc.title }}
              </div>
              <div class="text-sm text-gray-500 mt-1">
                {{ doc.word_count.toLocaleString() }} 字 · {{ formatDate(doc.created_at) }}
                <span v-if="doc.tags && doc.tags.length > 0" class="ml-2">
                  <span
                    v-for="tag in doc.tags"
                    :key="tag"
                    class="inline-block bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded-full mr-1"
                  >
                    {{ tag }}
                  </span>
                </span>
              </div>
            </div>
            <button class="ml-4 text-red-500 hover:text-red-700 text-sm" @click="deleteDoc(doc.id)">
              删除
            </button>
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
