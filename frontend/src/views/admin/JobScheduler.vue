<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import { useSchedulerStore } from '@/stores/scheduler'
import type { AddJobRequest, ScheduledJob } from '@/types/scheduler'

const store = useSchedulerStore()

// ========== Tabs ==========
type TabName = 'jobs' | 'create' | 'history'
const activeTab = ref<TabName>('jobs')

// ========== Create / Edit Form ==========
const editingJobId = ref<string | null>(null)
const isEditing = computed(() => editingJobId.value !== null)

const defaultForm = (): AddJobRequest => ({
  job_id: '',
  job_type: 'check_reminders',
  trigger_type: 'interval',
  name: '',
  description: '',
  seconds: undefined,
  minutes: 5,
  hours: undefined,
  hour: 8,
  minute: 0,
  day_of_week: undefined,
})

const form = ref<AddJobRequest>(defaultForm())

// ========== Delete Confirmation ==========
const deleteConfirmId = ref<string | null>(null)

// ========== Computed ==========
const selectedJobType = computed(() => store.jobTypes.find((jt) => jt.id === form.value.job_type))

const triggerSummary = computed(() => {
  if (form.value.trigger_type === 'interval') {
    const parts: string[] = []
    if (form.value.hours) parts.push(`${form.value.hours}h`)
    if (form.value.minutes) parts.push(`${form.value.minutes}m`)
    if (form.value.seconds) parts.push(`${form.value.seconds}s`)
    return parts.length ? `Every ${parts.join(' ')}` : 'Not configured'
  } else {
    const parts: string[] = []
    if (form.value.hour !== undefined) parts.push(`${String(form.value.hour).padStart(2, '0')}`)
    if (form.value.minute !== undefined)
      parts.push(`:${String(form.value.minute).padStart(2, '0')}`)
    if (form.value.day_of_week) parts.push(` (${form.value.day_of_week})`)
    return parts.length ? `At ${parts.join('')}` : 'Not configured'
  }
})

// ========== Methods ==========

function resetForm() {
  form.value = defaultForm()
  editingJobId.value = null
}

function openCreateTab() {
  resetForm()
  activeTab.value = 'create'
}

function editJob(job: ScheduledJob) {
  editingJobId.value = job.id
  // Parse trigger string to populate form
  form.value = {
    job_id: job.id,
    job_type: guessJobType(job.id),
    trigger_type: job.trigger.includes('cron') ? 'cron' : 'interval',
    name: job.name,
    description: '',
    seconds: undefined,
    minutes: undefined,
    hours: undefined,
    hour: undefined,
    minute: undefined,
    day_of_week: undefined,
  }
  activeTab.value = 'create'
}

function guessJobType(jobId: string): string {
  if (jobId.includes('reminder')) return 'check_reminders'
  if (jobId.includes('task')) return 'check_tasks'
  if (jobId.includes('summary')) return 'daily_summary'
  if (jobId.includes('email')) return 'send_emails'
  return 'check_reminders'
}

async function handleSubmit() {
  // Validate
  if (!form.value.job_id.trim()) return

  try {
    if (isEditing.value) {
      await store.updateJob(editingJobId.value!, form.value)
    } else {
      await store.addJob(form.value)
    }
    resetForm()
    activeTab.value = 'jobs'
  } catch {
    // Error is handled in store
  }
}

async function confirmDelete(jobId: string) {
  deleteConfirmId.value = jobId
}

async function executeDelete() {
  if (deleteConfirmId.value) {
    await store.removeJob(deleteConfirmId.value)
    deleteConfirmId.value = null
  }
}

function cancelDelete() {
  deleteConfirmId.value = null
}

function applyDefaults() {
  const jt = selectedJobType.value
  if (!jt) return
  form.value.trigger_type = jt.default_trigger
  if (jt.default_interval) {
    form.value.minutes = jt.default_interval.minutes
    form.value.hours = jt.default_interval.hours
    form.value.seconds = jt.default_interval.seconds
  }
  if (jt.default_cron) {
    form.value.hour = jt.default_cron.hour
    form.value.minute = jt.default_cron.minute
  }
}

function formatTime(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return iso
  }
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case 'success':
      return 'bg-green-100 text-green-800'
    case 'error':
      return 'bg-red-100 text-red-800'
    case 'missed':
      return 'bg-yellow-100 text-yellow-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

