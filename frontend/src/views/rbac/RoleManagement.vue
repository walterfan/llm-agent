<template>
  <AppLayout>
    <div class="mx-auto max-w-7xl px-4 py-8">
      <div class="mb-6 flex items-center justify-between">
        <div>
          <h1 class="text-3xl font-bold text-gray-900">Role Management</h1>
          <p class="mt-1 text-sm text-gray-600">Manage system roles and their permissions</p>
        </div>
        <button
          class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          @click="openCreateDialog"
        >
          + Create Role
        </button>
      </div>

      <!-- Search -->
      <div class="mb-6">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search roles..."
          class="w-full max-w-md rounded-md border border-gray-300 px-4 py-2"
          @input="debouncedSearch"
        />
      </div>

      <!-- Error Message -->
      <div v-if="rbacStore.error" class="mb-6 rounded-md bg-red-50 p-4 text-sm text-red-700">
        {{ rbacStore.error }}
      </div>

      <!-- Loading -->
      <div v-if="rbacStore.loading && !rbacStore.roles.length" class="text-center py-12">
        <div
          class="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"
        />
        <p class="mt-4 text-gray-600">Loading roles...</p>
      </div>

      <!-- Roles Grid -->
      <div
        v-else-if="rbacStore.roles.length"
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        <div
          v-for="role in rbacStore.roles"
          :key="role.id"
          class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm hover:shadow-md transition-shadow"
        >
          <div class="flex items-start justify-between mb-4">
            <div class="flex-1">
              <h3 class="text-lg font-semibold text-gray-900">
                {{ role.name }}
              </h3>
              <p class="mt-1 text-sm text-gray-600">
                {{ role.description || 'No description' }}
              </p>
            </div>
          </div>

          <div class="mb-4">
            <span class="text-sm font-medium text-gray-700">Permissions:</span>
            <span
              class="ml-2 inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800"
            >
              {{ role.permissions.length }}
            </span>
          </div>

          <div class="flex space-x-2">
            <button
              class="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              @click="openViewDialog(role)"
            >
              View
            </button>
            <button
              class="flex-1 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
              @click="openEditDialog(role)"
            >
              Edit
            </button>
            <button
              class="rounded-md border border-red-300 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
              @click="openDeleteDialog(role)"
            >
              Delete
            </button>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="rounded-lg bg-white p-12 text-center shadow">
        <p class="text-gray-600">No roles found</p>
      </div>

      <!-- Pagination -->
      <div v-if="rbacStore.totalRoles > pageSize" class="mt-6 flex justify-center">
        <div class="flex space-x-2">
          <button
            :disabled="currentPage === 1"
            class="rounded-md border border-gray-300 px-3 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50"
            @click="previousPage"
          >
            Previous
          </button>
          <span class="px-3 py-1 text-sm text-gray-700">
            Page {{ currentPage }} of {{ totalPages }}
          </span>
          <button
            :disabled="currentPage >= totalPages"
            class="rounded-md border border-gray-300 px-3 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50"
            @click="nextPage"
          >
            Next
          </button>
        </div>
      </div>
    </div>

    <!-- Dialogs (simplified for now) -->
    <div
      v-if="isCreateDialogOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      @click.self="closeCreateDialog"
    >
      <div class="w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl">
        <h2 class="mb-4 text-xl font-semibold">Create Role</h2>
        <p class="text-sm text-gray-600 mb-4">Feature coming soon: Use API directly for now</p>
        <button class="rounded-md bg-gray-600 px-4 py-2 text-white" @click="closeCreateDialog">
          Close
        </button>
      </div>
    </div>

    <div
      v-if="isViewDialogOpen && selectedRole"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      @click.self="closeViewDialog"
    >
      <div class="w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl max-h-[80vh] overflow-y-auto">
        <h2 class="mb-4 text-xl font-semibold">
          {{ selectedRole.name }}
        </h2>
        <p class="text-sm text-gray-600 mb-4">
          {{ selectedRole.description }}
        </p>
        <h3 class="font-medium mb-2">Permissions ({{ selectedRole.permissions.length }}):</h3>
        <div class="space-y-1 max-h-96 overflow-y-auto">
          <div
            v-for="perm in selectedRole.permissions"
            :key="perm.id"
            class="text-sm bg-gray-50 px-3 py-2 rounded"
          >
            <span class="font-medium">{{ perm.name }}</span>
            <span class="text-gray-600 ml-2">({{ perm.resource }}.{{ perm.action }})</span>
          </div>
        </div>
        <button class="mt-4 rounded-md bg-gray-600 px-4 py-2 text-white" @click="closeViewDialog">
          Close
        </button>
      </div>
    </div>

    <div
      v-if="isDeleteDialogOpen && selectedRole"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      @click.self="closeDeleteDialog"
    >
      <div class="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 class="mb-4 text-xl font-semibold">Delete Role</h2>
        <p class="mb-6 text-gray-600">
          Are you sure you want to delete role <strong>{{ selectedRole.name }}</strong
          >?
        </p>
        <div class="flex justify-end space-x-3">
          <button class="rounded-md border px-4 py-2" @click="closeDeleteDialog">Cancel</button>
          <button class="rounded-md bg-red-600 px-4 py-2 text-white" @click="handleDeleteRole">
            Delete
          </button>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRBACStore } from '@/stores/rbac'
import type { Role } from '@/types/rbac'
import AppLayout from '@/components/layout/AppLayout.vue'

const rbacStore = useRBACStore()

const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(20)

const isCreateDialogOpen = ref(false)
const isViewDialogOpen = ref(false)
const isEditDialogOpen = ref(false)
const isDeleteDialogOpen = ref(false)
const selectedRole = ref<Role | null>(null)

let searchTimeout: ReturnType<typeof setTimeout> | null = null

const totalPages = computed(() => Math.ceil(rbacStore.totalRoles / pageSize.value))

onMounted(() => {
  fetchRoles()
})

async function fetchRoles() {
  const skip = (currentPage.value - 1) * pageSize.value
  await rbacStore.fetchRoles({
    skip,
    limit: pageSize.value,
    search: searchQuery.value || undefined,
  })
}

function debouncedSearch() {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    fetchRoles()
  }, 300)
}

function previousPage() {
  if (currentPage.value > 1) {
    currentPage.value--
    fetchRoles()
  }
}

function nextPage() {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
    fetchRoles()
  }
}

function openCreateDialog() {
  isCreateDialogOpen.value = true
}

function closeCreateDialog() {
  isCreateDialogOpen.value = false
}

function openViewDialog(role: Role) {
  selectedRole.value = role
  isViewDialogOpen.value = true
}

function closeViewDialog() {
  isViewDialogOpen.value = false
  selectedRole.value = null
}

function openEditDialog(role: Role) {
  selectedRole.value = role
  isEditDialogOpen.value = true
}

// function closeEditDialog() {
//   isEditDialogOpen.value = false
//   selectedRole.value = null
// }

function openDeleteDialog(role: Role) {
  selectedRole.value = role
  isDeleteDialogOpen.value = true
}

function closeDeleteDialog() {
  isDeleteDialogOpen.value = false
  selectedRole.value = null
}

async function handleDeleteRole() {
  if (!selectedRole.value) return
  try {
    await rbacStore.deleteRole(selectedRole.value.id)
    closeDeleteDialog()
    fetchRoles()
  } catch (err) {
    // Error handled by store
  }
}
</script>
