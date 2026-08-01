/**
 * AI Agent Factory Service
 * Handles API calls to /api/v1/factory endpoints
 */

import api from './api'
import type {
  AgentSpec,
  SpecSummary,
  SpecResponse,
  ToolCapability,
  RunResponse,
  SpecStatus,
} from '@/types/agentFactory'

export const agentFactoryService = {
  /**
   * Compile one-liner into AgentSpec draft
   */
  async compile(oneLiner: string): Promise<SpecResponse> {
    const response = await api.post('/factory/compile', { one_liner: oneLiner })
    return response.data
  },

  /**
   * List all specs, optionally filtered by status
   */
  async listSpecs(status?: SpecStatus): Promise<SpecSummary[]> {
    const params = status ? { status } : {}
    const response = await api.get('/factory/specs', { params })
    return response.data
  },

  /**
   * Get spec details by ID
   */
  async getSpec(id: string): Promise<SpecResponse> {
    const response = await api.get(`/factory/specs/${id}`)
    return response.data
  },

  /**
   * Update draft spec (PATCH)
   */
  async updateSpec(id: string, spec: Partial<AgentSpec>): Promise<SpecResponse> {
    const response = await api.patch(`/factory/specs/${id}`, { spec })
    return response.data
  },

  /**
   * Approve spec (admin only)
   */
  async approveSpec(id: string): Promise<SpecResponse> {
    const response = await api.post(`/factory/specs/${id}/approve`)
    return response.data
  },

  /**
   * Publish spec (admin only)
   */
  async publishSpec(id: string): Promise<SpecResponse> {
    const response = await api.post(`/factory/specs/${id}/publish`)
    return response.data
  },

  /**
   * Run agent with input
   */
  async runAgent(specId: string, input: string): Promise<RunResponse> {
    const response = await api.post(`/factory/agents/${specId}/run`, { input })
    return response.data
  },

  /**
   * List available tool capabilities
   */
  async listTools(): Promise<ToolCapability[]> {
    const response = await api.get('/factory/tools')
    return response.data
  },

  /**
   * Delete a spec (owner or admin only)
   */
  async deleteSpec(id: string): Promise<void> {
    await api.delete(`/factory/specs/${id}`)
  },

  /**
   * Memory API
   */

  /**
   * Get recent memories for an agent
   */
  async getMemories(
    agentId: string,
    limit: number = 10
  ): Promise<{ memories: any[]; total: number }> {
    const response = await api.get(`/memory/agents/${agentId}/memories`, { params: { limit } })
    return response.data
  },

  /**
   * Search memories for an agent
   */
  async searchMemories(
    agentId: string,
    query: string,
    limit: number = 5
  ): Promise<{ memories: any[]; total: number }> {
    const response = await api.post(`/memory/agents/${agentId}/memories/search`, { query, limit })
    return response.data
  },

  /**
   * Count total memories for an agent
   */
  async countMemories(agentId: string): Promise<{ agent_id: string; count: number }> {
    const response = await api.get(`/memory/agents/${agentId}/memories/count`)
    return response.data
  },

  /**
   * Clear all memories for an agent
   */
  async clearMemories(agentId: string): Promise<void> {
    await api.delete(`/memory/agents/${agentId}/memories`)
  },
}