function agentBadgeClass(agent: string): string {
  switch (agent) {
    case 'secretary':
      return 'bg-blue-100 text-blue-800'
    case 'recommendation':
      return 'bg-purple-100 text-purple-800'
    case 'coach':
      return 'bg-green-100 text-green-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

// ========== Lifecycle ==========
onMounted(async () => {
  await Promise.all([store.fetchJobs(), store.fetchJobTypes(), store.fetchHistory()])
})
</script>

<template>
  <AppLayout>
    <div class="max-w-6xl mx-auto">
      <!-- Header -->
      <div class="mb-6 flex items-center justify-between">
        <div>
          <h1 class="text-3xl font-bold text-gray-900">⏰ Job Scheduler</h1>
          <p class="mt-1 text-gray-600">Manage scheduled jobs that trigger AI agents</p>
        </div>
        <div class="flex items-center gap-3">
          <!-- Scheduler Status Badge -->
          <span
            :class="[
              'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium',
              store.schedulerRunning ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800',
            ]"
          >
            <span
              :class="[
                'w-2 h-2 rounded-full',
                store.schedulerRunning ? 'bg-green-500 animate-pulse' : 'bg-red-500',
              ]"
            />
            {{ store.schedulerRunning ? 'Running' : 'Stopped' }}
            <span class="text-xs opacity-70">({{ store.jobCount }} jobs)</span>
          </span>
          <!-- Refresh Button -->
          <button
            :disabled="store.loading"
            class="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            title="Refresh"
            @click="store.fetchJobs(); store.fetchHistory()"
          >
            <svg
              class="w-5 h-5"
              :class="{ 'animate-spin': store.loading }"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        </div>
      </div>

      <!-- Alert Messages -->
      <Transition name="fade">
        <div
          v-if="store.error"
          class="mb-4 bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-2"
        >
          <span class="text-red-500">❌</span>
          <span class="text-red-800 text-sm">{{ store.error }}</span>
        </div>
      </Transition>
      <Transition name="fade">
        <div
          v-if="store.successMessage"
          class="mb-4 bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-2"
        >
          <span class="text-green-500">✅</span>
          <span class="text-green-800 text-sm">{{ store.successMessage }}</span>
        </div>
      </Transition>

      <!-- Tabs -->
      <div class="flex gap-1 mb-6 bg-gray-100 p-1 rounded-lg w-fit">
        <button
          v-for="tab in ['jobs', 'create', 'history'] as const"
          :key="tab"
          :class="[
            'px-4 py-2 rounded-md text-sm font-medium transition-all',
            activeTab === tab
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900',
          ]"
          @click="tab === 'create' ? openCreateTab() : (activeTab = tab)"
        >
          {{ tab === 'jobs' ? '📋 Jobs' : tab === 'create' ? '➕ Create' : '📜 History' }}
        </button>
      </div>

      <!-- ============================================================ -->
      <!-- Tab: Jobs List -->
      <!-- ============================================================ -->
      <div v-if="activeTab === 'jobs'">
        <!-- Search Bar -->
        <div class="mb-4">
          <div class="relative">
            <svg
              class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <input
              v-model="store.searchQuery"
              type="text"
              placeholder="Search jobs by ID, name, or trigger..."
              class="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
          </div>
        </div>

        <!-- Jobs Table -->
        <div class="bg-white rounded-lg shadow overflow-hidden">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th
                  class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Job
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Trigger
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Next Run
                </th>
                <th
                  class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Status
                </th>
                <th
                  class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Actions
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr
                v-for="job in store.filteredJobs"
                :key="job.id"
                class="hover:bg-gray-50 transition-colors"
              >
                <td class="px-4 py-3">
                  <div class="text-sm font-medium text-gray-900">
                    {{ job.name }}
                  </div>
                  <div class="text-xs text-gray-500 font-mono">
                    {{ job.id }}
                  </div>
                </td>
                <td class="px-4 py-3">
                  <code class="text-xs bg-gray-100 px-2 py-1 rounded text-gray-700">{{
                    job.trigger
                  }}</code>
                </td>
                <td class="px-4 py-3 text-sm text-gray-600">
                  {{ formatTime(job.next_run_time) }}
                </td>
                <td class="px-4 py-3">
                  <span
                    :class="[
                      'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                      job.next_run_time
                        ? 'bg-green-100 text-green-800'
                        : 'bg-yellow-100 text-yellow-800',
                    ]"
                  >
                    {{ job.next_run_time ? 'Active' : 'Paused' }}
                  </span>
                </td>
                <td class="px-4 py-3 text-right">
                  <div class="flex items-center justify-end gap-1">
                    <!-- Trigger Now -->
                    <button
                      class="p-1.5 text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
                      title="Run Now"
                      @click="store.triggerJob(job.id)"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                        />
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                    </button>
                    <!-- Pause / Resume -->
                    <button
                      v-if="job.next_run_time"
                      class="p-1.5 text-yellow-600 hover:bg-yellow-50 rounded-md transition-colors"
                      title="Pause"
                      @click="store.pauseJob(job.id)"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                    </button>
                    <button
                      v-else
                      class="p-1.5 text-green-600 hover:bg-green-50 rounded-md transition-colors"
                      title="Resume"
                      @click="store.resumeJob(job.id)"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                        />
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                    </button>
                    <!-- Edit -->
                    <button
                      class="p-1.5 text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
                      title="Edit"
                      @click="editJob(job)"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                        />
                      </svg>
                    </button>
                    <!-- Delete -->
                    <button
                      class="p-1.5 text-red-600 hover:bg-red-50 rounded-md transition-colors"
                      title="Delete"
                      @click="confirmDelete(job.id)"
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
                </td>
              </tr>
              <!-- Empty State -->
              <tr v-if="store.filteredJobs.length === 0">
                <td colspan="5" class="px-4 py-12 text-center text-gray-500">
                  <div class="text-4xl mb-2">📭</div>
                  <div v-if="store.searchQuery">No jobs matching "{{ store.searchQuery }}"</div>
                  <div v-else>No scheduled jobs. Click "Create" to add one.</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ============================================================ -->
      <!-- Tab: Create / Edit Job -->
      <!-- ============================================================ -->
      <div v-if="activeTab === 'create'">
        <div class="bg-white rounded-lg shadow p-6">
          <h2 class="text-xl font-semibold text-gray-900 mb-6">
            {{ isEditing ? `Edit Job: ${editingJobId}` : 'Create New Job' }}
          </h2>

          <form class="space-y-6" @submit.prevent="handleSubmit">
            <!-- Row 1: Job ID + Name -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Job ID *</label>
                <input
                  v-model="form.job_id"
                  type="text"
                  :disabled="isEditing"
                  placeholder="e.g., morning_reminder_check"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
                />
                <p class="mt-1 text-xs text-gray-500">
                  Unique identifier, lowercase with underscores
                </p>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Display Name</label>
                <input
                  v-model="form.name"
                  type="text"
                  placeholder="e.g., Morning Reminder Check"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <!-- Row 2: Job Type (Agent) -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Job Type (Agent) *</label>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <label
                  v-for="jt in store.jobTypes"
                  :key="jt.id"
                  :class="[
                    'relative flex items-start p-3 border rounded-lg cursor-pointer transition-all',
                    form.job_type === jt.id
                      ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                      : 'border-gray-200 hover:border-gray-300',
                  ]"
                >
                  <input
                    v-model="form.job_type"
                    type="radio"
                    :value="jt.id"
                    class="mt-0.5 mr-3"
                    @change="applyDefaults"
                  />
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="text-sm font-medium text-gray-900">{{ jt.id }}</span>
                      <span
                        :class="['text-xs px-1.5 py-0.5 rounded-full', agentBadgeClass(jt.agent)]"
                      >
                        {{ jt.agent }}
                      </span>
                    </div>
                    <p class="text-xs text-gray-500 mt-0.5">{{ jt.description }}</p>
                  </div>
                </label>
              </div>
            </div>

            <!-- Row 3: Trigger Type -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Trigger Type *</label>
              <div class="flex gap-4">
                <label class="flex items-center gap-2 cursor-pointer">
                  <input
                    v-model="form.trigger_type"
                    type="radio"
                    value="interval"
                    class="text-blue-600"
                  />
                  <span class="text-sm">⏱️ Interval (every N minutes/hours)</span>
                </label>
                <label class="flex items-center gap-2 cursor-pointer">
                  <input
                    v-model="form.trigger_type"
                    type="radio"
                    value="cron"
                    class="text-blue-600"
                  />
                  <span class="text-sm">🕐 Cron (at specific time)</span>
                </label>
              </div>
            </div>

            <!-- Row 4: Trigger Config — Interval -->
            <div v-if="form.trigger_type === 'interval'" class="bg-gray-50 rounded-lg p-4">
              <h3 class="text-sm font-medium text-gray-700 mb-3">Interval Configuration</h3>
              <div class="grid grid-cols-3 gap-4">
                <div>
                  <label class="block text-xs text-gray-500 mb-1">Hours</label>
                  <input
                    v-model.number="form.hours"
                    type="number"
                    min="0"
                    max="24"
                    placeholder="0"
                    class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label class="block text-xs text-gray-500 mb-1">Minutes</label>
                  <input
                    v-model.number="form.minutes"
                    type="number"
                    min="0"
                    max="59"
                    placeholder="5"
                    class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label class="block text-xs text-gray-500 mb-1">Seconds</label>
                  <input
                    v-model.number="form.seconds"
                    type="number"
                    min="0"
                    max="59"
                    placeholder="0"
                    class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            <!-- Row 4: Trigger Config — Cron -->
            <div v-if="form.trigger_type === 'cron'" class="bg-gray-50 rounded-lg p-4">
              <h3 class="text-sm font-medium text-gray-700 mb-3">Cron Configuration</h3>
              <div class="grid grid-cols-3 gap-4">
                <div>
                  <label class="block text-xs text-gray-500 mb-1">Hour (0-23)</label>
                  <input
                    v-model.number="form.hour"
                    type="number"
                    min="0"
                    max="23"
                    placeholder="8"
                    class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label class="block text-xs text-gray-500 mb-1">Minute (0-59)</label>
                  <input
                    v-model.number="form.minute"
                    type="number"
                    min="0"
                    max="59"
                    placeholder="0"
                    class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label class="block text-xs text-gray-500 mb-1">Day of Week</label>
                  <select
                    v-model="form.day_of_week"
                    class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option :value="undefined">Every day</option>
                    <option value="mon-fri">Mon–Fri</option>
                    <option value="sat,sun">Sat–Sun</option>
                    <option value="mon">Monday</option>
                    <option value="tue">Tuesday</option>
                    <option value="wed">Wednesday</option>
                    <option value="thu">Thursday</option>
                    <option value="fri">Friday</option>
                    <option value="sat">Saturday</option>
                    <option value="sun">Sunday</option>
                  </select>
                </div>
              </div>
            </div>

            <!-- Preview -->
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div class="text-sm text-blue-800">
                <strong>Preview:</strong>
                Job <code class="bg-blue-100 px-1 rounded">{{ form.job_id || '...' }}</code> will
                run <strong>{{ triggerSummary }}</strong> executing
                <code class="bg-blue-100 px-1 rounded">{{ form.job_type }}</code>
                <span v-if="selectedJobType"> ({{ selectedJobType.agent }} agent) </span>
              </div>
            </div>

            <!-- Buttons -->
            <div class="flex items-center gap-3 pt-2">
              <button
                type="submit"
                :disabled="store.loading || !form.job_id.trim()"
                class="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition-colors"
              >
                {{ store.loading ? 'Saving...' : isEditing ? 'Update Job' : 'Create Job' }}
              </button>
              <button
                type="button"
                class="px-6 py-2.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm font-medium transition-colors"
                @click="activeTab = 'jobs'; resetForm()"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- ============================================================ -->
      <!-- Tab: Execution History -->
      <!-- ============================================================ -->
      <div v-if="activeTab === 'history'">
        <div class="bg-white rounded-lg shadow overflow-hidden">
          <div class="px-4 py-3 bg-gray-50 border-b flex items-center justify-between">
            <h3 class="text-sm font-medium text-gray-700">Recent Executions</h3>
            <button class="text-xs text-blue-600 hover:text-blue-800" @click="store.fetchHistory()">
              Refresh
            </button>
          </div>

          <div v-if="store.history.length === 0" class="px-4 py-12 text-center text-gray-500">
            <div class="text-4xl mb-2">📭</div>
            <div>No execution history yet. Jobs will appear here after they run.</div>
          </div>

          <table v-else class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Job ID
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Executed At
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Details
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              <tr
                v-for="(entry, idx) in store.history.slice().reverse()"
                :key="idx"
                class="hover:bg-gray-50"
              >
                <td class="px-4 py-3 text-sm font-mono text-gray-900">
                  {{ entry.job_id }}
                </td>
                <td class="px-4 py-3">
                  <span
                    :class="[
                      'inline-flex px-2 py-0.5 rounded-full text-xs font-medium',
                      statusBadgeClass(entry.status),
                    ]"
                  >
                    {{ entry.status === 'success' ? '✅' : entry.status === 'error' ? '❌' : '⚠️' }}
                    {{ entry.status }}
                  </span>
                </td>
                <td class="px-4 py-3 text-sm text-gray-600">
                  {{ formatTime(entry.executed_at) }}
                </td>
                <td class="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">
                  {{ entry.error || entry.retval || '—' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ============================================================ -->
      <!-- Delete Confirmation Modal -->
      <!-- ============================================================ -->
      <Transition name="fade">
        <div
          v-if="deleteConfirmId"
          class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          @click.self="cancelDelete"
        >
          <div class="bg-white rounded-lg shadow-xl p-6 max-w-sm mx-4">
            <h3 class="text-lg font-semibold text-gray-900 mb-2">Delete Job</h3>
            <p class="text-sm text-gray-600 mb-4">
              Are you sure you want to delete
              <code class="bg-gray-100 px-1 rounded">{{ deleteConfirmId }}</code
              >? This action cannot be undone.
            </p>
            <div class="flex justify-end gap-3">
              <button
                class="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                @click="cancelDelete"
              >
                Cancel
              </button>
              <button
                class="px-4 py-2 text-sm text-white bg-red-600 rounded-lg hover:bg-red-700"
                @click="executeDelete"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      </Transition>
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
