/**
 * Learning records API service
 */

import api from './api'
import type {
  LearningRecord,
  LearningRecordCreate,
  LearningRecordUpdate,
  LearningRecordListResponse,
  LearningRecordType,
  LearningStatistics,
} from '@/types/secretary'

const BASE_PATH = '/learning'

/**
 * Save a learning record (confirm save)
 */
async function confirmLearning(data: LearningRecordCreate): Promise<LearningRecord> {
  const response = await api.post<LearningRecord>(`${BASE_PATH}/confirm`, data)
  return response.data
}

/**
 * List learning records
 */
async function listRecords(
  page: number = 1,
  pageSize: number = 20,
  type?: LearningRecordType | null,
  favoritesOnly: boolean = false
): Promise<LearningRecordListResponse> {
  const params: Record<string, any> = {
    page,
    page_size: pageSize,
    favorites_only: favoritesOnly,
  }
  if (type) {
    params.type = type
  }

  const response = await api.get<LearningRecordListResponse>(`${BASE_PATH}/records`, { params })
  return response.data
}

/**
 * Get a single learning record
 */
async function getRecord(recordId: string): Promise<LearningRecord> {
  const response = await api.get<LearningRecord>(`${BASE_PATH}/records/${recordId}`)
  return response.data
}

/**
 * Update a learning record
 */
async function updateRecord(recordId: string, data: LearningRecordUpdate): Promise<LearningRecord> {
  const response = await api.patch<LearningRecord>(`${BASE_PATH}/records/${recordId}`, data)
  return response.data
}

/**
 * Delete a learning record
 */
async function deleteRecord(recordId: string): Promise<void> {
  await api.delete(`${BASE_PATH}/records/${recordId}`)
}

/**
 * Search learning records
 */
async function searchRecords(
  query: string,
  page: number = 1,
  pageSize: number = 20,
  type?: LearningRecordType | null
): Promise<LearningRecordListResponse> {
  const params: Record<string, any> = {
    q: query,
    page,
    page_size: pageSize,
  }
  if (type) {
    params.type = type
  }

  const response = await api.get<LearningRecordListResponse>(`${BASE_PATH}/search`, { params })
  return response.data
}

/**
 * Mark a record as reviewed
 */
async function markReviewed(recordId: string): Promise<LearningRecord> {
  const response = await api.post<LearningRecord>(`${BASE_PATH}/records/${recordId}/review`)
  return response.data
}

/**
 * Toggle favorite status
 */
async function toggleFavorite(recordId: string): Promise<LearningRecord> {
  const response = await api.post<LearningRecord>(`${BASE_PATH}/records/${recordId}/favorite`)
  return response.data
}

/**
 * Get learning statistics
 */
async function getStatistics(): Promise<LearningStatistics> {
  const response = await api.get<LearningStatistics>(`${BASE_PATH}/statistics`)
  return response.data
}

export default {
  confirmLearning,
  listRecords,
  getRecord,
  updateRecord,
  deleteRecord,
  searchRecords,
  markReviewed,
  toggleFavorite,
  getStatistics,
}
