<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMedicalPaperStore } from '@/stores/medicalPaper'
import AppHeader from '@/components/layout/AppHeader.vue'
import type { CreateTaskRequest, PaperType } from '@/types/medicalPaper'

const store = useMedicalPaperStore()

// Tab navigation
type DetailTab = 'overview' | 'literature' | 'statistics' | 'manuscript' | 'compliance'
const activeTab = ref<DetailTab>('overview')

const detailTabs: { key: DetailTab; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'literature', label: 'Literature' },
  { key: 'statistics', label: 'Statistics' },
  { key: 'manuscript', label: 'Manuscript' },
  { key: 'compliance', label: 'Compliance' },
]

// Form state
const showCreateForm = ref(false)
const title = ref('')
const paperType = ref<PaperType>('rct')
const researchQuestion = ref('')

// Pipeline step labels
const stepLabels: Record<string, string> = {
  literature: 'Literature Search',
  stats: 'Statistical Analysis',
  writer: 'Manuscript Writing',
  compliance: 'Compliance Check',
  done: 'Completed',
}

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  running: 'bg-blue-100 text-blue-800',
  revision: 'bg-orange-100 text-orange-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
}

async function handleCreateTask() {
  if (!title.value || !researchQuestion.value) return

  const request: CreateTaskRequest = {
    title: title.value,
    paper_type: paperType.value,
    research_question: researchQuestion.value,
  }

  try {
    await store.createTask(request)
    showCreateForm.value = false
    title.value = ''
    researchQuestion.value = ''
  } catch (err) {
    console.error('Failed to create task:', err)
  }
}

async function handleSelectTask(taskId: string) {
  activeTab.value = 'overview'
  await store.getTask(taskId)
}

