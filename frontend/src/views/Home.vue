<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/components/layout/AppLayout.vue'
import ButtonComponent from '@/components/forms/ButtonComponent.vue'

const authStore = useAuthStore()

// Define available AI agents (implemented)
const agents = [
  {
    id: 'secretary',
    name: 'Personal Secretary',
    icon: '🤖',
    description:
      'Your AI assistant for learning English, tech topics, managing tasks, notes, and reminders',
    route: '/secretary',
    color: 'from-blue-500 to-indigo-600',
  },
  {
    id: 'learning',
    name: 'Learning History',
    icon: '📚',
    description:
      'Review and manage your learning records: words, sentences, topics, articles, and ideas',
    route: '/learning',
    color: 'from-amber-500 to-orange-600',
  },
  {
    id: 'medical-paper',
    name: 'Medical Paper',
    icon: '📄',
    description:
      'AI-assisted medical paper writing with compliance, literature, stats, and writing support',
    route: '/medical-paper',
    color: 'from-emerald-500 to-teal-600',
  },
  {
    id: 'dress',
    name: 'AI Dress Agent',
    icon: '👔',
    description: 'Get personalized outfit suggestions based on weather and your style preferences',
    route: '/recommendations',
    color: 'from-pink-500 to-rose-600',
  },
  {
    id: 'translation',
    name: 'Translation',
    icon: '🌐',
    description:
      'Translate URLs, pasted text, or uploaded files (PDF/text/md) to Chinese with explanation and summary',
    route: '/translation',
    color: 'from-violet-500 to-purple-600',
  },
  {
    id: 'philosophy',
    name: 'Philosophy Master',
    icon: '🧠',
    description:
      'Philosophical analysis and practical guidance with selectable schools, tone, depth, and modes',
    route: '/philosophy',
    color: 'from-cyan-500 to-sky-600',
  },
  {
    id: 'coach',
    name: 'AI Coach',
    icon: '🎓',
    description:
      'Personal learning coach with 3 modes: coaching, tutoring, and quiz — powered by your knowledge base',
    route: '/coach',
    color: 'from-amber-500 to-orange-600',
  },
  {
    id: 'factory',
    name: 'AI Agent Factory',
    icon: '🏭',
    description:
      'Create, manage, and deploy custom AI agents with specifications, tools, and memory',
    route: '/factory',
    color: 'from-indigo-500 to-blue-600',
  },
]

// Define available tools
const tools = [
  {
    id: 'weather',
    name: 'Weather',
    icon: '🌤️',
    description: 'Check current weather and forecasts',
    route: '/weather',
  },
  {
    id: 'calculator',
    name: 'Calculator',
    icon: '🧮',
    description: 'Evaluate mathematical expressions',
    route: '/tools/calculator',
  },
  {
    id: 'datetime',
    name: 'Date & Time',
    icon: '🕐',
    description: 'Get current date and time',
    route: '/tools/datetime',
  },
  {
    id: 'notes',
    name: 'Notes',
    icon: '📝',
    description: 'Save and search your notes',
    route: '/tools/notes',
  },
  {
    id: 'tasks',
    name: 'Tasks',
    icon: '✅',
    description: 'Manage your to-do tasks',
    route: '/tools/tasks',
  },
  {
    id: 'reminders',
    name: 'Reminders',
    icon: '⏰',
    description: 'Set and manage reminders',
    route: '/tools/reminders',
  },
]
</script>

