/**
 * Knowledge Base Pinia store
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import knowledgeService from '@/services/knowledge.service'
import type {
  KnowledgeDocument,
  DocumentUpload,
  KnowledgeQueryResult,
  KnowledgeStats,
} from '@/types/knowledge'

export const useKnowledgeStore = defineStore('knowledge', () => {
  // ============================================================================
  // State
  // ============================================================================

  const documents = ref<KnowledgeDocument[]>([])
  const stats = ref<KnowledgeStats | null>(null)
  const queryResults = ref<KnowledgeQueryResult[]>([])
  const lastQuery = ref('')
  /** Message from last query (e.g. when RAG is unavailable). */
  const queryMessage = ref<string | null>(null)

  const loading = ref(false)
  const uploading = ref(false)
  const querying = ref(false)
  const error = ref<string | null>(null)

  // ============================================================================
  // Computed
  // ============================================================================

  const hasDocuments = computed(() => documents.value.length > 0)
  const documentCount = computed(() => documents.value.length)
  const totalWords = computed(() => stats.value?.total_words || 0)
  const hasQueryResults = computed(() => queryResults.value.length > 0)

  // ============================================================================
  // Actions
  // ============================================================================

  /**
   * Load all documents
   */
  async function loadDocuments() {
    loading.value = true
    error.value = null

    try {
      documents.value = await knowledgeService.listDocuments()
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || '加载文档失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Upload a text document
   */
  async function uploadDocument(data: DocumentUpload) {
    uploading.value = true
    error.value = null

    try {
      const doc = await knowledgeService.uploadDocument(data)
      documents.value.unshift(doc)
      return doc
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || '上传文档失败'
      throw err
    } finally {
      uploading.value = false
    }
  }

  /**
   * Upload a file
   * Backend may return either { document } or a flat { id, title, ... }; only unshift when document exists to avoid blank page.
   */
  async function uploadFile(file: File, title?: string) {
    uploading.value = true
    error.value = null

    try {
      const result = await knowledgeService.uploadFile(file, title)
      if (result.document && result.document.id) {
        documents.value.unshift(result.document)
      }
      return result
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || '上传文件失败'
      throw err
    } finally {
      uploading.value = false
    }
  }

  /**
   * Delete a document
   */
  async function deleteDocument(docId: string) {
    loading.value = true
    error.value = null

    try {
      await knowledgeService.deleteDocument(docId)
      documents.value = documents.value.filter((d) => d.id !== docId)
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || '删除文档失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Query the knowledge base
   */
  async function queryKnowledge(queryText: string, topK: number = 5) {
    querying.value = true
    error.value = null
    queryMessage.value = null
    lastQuery.value = queryText

    try {
      const response = await knowledgeService.query({ query: queryText, top_k: topK })
      queryResults.value = response.results ?? []
      queryMessage.value = response.message ?? null
      return response
    } catch (err: any) {
      error.value = err.response?.data?.detail || err.message || '查询失败'
      throw err
    } finally {
      querying.value = false
    }
  }

  /**
   * Load knowledge base statistics
   */
  async function loadStats() {
    try {
      stats.value = await knowledgeService.getStats()
    } catch (err: any) {
      console.error('Failed to load knowledge stats:', err)
    }
  }

  /**
   * Clear query results
   */
  function clearQueryResults() {
    queryResults.value = []
    lastQuery.value = ''
    queryMessage.value = null
  }

  /**
   * Clear error
   */
  function clearError() {
    error.value = null
  }

  return {
    // State
    documents,
    stats,
    queryResults,
    lastQuery,
    queryMessage,
    loading,
    uploading,
    querying,
    error,

    // Computed
    hasDocuments,
    documentCount,
    totalWords,
    hasQueryResults,

    // Actions
    loadDocuments,
    uploadDocument,
    uploadFile,
    deleteDocument,
    queryKnowledge,
    loadStats,
    clearQueryResults,
    clearError,
  }
})