onMounted(async () => {
  await Promise.all([store.listTasks(), store.loadTemplates()])
})
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <AppHeader />
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Header -->
      <div class="flex items-center justify-between mb-8">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Medical Paper Assistant</h1>
          <p class="mt-1 text-sm text-gray-500">
            AI-powered medical paper writing with compliance checking
          </p>
        </div>
        <button
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700"
          @click="showCreateForm = !showCreateForm"
        >
          {{ showCreateForm ? 'Cancel' : 'New Paper' }}
        </button>
      </div>

      <!-- Error Banner -->
      <div v-if="store.error" class="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
        <div class="flex">
          <div class="flex-1">
            <p class="text-sm text-red-700">
              {{ store.error }}
            </p>
          </div>
          <button class="text-red-400 hover:text-red-600" @click="store.clearError()">
            &times;
          </button>
        </div>
      </div>

      <!-- Create Task Form -->
      <div v-if="showCreateForm" class="mb-8 bg-white shadow rounded-lg p-6">
        <h2 class="text-lg font-medium mb-4">Create New Paper</h2>
        <form class="space-y-4" @submit.prevent="handleCreateTask">
          <div>
            <label class="block text-sm font-medium text-gray-700">Title</label>
            <input
              v-model="title"
              type="text"
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              placeholder="e.g., Effect of Drug X on Blood Pressure in Hypertensive Patients"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700">Paper Type</label>
            <select
              v-model="paperType"
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            >
              <option
                v-for="template in store.templates"
                :key="template.paper_type"
                :value="template.paper_type"
              >
                {{ template.name }} ({{ template.checklist }})
              </option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700">Research Question</label>
            <textarea
              v-model="researchQuestion"
              rows="3"
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              placeholder="e.g., Does Drug X reduce systolic blood pressure compared to placebo in adults with stage 1 hypertension?"
            />
          </div>

          <div class="flex justify-end">
            <button
              type="submit"
              :disabled="store.loading || !title || !researchQuestion"
              class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
            >
              {{ store.loading ? 'Creating...' : 'Create Task' }}
            </button>
          </div>
        </form>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Task List (left) -->
        <div class="lg:col-span-1">
          <h2 class="text-lg font-medium text-gray-900 mb-4">Your Papers</h2>
          <div v-if="!store.hasTasks" class="text-sm text-gray-500">
            No papers yet. Click "New Paper" to get started.
          </div>
          <div class="space-y-3">
            <div
              v-for="task in store.tasks"
              :key="task.id"
              class="bg-white shadow rounded-lg p-4 cursor-pointer hover:ring-2 hover:ring-indigo-500 transition"
              :class="{ 'ring-2 ring-indigo-500': store.currentTask?.id === task.id }"
              @click="handleSelectTask(task.id)"
            >
              <h3 class="text-sm font-medium text-gray-900 truncate">
                {{ task.title }}
              </h3>
              <div class="mt-2 flex items-center gap-2">
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                  :class="statusColors[task.status] || 'bg-gray-100 text-gray-800'"
                >
                  {{ task.status }}
                </span>
                <span v-if="task.current_step" class="text-xs text-gray-500">
                  {{ stepLabels[task.current_step] || task.current_step }}
                </span>
              </div>
              <p class="mt-1 text-xs text-gray-400">
                {{ task.paper_type.toUpperCase() }} &middot; Rev {{ task.revision_round }}
              </p>
            </div>
          </div>
        </div>

        <!-- Task Detail (right) -->
        <div class="lg:col-span-2">
          <div v-if="!store.currentTask" class="text-center text-gray-400 py-20">
            Select a paper to view details
          </div>

          <div v-else class="bg-white shadow rounded-lg overflow-hidden">
            <!-- Task header -->
            <div class="px-6 pt-6 pb-4">
              <div class="flex items-center justify-between">
                <h2 class="text-lg font-medium">
                  {{ store.currentTask.title }}
                </h2>
                <span
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                  :class="statusColors[store.currentTask.status] || 'bg-gray-100'"
                >
                  {{ store.currentTask.status }}
                </span>
              </div>
            </div>

            <!-- Tab navigation -->
            <div class="border-b border-gray-200 px-6">
              <nav class="-mb-px flex space-x-6" aria-label="Tabs">
                <button
                  v-for="tab in detailTabs"
                  :key="tab.key"
                  :class="[
                    'whitespace-nowrap py-3 px-1 border-b-2 text-sm font-medium transition-colors',
                    activeTab === tab.key
                      ? 'border-indigo-500 text-indigo-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
                  ]"
                  @click="activeTab = tab.key"
                >
                  {{ tab.label }}
                </button>
              </nav>
            </div>

            <!-- Tab content -->
            <div class="p-6">
              <!-- Streaming output (shown on all tabs when active) -->
              <div v-if="store.isStreaming" class="mb-6">
                <div class="flex items-center gap-2 mb-2">
                  <div
                    class="animate-spin h-4 w-4 border-2 border-indigo-500 border-t-transparent rounded-full"
                  />
                  <span class="text-sm text-gray-600">
                    {{ store.currentAgent ? `Running: ${store.currentAgent}` : 'Processing...' }}
                  </span>
                </div>
                <pre
                  class="bg-gray-900 text-green-400 text-xs p-4 rounded-md overflow-auto max-h-64"
                  >{{ store.streamingText }}</pre
                >
              </div>

              <!-- Overview Tab -->
              <div v-if="activeTab === 'overview'">
                <dl class="grid grid-cols-2 gap-4 text-sm mb-6">
                  <div>
                    <dt class="font-medium text-gray-500">Paper Type</dt>
                    <dd>{{ store.currentTask.paper_type.toUpperCase() }}</dd>
                  </div>
                  <div>
                    <dt class="font-medium text-gray-500">Current Step</dt>
                    <dd>{{ stepLabels[store.currentTask.current_step || ''] || 'N/A' }}</dd>
                  </div>
                  <div>
                    <dt class="font-medium text-gray-500">Revision Round</dt>
                    <dd>{{ store.currentTask.revision_round }}</dd>
                  </div>
                  <div>
                    <dt class="font-medium text-gray-500">Created</dt>
                    <dd>{{ store.currentTask.created_at || 'N/A' }}</dd>
                  </div>
                </dl>

                <div>
                  <h3 class="text-sm font-medium text-gray-500 mb-1">Research Question</h3>
                  <p class="text-sm">
                    {{ store.currentTask.research_question }}
                  </p>
                </div>
              </div>

              <!-- Literature Tab -->
              <div v-if="activeTab === 'literature'">
                <div v-if="store.currentTask.references && store.currentTask.references.length > 0">
                  <h3 class="text-sm font-medium text-gray-700 mb-3">
                    References ({{ store.currentTask.references.length }})
                  </h3>
                  <ul class="space-y-2 text-sm text-gray-600">
                    <li
                      v-for="(reference, idx) in store.currentTask.references"
                      :key="idx"
                      class="p-3 bg-gray-50 rounded-md"
                    >
                      <span class="font-medium text-gray-800">[{{ idx + 1 }}]</span>
                      {{ reference.title || reference.pmid || 'Reference' }}
                      <span v-if="reference.authors" class="block text-xs text-gray-400 mt-1">
                        {{ reference.authors }}
                      </span>
                      <span v-if="reference.journal" class="text-xs text-gray-400">
                        {{ reference.journal }}{{ reference.year ? ` (${reference.year})` : '' }}
                      </span>
                    </li>
                  </ul>
                </div>
                <div v-else class="text-center text-gray-400 py-12">
                  No references yet. Literature search results will appear here.
                </div>
              </div>

              <!-- Statistics Tab -->
              <div v-if="activeTab === 'statistics'">
                <div v-if="store.currentTask.stats_report">
                  <h3 class="text-sm font-medium text-gray-700 mb-3">
                    Statistical Analysis Report
                  </h3>
                  <pre
                    class="bg-gray-50 text-sm p-4 rounded-md overflow-auto max-h-96 text-gray-700"
                    >{{ JSON.stringify(store.currentTask.stats_report, null, 2) }}</pre
                  >
                </div>
                <div v-else class="text-center text-gray-400 py-12">
                  No statistics yet. Analysis results will appear here.
                </div>
              </div>

              <!-- Manuscript Tab -->
              <div v-if="activeTab === 'manuscript'">
                <div v-if="store.currentTask.manuscript">
                  <div
                    v-for="(content, section) in store.currentTask.manuscript"
                    :key="section"
                    class="mb-6"
                  >
                    <h3 class="text-sm font-semibold text-gray-800 uppercase tracking-wide mb-2">
                      {{ section }}
                    </h3>
                    <div class="prose prose-sm max-w-none text-gray-700 bg-gray-50 p-4 rounded-md">
                      {{ content }}
                    </div>
                  </div>
                </div>
                <div v-else class="text-center text-gray-400 py-12">
                  No manuscript yet. Written sections will appear here.
                </div>
              </div>

              <!-- Compliance Tab -->
              <div v-if="activeTab === 'compliance'">
                <div v-if="store.currentTask.compliance_report">
                  <h3 class="text-sm font-medium text-gray-700 mb-3">Compliance Report</h3>
                  <div class="grid grid-cols-4 gap-2 text-center text-xs mb-6">
                    <div class="p-3 bg-blue-50 rounded-md">
                      <div class="text-lg font-bold text-blue-600">
                        {{ store.currentTask.compliance_report.total_items || 0 }}
                      </div>
                      <div class="text-gray-500">Total</div>
                    </div>
                    <div class="p-3 bg-green-50 rounded-md">
                      <div class="text-lg font-bold text-green-600">
                        {{ store.currentTask.compliance_report.passed || 0 }}
                      </div>
                      <div class="text-gray-500">Passed</div>
                    </div>
                    <div class="p-3 bg-yellow-50 rounded-md">
                      <div class="text-lg font-bold text-yellow-600">
                        {{ store.currentTask.compliance_report.warnings || 0 }}
                      </div>
                      <div class="text-gray-500">Warnings</div>
                    </div>
                    <div class="p-3 bg-red-50 rounded-md">
                      <div class="text-lg font-bold text-red-600">
                        {{ store.currentTask.compliance_report.failed || 0 }}
                      </div>
                      <div class="text-gray-500">Failed</div>
                    </div>
                  </div>
                  <div v-if="store.currentTask.compliance_report.items" class="space-y-2">
                    <div
                      v-for="(item, idx) in store.currentTask.compliance_report.items"
                      :key="idx"
                      class="flex items-start gap-2 text-sm p-2 rounded-md"
                      :class="{
                        'bg-green-50': item.status === 'passed',
                        'bg-yellow-50': item.status === 'warning',
                        'bg-red-50': item.status === 'failed',
                      }"
                    >
                      <span class="flex-shrink-0 mt-0.5">
                        {{
                          item.status === 'passed'
                            ? '&#10003;'
                            : item.status === 'warning'
                              ? '!'
                              : '&#10007;'
                        }}
                      </span>
                      <span>{{ item.description || item.name || `Item ${idx + 1}` }}</span>
                    </div>
                  </div>
                </div>
                <div v-else class="text-center text-gray-400 py-12">
                  No compliance report yet. Checklist results will appear here.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
