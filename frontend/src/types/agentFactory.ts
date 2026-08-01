/**
 * AI Agent Factory (孵化器) types — mirror of backend AgentSpec + factory schemas.
 * Backend: app/services/agent_factory/spec.py + app/schemas/agent_factory.py
 */

export type SpecStatus = 'draft' | 'approved' | 'published'
export type ToolRisk = 'low' | 'high'

export interface RoleSpec {
  name: string
  description: string
  boundaries: string[]
}

export interface BrainSpec {
  model: string
  strategy: 'react'
  max_iterations: number
}

export interface MemorySpec {
  short_term: boolean
  long_term: boolean
  rag_collection: string | null
}

export interface ToolBinding {
  name: string
  enabled: boolean
  config: Record<string, unknown>
}

export interface PromptSpec {
  system: string
  user_template: string
}

export interface AcceptanceCase {
  given: string
  when: string
  then: string
}

export type WorkflowNodeType = 'start' | 'think' | 'tool' | 'decision' | 'end'

export interface WorkflowNode {
  id: string
  type: WorkflowNodeType
  label: string
  tool_name?: string | null
  condition?: string | null
}

export interface WorkflowEdge {
  from_node: string
  to_node: string
  condition?: string | null
  label: string
}

export interface WorkflowSpec {
  enabled: boolean
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
}

/** The eight-slot blueprint compiled from one sentence. */
export interface AgentSpec {
  id: string
  version: number
  status: SpecStatus
  one_liner: string // 0
  role: RoleSpec // 1
  brain: BrainSpec // 2
  memory: MemorySpec // 3
  tools: ToolBinding[] // 4
  policies: string[] // 5
  prompts: PromptSpec // 6
  acceptance: AcceptanceCase[] // 7
  workflow: WorkflowSpec // 8 (optional)
  compiler_notes: string
  created_at?: string
  updated_at?: string
  created_by?: number | null
}

export interface SpecSummary {
  id: string
  name: string
  version: number
  status: SpecStatus
  one_liner: string
}

export interface SpecResponse {
  id: string
  name: string
  version: number
  status: SpecStatus
  spec: AgentSpec
}

export interface ToolCapability {
  name: string
  description: string
  input_schema: Record<string, unknown>
  verbs: string[]
  risk: ToolRisk
}

export interface RunStep {
  thought?: string | null
  action?: string | null
  observation?: string | null
}

export interface RunResponse {
  spec_id: string
  final: string
  trace: RunStep[]
}