<template>
  <AppLayout>
    <!-- Landing page for non-authenticated users -->
    <div v-if="!authStore.isAuthenticated" class="text-center py-12">
      <h1 class="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl mb-4">
        Lazy Rabbit Agent
      </h1>
      <p class="text-lg leading-8 text-gray-600 max-w-2xl mx-auto mb-8">
        Your personal AI assistant for learning, productivity, and daily life. Get help with English
        learning, tech topics, task management, and more.
      </p>

      <div class="flex gap-4 justify-center">
        <RouterLink to="/signup">
          <ButtonComponent>Get Started</ButtonComponent>
        </RouterLink>
        <RouterLink to="/signin">
          <ButtonComponent variant="secondary"> Sign In </ButtonComponent>
        </RouterLink>
      </div>

      <!-- Features preview -->
      <div class="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
        <div class="bg-white p-6 rounded-lg shadow">
          <div class="text-4xl mb-4">🤖</div>
          <h3 class="text-lg font-semibold mb-2">AI Agents</h3>
          <p class="text-gray-600">
            Intelligent assistants that help you learn, work, and organize your life
          </p>
        </div>

        <div class="bg-white p-6 rounded-lg shadow">
          <div class="text-4xl mb-4">📚</div>
          <h3 class="text-lg font-semibold mb-2">Learning Tools</h3>
          <p class="text-gray-600">
            Learn English words, sentences, and tech topics with AI-powered explanations
          </p>
        </div>

        <div class="bg-white p-6 rounded-lg shadow">
          <div class="text-4xl mb-4">✅</div>
          <h3 class="text-lg font-semibold mb-2">Productivity</h3>
          <p class="text-gray-600">Manage tasks, notes, and reminders all in one place</p>
        </div>
      </div>
    </div>

    <!-- Agent Dashboard for authenticated users -->
    <div v-else class="py-8">
      <div class="max-w-6xl mx-auto">
        <!-- Welcome section -->
        <div class="mb-8">
          <h1 class="text-3xl font-bold text-gray-900">
            Welcome back{{ authStore.user?.full_name ? `, ${authStore.user.full_name}` : '' }}!
          </h1>
          <p class="mt-2 text-gray-600">Choose an AI agent or tool to get started.</p>
        </div>

        <!-- AI Agents Section -->
        <section class="mb-12">
          <h2 class="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <span>🤖</span> AI Agents
          </h2>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <RouterLink
              v-for="agent in agents"
              :key="agent.id"
              :to="agent.route"
              class="group relative overflow-hidden rounded-xl bg-white shadow-md hover:shadow-xl transition-all duration-300"
            >
              <div
                class="absolute inset-0 bg-gradient-to-br opacity-0 group-hover:opacity-10 transition-opacity"
                :class="agent.color"
              />
              <div class="p-6">
                <div class="flex items-start gap-4">
                  <div
                    class="flex-shrink-0 w-14 h-14 rounded-xl bg-gradient-to-br flex items-center justify-center text-2xl"
                    :class="agent.color"
                  >
                    <span class="filter drop-shadow">{{ agent.icon }}</span>
                  </div>
                  <div class="flex-1">
                    <h3
                      class="text-lg font-semibold text-gray-900 group-hover:text-blue-600 transition-colors"
                    >
                      {{ agent.name }}
                    </h3>
                    <p class="mt-1 text-sm text-gray-600">
                      {{ agent.description }}
                    </p>
                  </div>
                  <div
                    class="flex-shrink-0 text-gray-400 group-hover:text-blue-500 transition-colors"
                  >
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                  </div>
                </div>
              </div>
            </RouterLink>
          </div>
        </section>

        <!-- AI Tools Section -->
        <section class="mb-12">
          <h2 class="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <span>🛠️</span> AI Tools
          </h2>
          <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <RouterLink
              v-for="tool in tools"
              :key="tool.id"
              :to="tool.route"
              class="group bg-white rounded-lg shadow hover:shadow-md p-4 text-center transition-all duration-200 hover:-translate-y-1"
            >
              <div class="text-3xl mb-2">
                {{ tool.icon }}
              </div>
              <h3
                class="text-sm font-medium text-gray-900 group-hover:text-blue-600 transition-colors"
              >
                {{ tool.name }}
              </h3>
              <p class="mt-1 text-xs text-gray-500 line-clamp-2">
                {{ tool.description }}
              </p>
            </RouterLink>
          </div>
        </section>

        <!-- Quick Actions -->
        <section>
          <h2 class="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <span>⚡</span> Quick Actions
          </h2>
          <div class="bg-white rounded-xl shadow p-6">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <RouterLink
                to="/factory"
                class="flex items-center gap-3 p-4 rounded-lg bg-gradient-to-br from-indigo-50 to-blue-50 hover:from-indigo-100 hover:to-blue-100 transition-all border-2 border-indigo-200"
              >
                <span class="text-2xl">🏭</span>
                <div>
                  <div class="font-medium text-gray-900">Agent Factory</div>
                  <div class="text-sm text-gray-600">Create custom AI agents</div>
                </div>
              </RouterLink>
              <RouterLink
                to="/learning"
                class="flex items-center gap-3 p-4 rounded-lg bg-gray-50 hover:bg-blue-50 transition-colors"
              >
                <span class="text-2xl">📚</span>
                <div>
                  <div class="font-medium text-gray-900">Learning History</div>
                  <div class="text-sm text-gray-500">Review your learning records</div>
                </div>
              </RouterLink>
              <RouterLink
                to="/tools/tasks"
                class="flex items-center gap-3 p-4 rounded-lg bg-gray-50 hover:bg-green-50 transition-colors"
              >
                <span class="text-2xl">✅</span>
                <div>
                  <div class="font-medium text-gray-900">My Tasks</div>
                  <div class="text-sm text-gray-500">View and manage your tasks</div>
                </div>
              </RouterLink>
              <RouterLink
                to="/profile"
                class="flex items-center gap-3 p-4 rounded-lg bg-gray-50 hover:bg-purple-50 transition-colors"
              >
                <span class="text-2xl">👤</span>
                <div>
                  <div class="font-medium text-gray-900">Profile Settings</div>
                  <div class="text-sm text-gray-500">Update your preferences</div>
                </div>
              </RouterLink>
            </div>
          </div>
        </section>
      </div>
    </div>
  </AppLayout>
</template>
