/**
 * Scheduler API service.
 *
 * Communicates with /api/v1/scheduled/* endpoints.
 */

import api from './api'
import type {
  ScheduledJob,
  JobType,
  JobHistoryEntry,
  AddJobRequest,
  SchedulerStatus,
  JobTypesResponse,
  JobHistoryResponse,
} from '@/types/scheduler'

const BASE = '/scheduled'

export const schedulerService = {
  /**
   * List all registered jobs.
   */
  async listJobs(): Promise<SchedulerStatus> {
    const { data } = await api.get(`${BASE}/jobs`)
    return data
  },

  /**
   * List available job types.
   */
  async listJobTypes(): Promise<JobType[]> {
    const { data } = await api.get<JobTypesResponse>(`${BASE}/job-types`)
    return data.job_types
  },

  /**
   * Get job execution history.
   */
  async getHistory(limit: number = 50): Promise<JobHistoryEntry[]> {
    const { data } = await api.get<JobHistoryResponse>(`${BASE}/jobs/history`, {
      params: { limit },
    })
    return data.history
  },

  /**
   * Add a new scheduled job.
   */
  async addJob(request: AddJobRequest): Promise<{ status: string; job: ScheduledJob }> {
    const { data } = await api.post(`${BASE}/jobs`, request)
    return data
  },

  /**
   * Update an existing job.
   */
  async updateJob(
    jobId: string,
    request: AddJobRequest
  ): Promise<{ status: string; job: ScheduledJob }> {
    const { data } = await api.put(`${BASE}/jobs/${jobId}`, request)
    return data
  },

  /**
   * Remove a scheduled job.
   */
  async removeJob(jobId: string): Promise<void> {
    await api.delete(`${BASE}/jobs/${jobId}`)
  },

  /**
   * Immediately trigger a job.
   */
  async triggerJob(jobId: string): Promise<{ status: string; job_id: string }> {
    const { data } = await api.post(`${BASE}/jobs/${jobId}/trigger`)
    return data
  },

  /**
   * Pause a job.
   */
  async pauseJob(jobId: string): Promise<void> {
    await api.post(`${BASE}/jobs/${jobId}/pause`)
  },

  /**
   * Resume a paused job.
   */
  async resumeJob(jobId: string): Promise<void> {
    await api.post(`${BASE}/jobs/${jobId}/resume`)
  },

  /**
   * Health check.
   */
  async healthCheck(): Promise<{
    status: string
    scheduler_running: boolean
    jobs_count: number
  }> {
    const { data } = await api.get(`${BASE}/health`)
    return data
  },
}
