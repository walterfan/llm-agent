<template>
  <AppLayout>
    <div class="mx-auto max-w-7xl px-4 py-8">
      <div class="mb-6 flex items-center justify-between">
        <div>
          <h1 class="text-3xl font-bold text-gray-900">Permission Management</h1>
          <p class="mt-1 text-sm text-gray-600">Manage system permissions</p>
        </div>
        <button
          class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          @click="openCreateDialog"
        >
          + Create Permission
        </button>
      </div>

      <!-- Filters -->
      <div class="mb-6 flex space-x-4">
        <select
          v-model="resourceFilter"
          class="rounded-md border border-gray-300 px-4 py-2"
          @change="fetchPermissions"
        >
          <option :value="null">All Resources</option>
          <option v-for="resource in uniqueResources" :key="resource" :value="resource">
            {{ resource }}
          </option>
        </select>
      </div>

      <!-- Error -->
      <div v-if="rbacStore.error" class="mb-6 rounded-md bg-red-50 p-4 text-sm text-red-700">
        {{ rbacStore.error }}
      </div>

      <!-- Loading -->
      <div v-if="rbacStore.loading && !rbacStore.permissions.length" class="text-center py-12">
        <div
          class="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"
        />
        <p class="mt-4 text-gray-600">Loading permissions...</p>
      </div>

      <!-- Permissions Table -->
      <div
        v-else-if="rbacStore.permissions.length"
        class="overflow-hidden rounded-lg bg-white shadow"
      >
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th
                class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
              >
                Name
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
              >
                Resource
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
              >
                Action
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
              >
                Description
              </th>
              <th
                class="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500"
              >
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 bg-white">
            <tr
              v-for="permission in rbacStore.permissions"
              :key="permission.id"
              class="hover:bg-gray-50"
            >
              <td class="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
                {{ permission.name }}
              </td>
              <td class="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                <span class="rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-800">
                  {{ permission.resource }}
                </span>
              </td>
              <td class="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                <span
                  class="rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-800"
                >
                  {{ permission.action }}
                </span>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600">
                {{ permission.description || 'N/A' }}
              </td>
              <td class="whitespace-nowrap px-6 py-4 text-right text-sm font-medium">
                <button
                  class="text-blue-600 hover:text-blue-900 mr-4"
                  @click="openEditDialog(permission)"
                >
                  Edit
                </button>
                <button
                  class="text-red-600 hover:text-red-900"
                  @click="openDeleteDialog(permission)"
                >
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Pagination -->
        <div class="border-t border-gray-200 bg-white px-4 py-3">
          <div class="flex items-center justify-between">
            <div class="text-sm text-gray-700">
              Showing {{ (currentPage - 1) * pageSize + 1 }} to
              {{ Math.min(currentPage * pageSize, rbacStore.totalPermissions) }} of
              {{ rbacStore.totalPermissions }} results
            </div>
            <div class="flex space-x-2">
              <button
                :disabled="currentPage === 1"
                class="rounded-md border px-3 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50"
                @click="previousPage"
              >
                Previous
              </button>
              <button
                :disabled="currentPage * pageSize >= rbacStore.totalPermissions"
                class="rounded-md border px-3 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50"
                @click="nextPage"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="rounded-lg bg-white p-12 text-center shadow">
        <p class="text-gray-600">No permissions found</p>
      </div>
    </div>

    <!-- Create/Edit Dialog Placeholder -->
    <div
      v-if="isCreateDialogOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      @click.self="closeCreateDialog"
    >
      <div class="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 class="mb-4 text-xl font-semibold">Create Permission</h2>
        <p class="text-sm text-gray-600 mb-4">Feature coming soon: Use API directly for now</p>
        <button class="rounded-md bg-gray-600 px-4 py-2 text-white" @click="closeCreateDialog">
          Close
        </button>
      </div>
    </div>

    <!-- Delete Dialog -->
    <div
      v-if="isDeleteDialogOpen && selectedPermission"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      @click.self="closeDeleteDialog"
    >
      <div class="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 class="mb-4 text-xl font-semibold">Delete Permission</h2>
        <p class="mb-6 text-gray-600">
          Are you sure you want to delete permission <strong>{{ selectedPermission.name }}</strong
          >?
        </p>
        <div class="flex justify-end space-x-3">
          <button class="rounded-md border px-4 py-2" @click="closeDeleteDialog">Cancel</button>
          <button
            class="rounded-md bg-red-600 px-4 py-2 text-white"
            @click="handleDeletePermission"
          >
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
import type { Permission } from '@/types/rbac'
import AppLayout from '@/components/layout/AppLayout.vue'

const rbacStore = useRBACStore()

const resourceFilter = ref<string | null>(null)
const currentPage = ref(1)
const pageSize = ref(20)

const isCreateDialogOpen = ref(false)
const isEditDialogOpen = ref(false)
const isDeleteDialogOpen = ref(false)
const selectedPermission = ref<Permission | null>(null)

const uniqueResources = computed(() => {
  const resources = new Set(rbacStore.permissions.map((p) => p.resource))
  return Array.from(resources).sort()
})

onMounted(() => {
  fetchPermissions()
})

async function fetchPermissions() {
  const skip = (currentPage.value - 1) * pageSize.value
  await rbacStore.fetchPermissions({
    skip,
    limit: pageSize.value,
    resource: resourceFilter.value || undefined,
  })
}

function previousPage() {
  if (currentPage.value > 1) {
    currentPage.value--
    fetchPermissions()
  }
}

function nextPage() {
  if (currentPage.value * pageSize.value < rbacStore.totalPermissions) {
    currentPage.value++
    fetchPermissions()
  }
}

function openCreateDialog() {
  isCreateDialogOpen.value = true
}

function closeCreateDialog() {
  isCreateDialogOpen.value = false
}

function openEditDialog(permission: Permission) {
  selectedPermission.value = permission
  isEditDialogOpen.value = true
}

// function closeEditDialog() {
//   isEditDialogOpen.value = false
//   selectedPermission.value = null
// }

function openDeleteDialog(permission: Permission) {
  selectedPermission.value = permission
  isDeleteDialogOpen.value = true
}

function closeDeleteDialog() {
  isDeleteDialogOpen.value = false
  selectedPermission.value = null
}

async function handleDeletePermission() {
  if (!selectedPermission.value) return
  try {
    await rbacStore.deletePermission(selectedPermission.value.id)
    closeDeleteDialog()
    fetchPermissions()
  } catch (err) {
    // Error handled by store
  }
}
</script>
