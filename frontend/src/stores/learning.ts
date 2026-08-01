/**
 * Learning records Pinia store
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import learningService from '@/services/learning.service'
import type {
  LearningRecord,
  LearningRecordCreate,
  LearningRecordType,
  LearningStatistics,
} from '@/types/secretary'

export const useLearningStore = defineStore('learning', () => {
  // ============================================================================
  // State
  // ============================================================================

  const records = ref<LearningRecord[]>([])
  const currentRecord = ref<LearningRecord | null>(null)
  const statistics = ref<LearningStatistics | null>(null)

  const loading = ref(false)
  const error = ref<string | null>(null)

  // Pagination
  const totalRecords = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(20)

  // Filters
  const typeFilter = ref<LearningRecordType | null>(null)
  const favoritesOnly = ref(false)
  const searchQuery = ref('')

  // ============================================================================
  // Computed
  // ============================================================================

  const hasRecords = computed(() => records.value.length > 0)

  const favoriteRecords = computed(() => records.value.filter((r) => r.is_favorite))

  const recordsByType = computed(() => {
    const grouped: Record<string, LearningRecord[]> = {}
    for (const record of records.value) {
      if (!grouped[record.input_type]) {
        grouped[record.input_type] = []
      }
      grouped[record.input_type].push(record)
    }
    return grouped
  })

  const totalPages = computed(() => Math.ceil(totalRecords.value / pageSize.value))

  // ============================================================================
  // Actions
  // ============================================================================

  /**
   * Save a learning record (confirm save from chat)
   */
  async function saveLearningRecord(data: LearningRecordCreate) {
    loading.value = true
    error.value = null

    try {
      const record = await learningService.confirmLearning(data)

      // Add to the beginning of the list
      records.value.unshift(record)
      totalRecords.value++

      return record
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to save learning record'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * List learning records with current filters
   */
  async function listRecords(page: number = 1) {
    loading.value = true
    error.value = null
    currentPage.value = page

    try {
      const response = await learningService.listRecords(
        page,
        pageSize.value,
        typeFilter.value,
        favoritesOnly.value
      )

      records.value = response.records
      totalRecords.value = response.total

      return response
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to list records'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Search learning records
   */
  async function searchRecords(query: string, page: number = 1) {
    loading.value = true
    error.value = null
    searchQuery.value = query
    currentPage.value = page

    try {
      const response = await learningService.searchRecords(
        query,
        page,
        pageSize.value,
        typeFilter.value
      )

      records.value = response.records
      totalRecords.value = response.total

      return response
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to search records'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Get a single record
   */
  async function getRecord(recordId: string) {
    loading.value = true
    error.value = null

    try {
      currentRecord.value = await learningService.getRecord(recordId)
      return currentRecord.value
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to get record'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Delete a record
   */
  async function deleteRecord(recordId: string) {
    loading.value = true
    error.value = null

    try {
      await learningService.deleteRecord(recordId)

      // Remove from list
      records.value = records.value.filter((r) => r.id !== recordId)
      totalRecords.value--

      // Clear current if deleted
      if (currentRecord.value?.id === recordId) {
        currentRecord.value = null
      }
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to delete record'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Toggle favorite status
   */
  async function toggleFavorite(recordId: string) {
    try {
      const updated = await learningService.toggleFavorite(recordId)

      // Update in list
      const index = records.value.findIndex((r) => r.id === recordId)
      if (index !== -1) {
        records.value[index] = updated
      }

      // Update current if it's the same
      if (currentRecord.value?.id === recordId) {
        currentRecord.value = updated
      }

      return updated
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to toggle favorite'
      throw err
    }
  }

  /**
   * Mark record as reviewed
   */
  async function markReviewed(recordId: string) {
    try {
      const updated = await learningService.markReviewed(recordId)

      // Update in list
      const index = records.value.findIndex((r) => r.id === recordId)
      if (index !== -1) {
        records.value[index] = updated
      }

      // Update current if it's the same
      if (currentRecord.value?.id === recordId) {
        currentRecord.value = updated
      }

      return updated
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to mark reviewed'
      throw err
    }
  }

  /**
   * Update record tags
   */
  async function updateTags(recordId: string, tags: string[]) {
    try {
      const updated = await learningService.updateRecord(recordId, { tags })

      // Update in list
      const index = records.value.findIndex((r) => r.id === recordId)
      if (index !== -1) {
        records.value[index] = updated
      }

      // Update current if it's the same
      if (currentRecord.value?.id === recordId) {
        currentRecord.value = updated
      }

      return updated
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || 'Failed to update tags'
      throw err
    }
  }

  /**
   * Load statistics
   */
  async function loadStatistics(): Promise<LearningStatistics | null> {
    try {
      statistics.value = await learningService.getStatistics()
      return statistics.value
    } catch (err: any) {
      console.error('Failed to load statistics:', err)
      return null
    }
  }

  /**
   * Set type filter and reload
   */
  async function setTypeFilter(type: LearningRecordType | null) {
    typeFilter.value = type
    await listRecords(1)
  }

  /**
   * Toggle favorites only filter and reload
   */
  async function setFavoritesOnly(value: boolean) {
    favoritesOnly.value = value
    await listRecords(1)
  }

  /**
   * Clear all filters
   */
  async function clearFilters() {
    typeFilter.value = null
    favoritesOnly.value = false
    searchQuery.value = ''
    await listRecords(1)
  }

  /**
   * Clear error
   */
  function clearError(): void {
    error.value = null
  }

  return {
    // State
    records,
    currentRecord,
    statistics,
    loading,
    error,
    totalRecords,
    currentPage,
    pageSize,
    typeFilter,
    favoritesOnly,
    searchQuery,

    // Computed
    hasRecords,
    favoriteRecords,
    recordsByType,
    totalPages,

    // Actions
    saveLearningRecord,
    listRecords,
    searchRecords,
    getRecord,
    deleteRecord,
    toggleFavorite,
    markReviewed,
    updateTags,
    loadStatistics,
    setTypeFilter,
    setFavoritesOnly,
    clearFilters,
    clearError,
  }
})
