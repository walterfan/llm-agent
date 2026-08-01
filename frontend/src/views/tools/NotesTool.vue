<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import { useSecretaryStore } from '@/stores/secretary'

const secretaryStore = useSecretaryStore()

const noteContent = ref('')
const noteTitle = ref('')
const searchQuery = ref('')
const result = ref<string | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const activeTab = ref<'save' | 'list' | 'search'>('list')

async function saveNote() {
  if (!noteContent.value.trim()) return

  loading.value = true
  error.value = null
  result.value = null

  try {
    const message = noteTitle.value
      ? `保存笔记，标题是"${noteTitle.value}"，内容是：${noteContent.value}`
      : `保存笔记：${noteContent.value}`

    const response = await secretaryStore.manageNote(message)
    result.value = response
    noteContent.value = ''
    noteTitle.value = ''
  } catch (err: any) {
    error.value = err.message || 'Failed to save note'
  } finally {
    loading.value = false
  }
}

async function listNotes() {
  loading.value = true
  error.value = null
  result.value = null

  try {
    const response = await secretaryStore.manageNote('显示我的笔记列表')
    result.value = response
  } catch (err: any) {
    error.value = err.message || 'Failed to list notes'
  } finally {
    loading.value = false
  }
}

async function searchNotes() {
  if (!searchQuery.value.trim()) return

  loading.value = true
  error.value = null
  result.value = null

  try {
    const response = await secretaryStore.manageNote(`搜索笔记：${searchQuery.value}`)
    result.value = response
  } catch (err: any) {
    error.value = err.message || 'Failed to search notes'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  listNotes()
})
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <AppHeader />

    <div class="max-w-2xl mx-auto px-4 py-8">
      <h1 class="text-2xl font-bold text-gray-800 mb-2">📝 Notes Tool</h1>
      <p class="text-gray-600 mb-6">Save, list, and search your notes.</p>

      <!-- Tabs -->
      <div class="flex gap-2 mb-6">
        <button
          v-for="tab in ['list', 'save', 'search'] as const"
          :key="tab"
          type="button"
          class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="{
            'bg-blue-500 text-white': activeTab === tab,
            'bg-white text-gray-700 hover:bg-gray-100': activeTab !== tab,
          }"
          @click="activeTab = tab"
        >
          {{ tab === 'list' ? '📋 List' : tab === 'save' ? '➕ Save' : '🔍 Search' }}
        </button>
      </div>

      <!-- Save Note -->
      <div v-if="activeTab === 'save'" class="bg-white rounded-lg shadow p-6 mb-6">
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">Title (optional)</label>
          <input
            v-model="noteTitle"
            type="text"
            placeholder="Note title"
            class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">Content</label>
          <textarea
            v-model="noteContent"
            placeholder="Write your note here..."
            rows="4"
            class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button
          type="button"
          :disabled="loading || !noteContent.trim()"
          class="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          @click="saveNote"
        >
          {{ loading ? 'Saving...' : 'Save Note' }}
        </button>
      </div>

      <!-- List Notes -->
      <div v-if="activeTab === 'list'" class="bg-white rounded-lg shadow p-6 mb-6">
        <button
          type="button"
          :disabled="loading"
          class="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          @click="listNotes"
        >
          {{ loading ? 'Loading...' : 'Refresh Notes' }}
        </button>
      </div>

      <!-- Search Notes -->
      <div v-if="activeTab === 'search'" class="bg-white rounded-lg shadow p-6 mb-6">
        <label class="block text-sm font-medium text-gray-700 mb-2">Search Query</label>
        <div class="flex gap-2">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search notes..."
            class="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            @keyup.enter="searchNotes"
          />
          <button
            type="button"
            :disabled="loading || !searchQuery.trim()"
            class="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            @click="searchNotes"
          >
            {{ loading ? 'Searching...' : 'Search' }}
          </button>
        </div>
      </div>

      <!-- Result -->
      <div v-if="result || error" class="bg-white rounded-lg shadow p-6">
        <h3 class="text-sm font-medium text-gray-500 mb-2">Result</h3>
        <div v-if="error" class="text-red-600">
          {{ error }}
        </div>
        <div v-else class="text-gray-800 whitespace-pre-wrap">
          {{ result }}
        </div>
      </div>
    </div>
  </div>
</template>
