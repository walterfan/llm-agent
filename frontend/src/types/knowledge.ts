/**
 * Knowledge base TypeScript interfaces
 */

// ============================================================================
// Document Types
// ============================================================================

export interface KnowledgeDocument {
  id: string
  user_id: number
  title: string
  content: string
  tags: string[]
  source: string | null
  word_count: number
  created_at: string
  updated_at: string
}

export interface DocumentUpload {
  title: string
  content: string
  tags?: string[]
  source?: string
}

export interface FileUploadResponse {
  document: KnowledgeDocument
  message: string
}

// ============================================================================
// Query Types
// ============================================================================

export interface KnowledgeQuery {
  query: string
  top_k?: number
}

export interface KnowledgeQueryResult {
  content: string
  score: number
  metadata: Record<string, any>
}

export interface KnowledgeQueryResponse {
  query: string
  results: KnowledgeQueryResult[]
  total: number
  /** Shown when RAG is unavailable (e.g. semantic search disabled). */
  message?: string
}

// ============================================================================
// Stats Types
// ============================================================================

export interface KnowledgeStats {
  total_documents: number
  total_words: number
  total_chunks: number
  tags: Record<string, number>
}
