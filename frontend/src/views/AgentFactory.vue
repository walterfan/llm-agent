<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import { useAgentFactoryStore } from '@/stores/agentFactory'
import { useAuthStore } from '@/stores/auth'
import type { SpecStatus } from '@/types/agentFactory'

const factoryStore = useAgentFactoryStore()
const authStore = useAuthStore()

const oneLiner = ref('')
const selectedStatus = ref<SpecStatus | 'all'>('all')
const runInput = ref('')
const editMode = ref(false)

// Memory
const memorySearchQuery = ref('')
const memories = ref<any[]>([])
const memoryTotal = ref(0)
const memoryLoading = ref(false)

// Computed
const filteredSpecs = computed(() => {
  if (selectedStatus.value === 'all') return factoryStore.specs
  return factoryStore.specs.filter((s) => s.status === selectedStatus.value)
})

const canApprove = computed(() => {
  return authStore.isAdmin && factoryStore.currentSpec?.status === 'draft'
})

const canPublish = computed(() => {
  return authStore.isAdmin && factoryStore.currentSpec?.status === 'approved'
})

const canRun = computed(() => {
  const status = factoryStore.currentSpec?.status
  return status === 'approved' || status === 'published'
})

const canEdit = computed(() => {
  return factoryStore.currentSpec?.status === 'draft'
})

// Editable fields
const editablePolicies = ref<string[]>([])
const editableTools = ref<any[]>([])

// Methods
async function handleCompile() {
  if (!oneLiner.value.trim()) return
  try {
    await factoryStore.compile(oneLiner.value)
    oneLiner.value = ''
  } catch (error) {
    console.error('Compile failed:', error)
  }
}

async function handleSelectSpec(id: string) {
  try {
    await factoryStore.loadSpec(id)
    editMode.value = false
    factoryStore.clearRunResult()
    // Initialize editable fields
    if (factoryStore.currentSpec) {
      editablePolicies.value = [...factoryStore.currentSpec.spec.policies]
      editableTools.value = JSON.parse(JSON.stringify(factoryStore.currentSpec.spec.tools))
      // Load memories if long-term memory is enabled
      if (factoryStore.currentSpec.spec.memory.long_term) {
        await loadRecentMemories()
      }
    }
  } catch (error) {
    console.error('Load spec failed:', error)
  }
}

function enterEditMode() {
  if (!factoryStore.currentSpec) return
  editMode.value = true
  editablePolicies.value = [...factoryStore.currentSpec.spec.policies]
  editableTools.value = JSON.parse(JSON.stringify(factoryStore.currentSpec.spec.tools))
}

function cancelEdit() {
  editMode.value = false
}

async function saveEdit() {
  if (!factoryStore.currentSpec) return
  try {
    const updates = {
      ...factoryStore.currentSpec.spec,
      policies: editablePolicies.value.filter((p) => p.trim()),
      tools: editableTools.value,
    }
    await factoryStore.updateSpec(factoryStore.currentSpec.id, updates)
    editMode.value = false
    alert('Spec updated successfully!')
  } catch (error) {
    console.error('Save failed:', error)
  }
}

function addPolicy() {
  editablePolicies.value.push('')
}

function removePolicy(index: number) {
  editablePolicies.value.splice(index, 1)
}

function toggleTool(index: number) {
  editableTools.value[index].enabled = !editableTools.value[index].enabled
}

async function handleApprove() {
  if (!factoryStore.currentSpec) return
  try {
    await factoryStore.approveSpec(factoryStore.currentSpec.id)
    alert('Spec approved successfully!')
  } catch (error) {
    console.error('Approve failed:', error)
  }
}

async function handlePublish() {
  if (!factoryStore.currentSpec) return
  try {
    await factoryStore.publishSpec(factoryStore.currentSpec.id)
    alert('Spec published successfully!')
  } catch (error) {
    console.error('Publish failed:', error)
  }
}

