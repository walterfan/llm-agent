<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const route = useRoute()

// Dropdown menu states
const adminMenuOpen = ref(false)
const aiAgentsMenuOpen = ref(false)
const aiToolsMenuOpen = ref(false)

// Timeout references for each menu
let adminCloseTimeout: ReturnType<typeof setTimeout> | null = null
let aiAgentsCloseTimeout: ReturnType<typeof setTimeout> | null = null
let aiToolsCloseTimeout: ReturnType<typeof setTimeout> | null = null

const handleLogout = () => {
  authStore.logout()
}

// Admin menu handlers
const toggleAdminMenu = () => {
  adminMenuOpen.value = !adminMenuOpen.value
}

const openAdminMenu = () => {
  if (adminCloseTimeout) {
    clearTimeout(adminCloseTimeout)
    adminCloseTimeout = null
  }
  adminMenuOpen.value = true
}

const closeAdminMenu = () => {
  adminMenuOpen.value = false
  if (adminCloseTimeout) {
    clearTimeout(adminCloseTimeout)
    adminCloseTimeout = null
  }
}

const startAdminCloseTimeout = () => {
  adminCloseTimeout = setTimeout(() => {
    adminMenuOpen.value = false
  }, 200)
}

// AI Agents menu handlers
const toggleAiAgentsMenu = () => {
  aiAgentsMenuOpen.value = !aiAgentsMenuOpen.value
}

const openAiAgentsMenu = () => {
  if (aiAgentsCloseTimeout) {
    clearTimeout(aiAgentsCloseTimeout)
    aiAgentsCloseTimeout = null
  }
  aiAgentsMenuOpen.value = true
}

const closeAiAgentsMenu = () => {
  aiAgentsMenuOpen.value = false
  if (aiAgentsCloseTimeout) {
    clearTimeout(aiAgentsCloseTimeout)
    aiAgentsCloseTimeout = null
  }
}

const startAiAgentsCloseTimeout = () => {
  aiAgentsCloseTimeout = setTimeout(() => {
    aiAgentsMenuOpen.value = false
  }, 200)
}

// AI Tools menu handlers
const toggleAiToolsMenu = () => {
  aiToolsMenuOpen.value = !aiToolsMenuOpen.value
}

const openAiToolsMenu = () => {
  if (aiToolsCloseTimeout) {
    clearTimeout(aiToolsCloseTimeout)
    aiToolsCloseTimeout = null
  }
  aiToolsMenuOpen.value = true
}

const closeAiToolsMenu = () => {
  aiToolsMenuOpen.value = false
  if (aiToolsCloseTimeout) {
    clearTimeout(aiToolsCloseTimeout)
    aiToolsCloseTimeout = null
  }
}

const startAiToolsCloseTimeout = () => {
  aiToolsCloseTimeout = setTimeout(() => {
    aiToolsMenuOpen.value = false
  }, 200)
}

// Check if current route is an admin route
const isAdminRoute = () => {
  return (
    route.path.startsWith('/admin') ||
    route.path.startsWith('/rbac') ||
    route.path.startsWith('/admin/scheduler')
  )
}

// Check if current route is an AI Agents route
const isAiAgentsRoute = () => {
  return (
    route.path.startsWith('/recommendations') ||
    route.path.startsWith('/secretary') ||
    route.path.startsWith('/learning') ||
    route.path.startsWith('/medical-paper') ||
    route.path.startsWith('/translation') ||
    route.path.startsWith('/philosophy') ||
    route.path.startsWith('/factory') ||
    route.path.startsWith('/coach') ||
    route.path.startsWith('/knowledge') ||
    route.path.startsWith('/learning-plan')
  )
}

// Check if current route is an AI Tools route
const isAiToolsRoute = () => {
  return route.path.startsWith('/weather') || route.path.startsWith('/tools/')
}
</script>

