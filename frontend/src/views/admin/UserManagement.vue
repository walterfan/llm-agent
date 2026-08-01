<template>
  <AppLayout>
    <div class="mx-auto max-w-7xl px-4 py-8">
      <div class="mb-6 flex items-center justify-between">
        <div>
          <h1 class="text-3xl font-bold text-gray-900">User Management</h1>
          <p class="mt-1 text-sm text-gray-600">Manage system users, roles, and permissions</p>
        </div>
        <button
          class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          @click="openCreateDialog"
        >
          + Create User
        </button>
      </div>

      <!-- Search and Filters -->
      <div class="mb-6 flex space-x-4">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by email or name..."
          class="flex-1 rounded-md border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          @input="debouncedSearch"
        />
        <select
          v-model="roleFilter"
          class="rounded-md border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          @change="fetchUsers"
        >
          <option :value="null">All Roles</option>
          <option :value="UserRole.SUPER_ADMIN">Super Admin</option>
          <option :value="UserRole.ADMIN">Admin</option>
          <option :value="UserRole.USER">User</option>
          <option :value="UserRole.GUEST">Guest</option>
        </select>
      </div>

      <!-- Pending Approvals Banner -->
      <div
        v-if="pendingCount > 0"
        class="mb-6 rounded-md bg-yellow-50 border border-yellow-200 p-4"
      >
        <div class="flex items-center">
          <svg class="h-5 w-5 text-yellow-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path
              fill-rule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clip-rule="evenodd"
            />
          </svg>
          <span class="text-sm text-yellow-800">
            <strong>{{ pendingCount }}</strong> user(s) pending approval
          </span>
        </div>
      </div>

      <!-- Error Message -->
      <div v-if="adminStore.error" class="mb-6 rounded-md bg-red-50 p-4 text-sm text-red-700">
        {{ adminStore.error }}
      </div>

      <!-- Loading State -->
      <div v-if="adminStore.loading && !adminStore.users.length" class="text-center py-12">
        <div
          class="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"
        />
        <p class="mt-4 text-gray-600">Loading users...</p>
      </div>

      <!-- Users Table -->
      <div v-else-if="adminStore.users.length" class="overflow-hidden rounded-lg bg-white shadow">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th
                class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
              >
                User
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
              >
                Role
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
              >
                Status
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
              >
                Created
              </th>
              <th
                class="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500"
              >
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 bg-white">
            <tr v-for="user in adminStore.users" :key="user.id" class="hover:bg-gray-50">
              <td class="whitespace-nowrap px-6 py-4">
                <div class="text-sm font-medium text-gray-900">
                  {{ user.email }}
                </div>
                <div class="text-sm text-gray-500">
                  {{ user.full_name || 'N/A' }}
                </div>
              </td>
              <td class="whitespace-nowrap px-6 py-4">
                <span
                  :class="getRoleBadgeClass(user.role)"
                  class="inline-flex rounded-full px-2 text-xs font-semibold leading-5"
                >
                  {{ getRoleLabel(user.role) }}
                </span>
              </td>
              <td class="whitespace-nowrap px-6 py-4">
                <span
                  :class="
                    user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  "
                  class="inline-flex rounded-full px-2 text-xs font-semibold leading-5"
                >
                  {{ user.is_active ? 'Active' : 'Inactive' }}
                </span>
              </td>
              <td class="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                {{ formatDate(user.created_at) }}
              </td>
              <td class="whitespace-nowrap px-6 py-4 text-right text-sm font-medium">
                <button
                  v-if="!user.is_active"
                  class="text-green-600 hover:text-green-900 mr-4"
                  title="Approve user"
                  @click="approveUser(user)"
                >
                  ✓ Approve
                </button>
                <button
                  class="text-blue-600 hover:text-blue-900 mr-4"
                  @click="openEditDialog(user)"
                >
                  Edit
                </button>
                <button
                  class="text-purple-600 hover:text-purple-900 mr-4"
                  @click="openProfileDialog(user)"
                >
                  Profile
                </button>
                <button
                  :disabled="user.id === authStore.user?.id"
                  :class="
                    user.id === authStore.user?.id
                      ? 'text-gray-400 cursor-not-allowed'
                      : 'text-red-600 hover:text-red-900'
                  "
                  @click="openDeleteDialog(user)"
                >
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Pagination -->
        <div class="border-t border-gray-200 bg-white px-4 py-3 sm:px-6">
          <div class="flex items-center justify-between">
            <div class="text-sm text-gray-700">
              Showing {{ (currentPage - 1) * pageSize + 1 }} to
              {{ Math.min(currentPage * pageSize, adminStore.totalUsers) }} of
              {{ adminStore.totalUsers }} results
            </div>
            <div class="flex space-x-2">
              <button
                :disabled="currentPage === 1"
                class="rounded-md border border-gray-300 px-3 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50 hover:bg-gray-50"
                @click="previousPage"
              >
                Previous
              </button>
              <button
                :disabled="currentPage * pageSize >= adminStore.totalUsers"
                class="rounded-md border border-gray-300 px-3 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50 hover:bg-gray-50"
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
        <p class="text-gray-600">No users found</p>
      </div>
    </div>

    <!-- Dialogs -->
    <UserCreateDialog
      :is-open="isCreateDialogOpen"
      @close="closeCreateDialog"
      @submit="handleCreateUser"
    />
    <UserEditDialog
      :is-open="isEditDialogOpen"
      :user="selectedUser"
      @close="closeEditDialog"
      @submit="handleUpdateUser"
    />
    <UserProfileDialog
      :is-open="isProfileDialogOpen"
      :user="selectedUser"
      @close="closeProfileDialog"
      @submit="handleUpdateUser"
    />
    <DeleteUserDialog
      :is-open="isDeleteDialogOpen"
      :user="selectedUser"
      @close="closeDeleteDialog"
      @confirm="handleDeleteUser"
    />
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAdminStore } from '@/stores/admin'
import { UserRole } from '@/types/rbac'
import type { User, UserAdminCreate, UserAdminUpdate } from '@/types/rbac'
import AppLayout from '@/components/layout/AppLayout.vue'
import UserCreateDialog from '@/components/admin/UserCreateDialog.vue'
import UserEditDialog from '@/components/admin/UserEditDialog.vue'
import UserProfileDialog from '@/components/admin/UserProfileDialog.vue'
import DeleteUserDialog from '@/components/admin/DeleteUserDialog.vue'