async function handleRun() {
  if (!factoryStore.currentSpec || !runInput.value.trim()) return
  try {
    await factoryStore.runAgent(factoryStore.currentSpec.id, runInput.value)
    // Reload memories if long-term memory is enabled
    if (factoryStore.currentSpec.spec.memory.long_term) {
      await loadRecentMemories()
    }
  } catch (error) {
    console.error('Run failed:', error)
  }
}

async function handleDelete(id: string, name: string) {
  if (!confirm(`Are you sure you want to delete "${name}"? This action cannot be undone.`)) {
    return
  }
  try {
    await factoryStore.deleteSpec(id)
  } catch (error) {
    console.error('Delete failed:', error)
  }
}

function getStatusBadgeClass(status: SpecStatus) {
  const classes = {
    draft: 'bg-gray-100 text-gray-800',
    approved: 'bg-green-100 text-green-800',
    published: 'bg-blue-100 text-blue-800',
  }
  return classes[status]
}

// Memory functions
async function loadRecentMemories() {
  if (!factoryStore.currentSpec) return

  memoryLoading.value = true
  try {
    const result = await factoryStore.getMemories(factoryStore.currentSpec.id, 10)
    memories.value = result.memories
    memoryTotal.value = result.total
  } catch (error) {
    console.error('Failed to load memories:', error)
  } finally {
    memoryLoading.value = false
  }
}

async function searchMemories() {
  if (!factoryStore.currentSpec || !memorySearchQuery.value.trim()) {
    await loadRecentMemories()
    return
  }

  memoryLoading.value = true
  try {
    const result = await factoryStore.searchMemories(
      factoryStore.currentSpec.id,
      memorySearchQuery.value,
      10
    )
    memories.value = result.memories
  } catch (error) {
    console.error('Failed to search memories:', error)
  } finally {
    memoryLoading.value = false
  }
}

async function clearAllMemories() {
  if (!factoryStore.currentSpec) return

  if (!confirm(`Clear all ${memoryTotal.value} memories for ${factoryStore.currentSpec.name}?`)) {
    return
  }

  try {
    await factoryStore.clearMemories(factoryStore.currentSpec.id)
    memories.value = []
    memoryTotal.value = 0
  } catch (error) {
    console.error('Failed to clear memories:', error)
  }
}

onMounted(async () => {
  await factoryStore.loadSpecs()
  await factoryStore.loadTools()
})
</script>

