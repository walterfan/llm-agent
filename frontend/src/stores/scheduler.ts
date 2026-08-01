/**
 * Pinia store for Job Scheduler state management.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { schedulerService } from '@/services/scheduler.service'
import type { ScheduledJob, JobType, JobHistoryEntry, AddJobRequest } from '@/types/scheduler'

export const useSchedulerStore = defineStore('scheduler', () => {
  // ========== State ==========
  const jobs = ref<ScheduledJob[]>([])
  const jobTypes = ref<JobType[]>([])
  const history = ref<JobHistoryEntry[]>([])
  const schedulerRunning = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const successMessage = ref<string | null>(null)
  const searchQuery = ref('')

  // ========== Getters ==========
  const filteredJobs = computed(() => {
    if (!searchQuery.value.trim()) return jobs.value
    const q = searchQuery.value.toLowerCase()
    return jobs.value.filter(
      (job) =>
        job.id.toLowerCase().includes(q) ||
        job.name.toLowerCase().includes(q) ||
        job.trigger.toLowerCase().includes(q)
    )
  })

  const jobCount = computed(() => jobs.value.length)

  const recentErrors = computed(() =>
    history.value.filter((h) => h.status === 'error').slice(0, 10)
  )

  // ========== Actions ==========

  function clearMessages() {
    error.value = null
    successMessage.value = null
  }

  function setError(msg: string) {
    error.value = msg
    successMessage.value = null
    // Auto-clear after 5s
    setTimeout(() => {
      if (error.value === msg) error.value = null
    }, 5000)
  }

  function setSuccess(msg: string) {
    successMessage.value = msg
    error.value = null
    setTimeout(() => {
      if (successMessage.value === msg) successMessage.value = null
    }, 3000)
  }

  async function fetchJobs() {
    loading.value = true
    clearMessages()
    try {
      const result = await schedulerService.listJobs()
      jobs.value = result.jobs
      schedulerRunning.value = result.status === 'running'
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch jobs')
    } finally {
      loading.value = false
    }
  }

  async function fetchJobTypes() {
    try {
      jobTypes.value = await schedulerService.listJobTypes()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch job types')
    }
  }

  async function fetchHistory(limit: number = 50) {
    try {
      history.value = await schedulerService.getHistory(limit)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch history')
    }
  }

  async function addJob(request: AddJobRequest) {
    loading.value = true
    clearMessages()
    try {
      await schedulerService.addJob(request)
      setSuccess(`Job "${request.job_id}" created successfully`)
      await fetchJobs()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to add job')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateJob(jobId: string, request: AddJobRequest) {
    loading.value = true
    clearMessages()
    try {
      await schedulerService.updateJob(jobId, request)
      setSuccess(`Job "${jobId}" updated successfully`)
      await fetchJobs()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to update job')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function removeJob(jobId: string) {
    loading.value = true
    clearMessages()
    try {
      await schedulerService.removeJob(jobId)
      setSuccess(`Job "${jobId}" removed`)
      await fetchJobs()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to remove job')
    } finally {
      loading.value = false
    }
  }

  async function triggerJob(jobId: string) {
    clearMessages()
    try {
      await schedulerService.triggerJob(jobId)
      setSuccess(`Job "${jobId}" triggered`)
      // Refresh history after a short delay
      setTimeout(() => fetchHistory(), 2000)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to trigger job')
    }
  }

  async function pauseJob(jobId: string) {
    clearMessages()
    try {
      await schedulerService.pauseJob(jobId)
      setSuccess(`Job "${jobId}" paused`)
      await fetchJobs()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to pause job')
    }
  }

  async function resumeJob(jobId: string) {
    clearMessages()
    try {
      await schedulerService.resumeJob(jobId)
      setSuccess(`Job "${jobId}" resumed`)
      await fetchJobs()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to resume job')
    }
  }

  return {
    // State
    jobs,
    jobTypes,
    history,
    schedulerRunning,
    loading,
    error,
    successMessage,
    searchQuery,
    // Getters
    filteredJobs,
    jobCount,
    recentErrors,
    // Actions
    fetchJobs,
    fetchJobTypes,
    fetchHistory,
    addJob,
    updateJob,
    removeJob,
    triggerJob,
    pauseJob,
    resumeJob,
    clearMessages,
  }
})