const authStore = useAuthStore()
const adminStore = useAdminStore()

const searchQuery = ref('')
const roleFilter = ref<UserRole | null>(null)
const currentPage = ref(1)
const pageSize = ref(20)

const isCreateDialogOpen = ref(false)
const isEditDialogOpen = ref(false)
const isProfileDialogOpen = ref(false)
const isDeleteDialogOpen = ref(false)
const selectedUser = ref<User | null>(null)

let searchTimeout: ReturnType<typeof setTimeout> | null = null

// Computed: count of pending users
const pendingCount = computed(() => {
  return adminStore.users.filter((u) => !u.is_active).length
})

onMounted(() => {
  fetchUsers()
})

async function fetchUsers() {
  const skip = (currentPage.value - 1) * pageSize.value
  await adminStore.fetchUsers({
    skip,
    limit: pageSize.value,
    search: searchQuery.value || undefined,
    role: roleFilter.value || undefined,
  })
}

function debouncedSearch() {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    fetchUsers()
  }, 300)
}

function previousPage() {
  if (currentPage.value > 1) {
    currentPage.value--
    fetchUsers()
  }
}

function nextPage() {
  if (currentPage.value * pageSize.value < adminStore.totalUsers) {
    currentPage.value++
    fetchUsers()
  }
}

function getRoleLabel(role: UserRole): string {
  const labels = {
    [UserRole.SUPER_ADMIN]: 'Super Admin',
    [UserRole.ADMIN]: 'Admin',
    [UserRole.USER]: 'User',
    [UserRole.GUEST]: 'Guest',
  }
  return labels[role]
}

function getRoleBadgeClass(role: UserRole): string {
  const classes = {
    [UserRole.SUPER_ADMIN]: 'bg-purple-100 text-purple-800',
    [UserRole.ADMIN]: 'bg-blue-100 text-blue-800',
    [UserRole.USER]: 'bg-green-100 text-green-800',
    [UserRole.GUEST]: 'bg-gray-100 text-gray-800',
  }
  return classes[role]
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString()
}

// Dialog handlers
function openCreateDialog() {
  isCreateDialogOpen.value = true
}

function closeCreateDialog() {
  isCreateDialogOpen.value = false
}

async function handleCreateUser(userData: UserAdminCreate) {
  try {
    await adminStore.createUser(userData)
    closeCreateDialog()
    fetchUsers()
  } catch (err) {
    // Error is handled by the store
  }
}

function openEditDialog(user: User) {
  selectedUser.value = user
  isEditDialogOpen.value = true
}

function closeEditDialog() {
  isEditDialogOpen.value = false
  selectedUser.value = null
}

function openProfileDialog(user: User) {
  selectedUser.value = user
  isProfileDialogOpen.value = true
}

function closeProfileDialog() {
  isProfileDialogOpen.value = false
  selectedUser.value = null
}

async function handleUpdateUser(userId: number, userData: UserAdminUpdate) {
  try {
    await adminStore.updateUser(userId, userData)
    closeEditDialog()
    closeProfileDialog()
    fetchUsers()
  } catch (err) {
    // Error is handled by the store
  }
}

function openDeleteDialog(user: User) {
  selectedUser.value = user
  isDeleteDialogOpen.value = true
}

function closeDeleteDialog() {
  isDeleteDialogOpen.value = false
  selectedUser.value = null
}

async function handleDeleteUser(userId: number) {
  try {
    await adminStore.deleteUser(userId)
    closeDeleteDialog()
    fetchUsers()
  } catch (err) {
    // Error is handled by the store
  }
}

async function approveUser(user: User) {
  if (confirm(`Approve user ${user.email}?`)) {
    try {
      await adminStore.updateUser(user.id, { is_active: true })
      fetchUsers()
    } catch (err) {
      // Error is handled by the store
    }
  }
}
</script>