<template>
  <AppLayout>
    <div>
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900">🏭 AI Agent Factory</h1>
        <p class="mt-2 text-gray-600">Compile one sentence into a runnable agent</p>
      </div>

      <!-- Error Display -->
      <div v-if="factoryStore.error" class="mb-4 rounded-md bg-red-50 p-4">
        <div class="flex">
          <div class="flex-shrink-0">
            <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path
                fill-rule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clip-rule="evenodd"
              />
            </svg>
          </div>
          <div class="ml-3">
            <p class="text-sm text-red-800">
              {{ factoryStore.error }}
            </p>
          </div>
          <button class="ml-auto text-red-500 hover:text-red-700" @click="factoryStore.clearError">
            ✕
          </button>
        </div>
      </div>

      <!-- Main Layout: Two Columns -->
      <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <!-- Left Column: Spec List + Compile -->
        <div class="lg:col-span-1">
          <!-- Compile Section -->
          <div class="mb-6 rounded-lg bg-white p-6 shadow">
            <h2 class="mb-4 text-lg font-semibold">✨ Compile Agent</h2>
            <textarea
              v-model="oneLiner"
              placeholder="帮我做一个日程安排专家：查天气、翻待办、排日程、设提醒"
              class="w-full rounded-md border border-gray-300 p-3 text-sm"
              rows="3"
            />
            <button
              :disabled="!oneLiner.trim() || factoryStore.loading"
              class="mt-3 w-full rounded-md bg-primary-600 px-4 py-2 text-white hover:bg-primary-700 disabled:bg-gray-300"
              @click="handleCompile"
            >
              {{ factoryStore.loading ? 'Compiling...' : '🔨 Compile' }}
            </button>
          </div>

          <!-- Spec List -->
          <div class="rounded-lg bg-white p-6 shadow">
            <div class="mb-4 flex items-center justify-between">
              <h2 class="text-lg font-semibold">Agent Specs</h2>
              <select
                v-model="selectedStatus"
                class="rounded-md border border-gray-300 px-2 py-1 text-sm"
              >
                <option value="all">All</option>
                <option value="draft">Draft</option>
                <option value="approved">Approved</option>
                <option value="published">Published</option>
              </select>
            </div>
            <div class="space-y-2">
              <div
                v-for="spec in filteredSpecs"
                :key="spec.id"
                :class="[
                  'relative rounded-md border p-3 group',
                  factoryStore.currentSpec?.id === spec.id
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-200',
                ]"
              >
                <button
                  class="w-full text-left hover:bg-gray-50 rounded"
                  @click="handleSelectSpec(spec.id)"
                >
                  <div class="flex items-center justify-between">
                    <span class="text-sm font-medium">{{ spec.name }}</span>
                    <span :class="['rounded px-2 py-1 text-xs', getStatusBadgeClass(spec.status)]">
                      {{ spec.status }}
                    </span>
                  </div>
                  <p class="mt-1 text-xs text-gray-600">
                    {{ spec.one_liner }}
                  </p>
                </button>
                <button
                  class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-red-100 rounded text-red-600 hover:text-red-800"
                  title="Delete spec"
                  @click.stop="handleDelete(spec.id, spec.name)"
                >
                  🗑️
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Column: Spec Details -->
        <div v-if="factoryStore.currentSpec" class="lg:col-span-2">
          <div class="rounded-lg bg-white p-6 shadow">
            <div class="mb-6 flex items-center justify-between">
              <h2 class="text-xl font-bold">
                {{ factoryStore.currentSpec.name }}
              </h2>
              <div class="flex gap-2">
                <!-- Edit Mode Buttons -->
                <template v-if="editMode">
                  <button
                    class="rounded-md bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700"
                    @click="saveEdit"
                  >
                    💾 Save
                  </button>
                  <button
                    class="rounded-md bg-gray-600 px-4 py-2 text-sm text-white hover:bg-gray-700"
                    @click="cancelEdit"
                  >
                    ❌ Cancel
                  </button>
                </template>
                <!-- Normal Mode Buttons -->
                <template v-else>
                  <button
                    v-if="canEdit"
                    class="rounded-md bg-yellow-600 px-4 py-2 text-sm text-white hover:bg-yellow-700"
                    @click="enterEditMode"
                  >
                    ✏️ Edit
                  </button>
                  <button
                    v-if="canApprove"
                    class="rounded-md bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700"
                    @click="handleApprove"
                  >
                    ✅ Approve
                  </button>
                  <button
                    v-if="canPublish"
                    class="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
                    @click="handlePublish"
                  >
                    📢 Publish
                  </button>
                </template>
              </div>
            </div>

            <!-- Spec Sections -->
            <div class="space-y-6">
              <!-- Role & Boundaries -->
              <div>
                <h3 class="mb-2 font-semibold text-gray-900">1️⃣ Role & Boundaries</h3>
                <div class="rounded-md bg-gray-50 p-4">
                  <p class="text-sm">
                    <strong>Name:</strong> {{ factoryStore.currentSpec.spec.role.name }}
                  </p>
                  <p class="mt-2 text-sm">
                    <strong>Description:</strong>
                    {{ factoryStore.currentSpec.spec.role.description }}
                  </p>
                  <p class="mt-2 text-sm">
                    <strong>Boundaries:</strong>
                  </p>
                  <ul class="ml-4 mt-1 list-disc text-sm">
                    <li v-for="(b, i) in factoryStore.currentSpec.spec.role.boundaries" :key="i">
                      {{ b }}
                    </li>
                  </ul>
                </div>
              </div>

              <!-- Memory -->
              <div>
                <h3 class="mb-2 font-semibold text-gray-900">3️⃣ Memory</h3>
                <div class="rounded-md bg-indigo-50 p-4">
                  <div class="space-y-2 text-sm">
                    <div class="flex items-center gap-2">
                      <span class="font-semibold">Short-Term:</span>
                      <span
                        :class="
                          factoryStore.currentSpec.spec.memory.short_term
                            ? 'text-green-600'
                            : 'text-gray-400'
                        "
                      >
                        {{
                          factoryStore.currentSpec.spec.memory.short_term
                            ? '✅ Enabled'
                            : '❌ Disabled'
                        }}
                      </span>
                      <span class="text-xs text-gray-600">(Conversation context)</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <span class="font-semibold">Long-Term:</span>
                      <span
                        :class="
                          factoryStore.currentSpec.spec.memory.long_term
                            ? 'text-green-600'
                            : 'text-gray-400'
                        "
                      >
                        {{
                          factoryStore.currentSpec.spec.memory.long_term
                            ? '✅ Enabled'
                            : '❌ Disabled'
                        }}
                      </span>
                      <span class="text-xs text-gray-600">(RAG/Vector database)</span>
                    </div>
                    <div
                      v-if="factoryStore.currentSpec.spec.memory.rag_collection"
                      class="ml-4 text-xs text-gray-600"
                    >
                      📚 Collection: {{ factoryStore.currentSpec.spec.memory.rag_collection }}
                    </div>
                    <div
                      v-else-if="factoryStore.currentSpec.spec.memory.long_term"
                      class="ml-4 text-xs text-gray-600"
                    >
                      📚 Collection: agent_{{
                        factoryStore.currentSpec.id.substring(0, 8)
                      }}
                      (auto-generated)
                    </div>
                  </div>
                  <div class="mt-3 text-xs text-gray-600 bg-white rounded p-2">
                    <p><strong>💡 How it works:</strong></p>
                    <ul class="mt-1 ml-4 list-disc space-y-1">
                      <li><strong>Short-term</strong>: Remembers this conversation</li>
                      <li><strong>Long-term</strong>: Remembers across all sessions (permanent)</li>
                    </ul>
                  </div>
                </div>
              </div>

              <!-- Tools -->
              <div>
                <h3 class="mb-2 font-semibold text-gray-900">4️⃣ Tools</h3>
                <!-- Edit Mode -->
                <div v-if="editMode" class="grid grid-cols-2 gap-2">
                  <button
                    v-for="(tool, idx) in editableTools"
                    :key="tool.name"
                    :class="[
                      'rounded-md p-2 text-sm cursor-pointer hover:opacity-80',
                      tool.enabled
                        ? 'bg-green-50 text-green-800 border-2 border-green-300'
                        : 'bg-gray-100 text-gray-500 border-2 border-gray-300',
                    ]"
                    @click="toggleTool(idx)"
                  >
                    {{ tool.name }} {{ tool.enabled ? '✓' : '✗' }}
                  </button>
                </div>
                <!-- View Mode -->
                <div v-else class="grid grid-cols-2 gap-2">
                  <div
                    v-for="tool in factoryStore.currentSpec.spec.tools"
                    :key="tool.name"
                    :class="[
                      'rounded-md p-2 text-sm',
                      tool.enabled ? 'bg-green-50 text-green-800' : 'bg-gray-100 text-gray-500',
                    ]"
                  >
                    {{ tool.name }} {{ tool.enabled ? '✓' : '✗' }}
                  </div>
                </div>
              </div>

              <!-- Policies -->
              <div>
                <h3 class="mb-2 font-semibold text-gray-900">5️⃣ Decision Policies</h3>
                <div class="rounded-md bg-yellow-50 p-4">
                  <!-- Edit Mode -->
                  <div v-if="editMode" class="space-y-2">
                    <div v-for="(_, idx) in editablePolicies" :key="idx" class="flex gap-2">
                      <input
                        v-model="editablePolicies[idx]"
                        type="text"
                        class="flex-1 rounded-md border border-gray-300 p-2 text-sm"
                        placeholder="Enter policy..."
                      />
                      <button
                        class="rounded-md bg-red-100 px-3 py-1 text-red-600 hover:bg-red-200 text-sm"
                        @click="removePolicy(idx)"
                      >
                        ✕
                      </button>
                    </div>
                    <button
                      class="mt-2 rounded-md bg-yellow-600 px-4 py-2 text-sm text-white hover:bg-yellow-700"
                      @click="addPolicy"
                    >
                      ➕ Add Policy
                    </button>
                  </div>
                  <!-- View Mode -->
                  <ul v-else class="list-disc ml-4 text-sm">
                    <li v-for="(p, i) in factoryStore.currentSpec.spec.policies" :key="i">
                      {{ p }}
                    </li>
                  </ul>
                  <p
                    v-if="factoryStore.currentSpec.spec.compiler_notes"
                    class="mt-3 text-xs text-gray-600"
                  >
                    <strong>Note:</strong> {{ factoryStore.currentSpec.spec.compiler_notes }}
                  </p>
                </div>
              </div>

              <!-- Workflow -->
              <div>
                <h3 class="mb-2 font-semibold text-gray-900">8️⃣ Execution Workflow</h3>
                <div class="rounded-md bg-purple-50 p-4">
                  <div v-if="factoryStore.currentSpec.spec.workflow?.enabled" class="space-y-4">
                    <!-- Workflow Nodes -->
                    <div class="space-y-2">
                      <div
                        v-for="node in factoryStore.currentSpec.spec.workflow.nodes"
                        :key="node.id"
                        class="flex items-center gap-2 rounded-md bg-white p-2 border-l-4"
                        :class="{
                          'border-green-500': node.type === 'start',
                          'border-blue-500': node.type === 'think',
                          'border-yellow-500': node.type === 'tool',
                          'border-orange-500': node.type === 'decision',
                          'border-red-500': node.type === 'end',
                        }"
                      >
                        <span class="text-xs font-mono text-gray-500">{{ node.id }}</span>
                        <span class="text-sm font-semibold">{{ node.type }}</span>
                        <span class="text-sm text-gray-700">{{ node.label }}</span>
                        <span v-if="node.tool_name" class="text-xs bg-yellow-100 px-2 py-1 rounded"
                          >🔧 {{ node.tool_name }}</span
                        >
                      </div>
                    </div>
                    <!-- Workflow Edges -->
                    <div class="text-xs text-gray-600">
                      <p class="font-semibold mb-1">Connections:</p>
                      <div
                        v-for="(edge, idx) in factoryStore.currentSpec.spec.workflow.edges"
                        :key="idx"
                        class="ml-2"
                      >
                        {{ edge.from_node }} → {{ edge.to_node }}
                        <span v-if="edge.condition" class="text-orange-600"
                          >(if: {{ edge.condition }})</span
                        >
                      </div>
                    </div>
                  </div>
                  <div v-else class="text-sm text-gray-600">
                    <p>🔄 Using default ReAct loop (Think → Act → Observe → Think...)</p>
                    <button
                      v-if="canEdit && editMode"
                      class="mt-2 text-xs text-purple-600 hover:text-purple-800 underline"
                    >
                      ➕ Enable custom workflow
                    </button>
                  </div>
                </div>
              </div>

              <!-- Run Section -->
              <div v-if="canRun">
                <h3 class="mb-2 font-semibold text-gray-900">▶️ Test Run</h3>
                <div class="rounded-md bg-blue-50 p-4">
                  <input
                    v-model="runInput"
                    type="text"
                    placeholder="Enter task input..."
                    class="w-full rounded-md border border-gray-300 p-2 text-sm"
                  />
                  <button
                    :disabled="!runInput.trim() || factoryStore.loading"
                    class="mt-2 rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:bg-gray-300"
                    @click="handleRun"
                  >
                    {{ factoryStore.loading ? 'Running...' : 'Run Agent' }}
                  </button>

                  <!-- Run Result -->
                  <div v-if="factoryStore.runResult" class="mt-4 rounded-md bg-white p-3">
                    <p class="text-sm font-semibold">Result:</p>
                    <p class="mt-2 text-sm whitespace-pre-wrap">
                      {{ factoryStore.runResult.final }}
                    </p>
                  </div>
                </div>
              </div>

              <!-- Memory Viewer -->
              <div v-if="factoryStore.currentSpec.spec.memory.long_term" class="mt-6">
                <div class="flex items-center justify-between mb-2">
                  <h3 class="font-semibold text-gray-900">🧠 Agent Memory</h3>
                  <span class="text-xs text-gray-500">{{ memoryTotal }} memories</span>
                </div>
                <div class="rounded-md bg-purple-50 p-4">
                  <!-- Search Bar -->
                  <div class="flex gap-2 mb-3">
                    <input
                      v-model="memorySearchQuery"
                      type="text"
                      placeholder="Search memories (press Enter)..."
                      class="flex-1 rounded-md border border-gray-300 p-2 text-sm"
                      @keyup.enter="searchMemories"
                    />
                    <button
                      :disabled="memoryLoading"
                      class="rounded-md bg-purple-600 px-4 py-2 text-sm text-white hover:bg-purple-700 disabled:bg-gray-300"
                      @click="searchMemories"
                    >
                      🔍
                    </button>
                    <button
                      :disabled="memoryLoading"
                      class="rounded-md bg-gray-600 px-3 py-2 text-sm text-white hover:bg-gray-700 disabled:bg-gray-300"
                      title="Load recent memories"
                      @click="loadRecentMemories"
                    >
                      ↻
                    </button>
                    <button
                      :disabled="memoryLoading || memoryTotal === 0"
                      class="rounded-md bg-red-600 px-3 py-2 text-sm text-white hover:bg-red-700 disabled:bg-gray-300"
                      title="Clear all memories"
                      @click="clearAllMemories"
                    >
                      🗑️
                    </button>
                  </div>

                  <!-- Memory List -->
                  <div v-if="memoryLoading" class="text-center py-4">
                    <p class="text-sm text-gray-500">Loading...</p>
                  </div>
                  <div v-else-if="memories.length === 0" class="text-center py-4">
                    <p class="text-sm text-gray-500">No memories found</p>
                  </div>
                  <div v-else class="space-y-2 max-h-96 overflow-y-auto">
                    <div
                      v-for="memory in memories"
                      :key="memory.id"
                      class="rounded-md bg-white p-3 text-sm"
                    >
                      <div class="flex items-start justify-between mb-1">
                        <p class="text-xs text-gray-500">
                          {{ new Date(memory.timestamp).toLocaleString() }}
                        </p>
                        <div class="flex gap-2 text-xs text-gray-400">
                          <span v-if="memory.metadata.role" class="px-1 rounded bg-gray-100">
                            {{ memory.metadata.role }}
                          </span>
                        </div>
                      </div>
                      <p class="whitespace-pre-wrap">
                        {{ memory.content }}
                      </p>
                      <div v-if="memory.keywords.length" class="flex gap-1 mt-2 flex-wrap">
                        <span
                          v-for="keyword in memory.keywords.slice(0, 5)"
                          :key="keyword"
                          class="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded"
                        >
                          {{ keyword }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div
          v-else
          class="lg:col-span-2 flex items-center justify-center rounded-lg bg-white p-12 shadow"
        >
          <div class="text-center text-gray-500">
            <p class="text-lg">Select a spec or compile a new one to get started</p>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