<template>
  <header class="bg-white shadow-sm">
    <nav class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div class="flex h-16 justify-between items-center">
        <div class="flex items-center">
          <RouterLink to="/" class="text-2xl font-bold text-primary-600">
            Lazy Rabbit Agent
          </RouterLink>
        </div>

        <div class="flex items-center gap-4">
          <RouterLink
            v-if="!authStore.isAuthenticated"
            to="/signin"
            class="text-gray-700 hover:text-primary-600 px-3 py-2 rounded-md text-sm font-medium"
          >
            Sign In
          </RouterLink>
          <RouterLink
            v-if="!authStore.isAuthenticated"
            to="/signup"
            class="bg-primary-600 text-white hover:bg-primary-700 px-4 py-2 rounded-md text-sm font-medium"
          >
            Sign Up
          </RouterLink>

          <template v-if="authStore.isAuthenticated">
            <!-- AI Agents Dropdown Menu -->
            <div
              class="relative"
              @mouseenter="openAiAgentsMenu"
              @mouseleave="startAiAgentsCloseTimeout"
            >
              <button
                :class="[
                  'text-gray-700 hover:text-primary-600 px-3 py-2 rounded-md text-sm font-medium flex items-center gap-1',
                  isAiAgentsRoute() ? 'text-primary-600 font-semibold' : '',
                ]"
                @click="toggleAiAgentsMenu"
              >
                🤖 AI Agents
                <svg
                  class="w-4 h-4 transition-transform"
                  :class="{ 'rotate-180': aiAgentsMenuOpen }"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>

              <!-- AI Agents Dropdown -->
              <div
                v-show="aiAgentsMenuOpen"
                class="absolute left-0 mt-0 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-50"
                @mouseenter="openAiAgentsMenu"
                @mouseleave="startAiAgentsCloseTimeout"
              >
                <div class="py-1">
                  <RouterLink
                    to="/secretary"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAiAgentsMenu"
                  >
                    🤖 Personal Secretary
                  </RouterLink>
                  <RouterLink
                    to="/learning"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAiAgentsMenu"
                  >
                    📚 Learning History
                  </RouterLink>
                  <RouterLink
                    to="/medical-paper"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAiAgentsMenu"
                  >
                    📄 Medical Paper
                  </RouterLink>
                  <RouterLink
                    to="/recommendations"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAiAgentsMenu"
                  >
                    👔 AI Dress Agent
                  </RouterLink>
                  <RouterLink
                    to="/translation"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAiAgentsMenu"
                  >
                    🌐 Translation
                  </RouterLink>
                  <RouterLink
                    to="/philosophy"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAiAgentsMenu"
                  >
                    🧠 Philosophy Master
                  </RouterLink>
                  <div class="border-t my-1" />
                  <RouterLink
                    to="/factory"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAiAgentsMenu"
                  >
                    🏭 AI Agent Factory
                  </RouterLink>
                  <RouterLink
                    to="/coach"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAiAgentsMenu"
                  >
                    🎓 AI Coach
                  </RouterLink>
                  <RouterLink
                    to="/knowledge"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAiAgentsMenu"
                  >
                    📚 Knowledge Base
                  </RouterLink>
                  <RouterLink
                    to="/learning-plan"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAiAgentsMenu"
                  >
                    📅 Learning Plan
                  </RouterLink>
                </div>
              </div>
            </div>

            <!-- AI Tools Dropdown Menu -->
            <div
              class="relative"
              @mouseenter="openAiToolsMenu"
              @mouseleave="startAiToolsCloseTimeout"
            >
              <button
                :class="[
                  'text-gray-700 hover:text-primary-600 px-3 py-2 rounded-md text-sm font-medium flex items-center gap-1',
                  isAiToolsRoute() ? 'text-primary-600 font-semibold' : '',
                ]"
                @click="toggleAiToolsMenu"
              >
                🛠️ AI Tools
                <svg
                  class="w-4 h-4 transition-transform"
                  :class="{ 'rotate-180': aiToolsMenuOpen }"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>

              <!-- AI Tools Dropdown -->
              <div
                v-show="aiToolsMenuOpen"
                class="absolute left-0 mt-0 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-50"
                @mouseenter="openAiToolsMenu"
                @mouseleave="startAiToolsCloseTimeout"
              >
                <div class="py-1">
                  <!-- Utility Tools -->
                  <div class="px-4 py-1 text-xs text-gray-500 font-semibold uppercase">Utility</div>
                  <RouterLink
                    to="/weather"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAiToolsMenu"
                  >
                    🌤️ Weather
                  </RouterLink>
                  <RouterLink
                    to="/tools/calculator"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAiToolsMenu"
                  >
                    🧮 Calculator
                  </RouterLink>
                  <RouterLink
                    to="/tools/datetime"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAiToolsMenu"
                  >
                    🕐 Date & Time
                  </RouterLink>

                  <!-- Productivity Tools -->
                  <div
                    class="px-4 py-1 mt-2 text-xs text-gray-500 font-semibold uppercase border-t"
                  >
                    Productivity
                  </div>
                  <RouterLink
                    to="/tools/notes"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAiToolsMenu"
                  >
                    📝 Notes
                  </RouterLink>
                  <RouterLink
                    to="/tools/tasks"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAiToolsMenu"
                  >
                    ✅ Tasks
                  </RouterLink>
                  <RouterLink
                    to="/tools/reminders"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAiToolsMenu"
                  >
                    ⏰ Reminders
                  </RouterLink>
                </div>
              </div>
            </div>

            <!-- Admin Dropdown Menu -->
            <div
              v-if="authStore.isAdmin"
              class="relative"
              @mouseenter="openAdminMenu"
              @mouseleave="startAdminCloseTimeout"
            >
              <button
                :class="[
                  'text-gray-700 hover:text-primary-600 px-3 py-2 rounded-md text-sm font-medium flex items-center gap-1',
                  isAdminRoute() ? 'text-primary-600 font-semibold' : '',
                ]"
                @click="toggleAdminMenu"
              >
                ⚙️ Admin
                <svg
                  class="w-4 h-4 transition-transform"
                  :class="{ 'rotate-180': adminMenuOpen }"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>

              <!-- Dropdown Menu -->
              <div
                v-show="adminMenuOpen"
                class="absolute left-0 mt-0 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-50"
                @mouseenter="openAdminMenu"
                @mouseleave="startAdminCloseTimeout"
              >
                <div class="py-1">
                  <RouterLink
                    v-if="authStore.isSuperAdmin"
                    to="/admin/users"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAdminMenu"
                  >
                    👥 Users
                  </RouterLink>
                  <RouterLink
                    v-if="authStore.isAdmin"
                    to="/admin/email-management"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAdminMenu"
                  >
                    📧 Email Settings
                  </RouterLink>
                  <RouterLink
                    v-if="authStore.isAdmin"
                    to="/admin/scheduler"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAdminMenu"
                  >
                    ⏰ Job Scheduler
                  </RouterLink>
                  <RouterLink
                    v-if="authStore.isSuperAdmin"
                    to="/rbac/roles"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAdminMenu"
                  >
                    🔐 Roles
                  </RouterLink>
                  <RouterLink
                    v-if="authStore.isSuperAdmin"
                    to="/rbac/permissions"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    @click="closeAdminMenu"
                  >
                    🔑 Permissions
                  </RouterLink>
                </div>
              </div>
            </div>

            <RouterLink
              to="/admin/llm-settings"
              class="text-gray-700 hover:text-primary-600 px-3 py-2 rounded-md text-sm font-medium"
            >
              LLM Settings
            </RouterLink>
            <RouterLink
              to="/profile"
              class="text-gray-700 hover:text-primary-600 px-3 py-2 rounded-md text-sm font-medium"
            >
              Profile
            </RouterLink>
            <button
              class="text-gray-700 hover:text-red-600 px-3 py-2 rounded-md text-sm font-medium"
              @click="handleLogout"
            >
              Logout
            </button>
          </template>
        </div>
      </div>
    </nav>
  </header>
</template>
