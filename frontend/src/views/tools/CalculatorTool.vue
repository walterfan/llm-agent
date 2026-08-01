<script setup lang="ts">
import { ref } from 'vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import { useSecretaryStore } from '@/stores/secretary'

const secretaryStore = useSecretaryStore()

const expression = ref('')
const result = ref<string | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const examples = [
  '2 + 3 * 4',
  'sqrt(16) + 2',
  'sin(0) + cos(0)',
  '(10 + 5) / 3',
  'pi * 2',
  'log(100)',
]

async function calculate() {
  if (!expression.value.trim()) return

  loading.value = true
  error.value = null
  result.value = null

  try {
    const response = await secretaryStore.calculate(expression.value)
    result.value = response
  } catch (err: any) {
    error.value = err.message || 'Calculation failed'
  } finally {
    loading.value = false
  }
}

function setExample(expr: string) {
  expression.value = expr
}
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <AppHeader />

    <div class="max-w-2xl mx-auto px-4 py-8">
      <h1 class="text-2xl font-bold text-gray-800 mb-2">🧮 Calculator Tool</h1>
      <p class="text-gray-600 mb-6">
        Test the calculator tool. Enter a mathematical expression to evaluate.
      </p>

      <!-- Input -->
      <div class="bg-white rounded-lg shadow p-6 mb-6">
        <label class="block text-sm font-medium text-gray-700 mb-2"> Expression </label>
        <div class="flex gap-2">
          <input
            v-model="expression"
            type="text"
            placeholder="e.g., sqrt(16) + 2 * 3"
            class="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            @keyup.enter="calculate"
          />
          <button
            type="button"
            :disabled="loading || !expression.trim()"
            class="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            @click="calculate"
          >
            {{ loading ? 'Calculating...' : 'Calculate' }}
          </button>
        </div>

        <!-- Examples -->
        <div class="mt-4">
          <span class="text-sm text-gray-500">Examples: </span>
          <div class="flex flex-wrap gap-2 mt-2">
            <button
              v-for="ex in examples"
              :key="ex"
              type="button"
              class="px-3 py-1 text-sm bg-gray-100 rounded-full hover:bg-gray-200"
              @click="setExample(ex)"
            >
              {{ ex }}
            </button>
          </div>
        </div>
      </div>

      <!-- Result -->
      <div v-if="result || error" class="bg-white rounded-lg shadow p-6">
        <h3 class="text-sm font-medium text-gray-500 mb-2">Result</h3>
        <div v-if="error" class="text-red-600">
          {{ error }}
        </div>
        <div v-else class="text-lg text-gray-800 whitespace-pre-wrap">
          {{ result }}
        </div>
      </div>

      <!-- Supported Functions -->
      <div class="mt-6 text-sm text-gray-500">
        <h4 class="font-medium mb-2">Supported Functions:</h4>
        <ul class="list-disc list-inside space-y-1">
          <li>Basic: +, -, *, /, ** (power)</li>
          <li>Functions: sqrt, sin, cos, tan, log, exp, abs, floor, ceil</li>
          <li>Constants: pi, e</li>
        </ul>
      </div>
    </div>
  </div>
</template>
