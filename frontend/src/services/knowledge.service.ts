/**
 * Knowledge Base API service
 */

import api from './api'
import type {
  KnowledgeDocument,
  DocumentUpload,
  FileUploadResponse,
  KnowledgeQuery,
  KnowledgeQueryResponse,
  KnowledgeStats,
} from '@/types/knowledge'

const BASE_PATH = '/knowledge'

/**
 * Upload a text document to the knowledge base
 */
async function uploadDocument(data: DocumentUpload): Promise<KnowledgeDocument> {
  const response = await api.post<KnowledgeDocument>(`${BASE_PATH}/documents`, data)
  return response.data
}

/**
 * Upload a file (PDF/TXT/MD) to the knowledge base
 */
async function uploadFile(file: File, title?: string): Promise<FileUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  if (title) {
    formData.append('title', title)
  }

  const response = await api.post<FileUploadResponse>(`${BASE_PATH}/documents/file`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 30000, // File upload may take longer
  })
  return response.data
}

/**
 * List all documents for the current user
 */
async function listDocuments(): Promise<KnowledgeDocument[]> {
  const response = await api.get<KnowledgeDocument[]>(`${BASE_PATH}/documents`)
  return response.data
}

/**
 * Delete a document from the knowledge base
 */
async function deleteDocument(docId: string): Promise<void> {
  await api.delete(`${BASE_PATH}/documents/${docId}`)
}

/**
 * Query the knowledge base using semantic search
 */
async function query(data: KnowledgeQuery): Promise<KnowledgeQueryResponse> {
  const response = await api.post<KnowledgeQueryResponse>(`${BASE_PATH}/query`, data)
  return response.data
}

/**
 * Get knowledge base statistics
 */
async function getStats(): Promise<KnowledgeStats> {
  const response = await api.get<KnowledgeStats>(`${BASE_PATH}/stats`)
  return response.data
}

export default {
  uploadDocument,
  uploadFile,
  listDocuments,
  deleteDocument,
  query,
  getStats,
}
