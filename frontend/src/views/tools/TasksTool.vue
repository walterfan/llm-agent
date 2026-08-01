<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import { useSecretaryStore } from '@/stores/secretary'

const secretaryStore = useSecretaryStore()

const taskTitle = ref('')
const taskPriority = ref('medium')
const taskDueDate = ref('')
const result = ref<string | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const activeTab = ref<'list' | 'create'>('list')

const priorities = [
  { value: 'low', label: '🟢 Low' },
  { value: 'medium', label: '🟡 Medium' },
  { value: 'high', label: '🟠 High' },
  { value: 'urgent', label: '🔴 Urgent' },
]

async function createTask() {
  if (!taskTitle.value.trim()) return

  loading.value = true
  error.value = null
  result.value = null

  try {
    let message = `创建任务：${taskTitle.value}，优先级${taskPriority.value}`
    if (taskDueDate.value) {
      message += `，截止日期${taskDueDate.value}`
    }

    const response = await secretaryStore.manageTask(message)
    result.value = response
    taskTitle.value = ''
    taskDueDate.value = ''
  } catch (err: any) {
    error.value = err.message || 'Failed to create task'
  } finally {
    loading.value = false
  }
}

async function listTasks() {
  loading.value = true
  error.value = null
  result.value = null

  try {
    const response = await secretaryStore.manageTask('显示我的任务列表')
    result.value = response
  } catch (err: any) {
    error.value = err.message || 'Failed to list tasks'
  } finally {
    loading.value = false
  }
}

async function listOverdueTasks() {
  loading.value = true
  error.value = null
  result.value = null

  try {
    const response = await secretaryStore.manageTask('显示过期的任务')
    result.value = response
  } catch (err: any) {
    error.value = err.message || 'Failed to get overdue tasks'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  listTasks()
})
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <AppHeader />

    <div class="max-w-2xl mx-auto px-4 py-8">
      <h1 class="text-2xl font-bold text-gray-800 mb-2">✅ Tasks Tool</h1>
      <p class="text-gray-600 mb-6">Create and manage your to-do tasks.</p>

      <!-- Tabs -->
      <div class="flex gap-2 mb-6">
        <button
          v-for="tab in ['list', 'create'] as const"
          :key="tab"
          type="button"
          class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="{
            'bg-blue-500 text-white': activeTab === tab,
            'bg-white text-gray-700 hover:bg-gray-100': activeTab !== tab,
          }"
          @click="activeTab = tab"
        >
          {{ tab === 'list' ? '📋 List Tasks' : '➕ Create Task' }}
        </button>
      </div>

      <!-- Create Task -->
      <div v-if="activeTab === 'create'" class="bg-white rounded-lg shadow p-6 mb-6">
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">Task Title</label>
          <input
            v-model="taskTitle"
            type="text"
            placeholder="What needs to be done?"
            class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div class="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Priority</label>
            <select
              v-model="taskPriority"
              class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option v-for="p in priorities" :key="p.value" :value="p.value">
                {{ p.label }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Due Date (optional)</label>
            <input
              v-model="taskDueDate"
              type="datetime-local"
              class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        <button
          type="button"
          :disabled="loading || !taskTitle.trim()"
          class="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          @click="createTask"
        >
          {{ loading ? 'Creating...' : 'Create Task' }}
        </button>
      </div>

      <!-- List Tasks -->
      <div v-if="activeTab === 'list'" class="bg-white rounded-lg shadow p-6 mb-6">
        <div class="flex gap-2">
          <button
            type="button"
            :disabled="loading"
            class="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            @click="listTasks"
          >
            {{ loading ? 'Loading...' : 'All Tasks' }}
          </button>
          <button
            type="button"
            :disabled="loading"
            class="px-6 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed"
            @click="listOverdueTasks"
          >
            Overdue Tasks
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
