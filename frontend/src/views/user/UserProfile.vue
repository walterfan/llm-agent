<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/components/layout/AppLayout.vue'
import InputField from '@/components/forms/InputField.vue'
import ButtonComponent from '@/components/forms/ButtonComponent.vue'
import { validateFullName } from '@/utils/validators'

const router = useRouter()
const authStore = useAuthStore()

const fullName = ref('')
const fullNameError = ref<string | null>(null)
const serverError = ref<string | null>(null)
const successMessage = ref<string | null>(null)
const isEditing = ref(false)

// Change password state
const isChangingPassword = ref(false)
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const currentPasswordError = ref<string | null>(null)
const newPasswordError = ref<string | null>(null)
const confirmPasswordError = ref<string | null>(null)
const passwordServerError = ref<string | null>(null)
const passwordSuccessMessage = ref<string | null>(null)
const isPasswordLoading = ref(false)

onMounted(() => {
  if (authStore.currentUser) {
    fullName.value = authStore.currentUser.full_name || ''
  }
})

const startEditing = () => {
  isEditing.value = true
  serverError.value = null
  successMessage.value = null
}

const cancelEditing = () => {
  isEditing.value = false
  if (authStore.currentUser) {
    fullName.value = authStore.currentUser.full_name || ''
  }
  fullNameError.value = null
}

const handleUpdateProfile = async () => {
  serverError.value = null
  successMessage.value = null

  fullNameError.value = validateFullName(fullName.value)
  if (fullNameError.value) {
    return
  }

  try {
    await authStore.updateProfile({
      full_name: fullName.value || undefined,
    })
    successMessage.value = 'Profile updated successfully!'
    isEditing.value = false
  } catch (error: any) {
    serverError.value = error.message || 'Update failed. Please try again.'
  }
}

const handleDeleteAccount = async () => {
  if (!confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
    return
  }

  try {
    await authStore.logout()
    router.push('/')
  } catch (error: any) {
    serverError.value = error.message || 'Delete failed. Please try again.'
  }
}

// Change password methods
const startChangingPassword = () => {
  isChangingPassword.value = true
  passwordServerError.value = null
  passwordSuccessMessage.value = null
  currentPassword.value = ''
  newPassword.value = ''
  confirmPassword.value = ''
}

const cancelChangingPassword = () => {
  isChangingPassword.value = false
  currentPassword.value = ''
  newPassword.value = ''
  confirmPassword.value = ''
  currentPasswordError.value = null
  newPasswordError.value = null
  confirmPasswordError.value = null
  passwordServerError.value = null
}

const validatePassword = (password: string): string | null => {
  if (!password) {
    return 'Password is required'
  }
  if (password.length < 8) {
    return 'Password must be at least 8 characters'
  }
  return null
}

const handleChangePassword = async () => {
  passwordServerError.value = null
  passwordSuccessMessage.value = null

  // Validate all fields
  currentPasswordError.value = !currentPassword.value ? 'Current password is required' : null
  newPasswordError.value = validatePassword(newPassword.value)
  confirmPasswordError.value = null

  if (!confirmPassword.value) {
    confirmPasswordError.value = 'Please confirm your new password'
  } else if (newPassword.value !== confirmPassword.value) {
    confirmPasswordError.value = 'Passwords do not match'
  }

  if (currentPasswordError.value || newPasswordError.value || confirmPasswordError.value) {
    return
  }

  isPasswordLoading.value = true
  try {
    await authStore.changePassword({
      current_password: currentPassword.value,
      new_password: newPassword.value,
    })
    passwordSuccessMessage.value = 'Password changed successfully!'
    isChangingPassword.value = false
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
  } catch (error: any) {
    passwordServerError.value = error.message || 'Failed to change password. Please try again.'
  } finally {
    isPasswordLoading.value = false
  }
}
</script>

<template>
  <AppLayout>
    <div class="mx-auto max-w-2xl">
      <h1 class="text-3xl font-bold tracking-tight text-gray-900 mb-8">User Profile</h1>

      <div class="bg-white shadow sm:rounded-lg">
        <div class="px-4 py-5 sm:p-6">
          <div v-if="successMessage" class="mb-4 rounded-md bg-green-50 p-4">
            <p class="text-sm text-green-800">
              {{ successMessage }}
            </p>
          </div>

          <div v-if="serverError" class="mb-4 rounded-md bg-red-50 p-4">
            <p class="text-sm text-red-800">
              {{ serverError }}
            </p>
          </div>

          <div class="space-y-6">
            <div>
              <label class="block text-sm font-medium text-gray-700">Email</label>
              <p class="mt-1 text-sm text-gray-900">
                {{ authStore.currentUser?.email }}
              </p>
              <p class="mt-1 text-xs text-gray-500">Email cannot be changed</p>
            </div>

            <div v-if="!isEditing">
              <label class="block text-sm font-medium text-gray-700">Full Name</label>
              <p class="mt-1 text-sm text-gray-900">
                {{ authStore.currentUser?.full_name || 'Not set' }}
              </p>
            </div>

            <InputField
              v-if="isEditing"
              v-model="fullName"
              label="Full Name"
              type="text"
              placeholder="John Doe"
              :error="fullNameError"
              @blur="fullNameError = validateFullName(fullName)"
            />

            <div>
              <label class="block text-sm font-medium text-gray-700">Member Since</label>
              <p class="mt-1 text-sm text-gray-900">
                {{ new Date(authStore.currentUser?.created_at || '').toLocaleDateString() }}
              </p>
            </div>

            <div class="flex gap-3">
              <ButtonComponent v-if="!isEditing" @click="startEditing">
                Edit User Profile
              </ButtonComponent>

              <template v-if="isEditing">
                <ButtonComponent :loading="authStore.loading" @click="handleUpdateProfile">
                  Save Changes
                </ButtonComponent>
                <ButtonComponent variant="secondary" @click="cancelEditing">
                  Cancel
                </ButtonComponent>
              </template>
            </div>
          </div>
        </div>

        <!-- Change Password Section -->
        <div class="border-t border-gray-200 px-4 py-5 sm:p-6">
          <h3 class="text-lg font-medium text-gray-900 mb-4">Change Password</h3>

          <div v-if="passwordSuccessMessage" class="mb-4 rounded-md bg-green-50 p-4">
            <p class="text-sm text-green-800">
              {{ passwordSuccessMessage }}
            </p>
          </div>

          <div v-if="passwordServerError" class="mb-4 rounded-md bg-red-50 p-4">
            <p class="text-sm text-red-800">
              {{ passwordServerError }}
            </p>
          </div>

          <div v-if="!isChangingPassword">
            <p class="text-sm text-gray-600 mb-4">
              Update your password to keep your account secure.
            </p>
            <ButtonComponent @click="startChangingPassword"> Change Password </ButtonComponent>
          </div>

          <div v-else class="space-y-4">
            <InputField
              v-model="currentPassword"
              label="Current Password"
              type="password"
              placeholder="Enter your current password"
              :error="currentPasswordError"
              @blur="
                currentPasswordError = !currentPassword ? 'Current password is required' : null
              "
            />

            <InputField
              v-model="newPassword"
              label="New Password"
              type="password"
              placeholder="Enter your new password (min. 8 characters)"
              :error="newPasswordError"
              @blur="newPasswordError = validatePassword(newPassword)"
            />

            <InputField
              v-model="confirmPassword"
              label="Confirm New Password"
              type="password"
              placeholder="Confirm your new password"
              :error="confirmPasswordError"
              @blur="
                confirmPasswordError =
                  newPassword !== confirmPassword ? 'Passwords do not match' : null
              "
            />

            <div class="flex gap-3">
              <ButtonComponent :loading="isPasswordLoading" @click="handleChangePassword">
                Update Password
              </ButtonComponent>
              <ButtonComponent variant="secondary" @click="cancelChangingPassword">
                Cancel
              </ButtonComponent>
            </div>
          </div>
        </div>

        <div class="border-t border-gray-200 px-4 py-5 sm:p-6">
          <h3 class="text-lg font-medium text-gray-900 mb-2">Danger Zone</h3>
          <p class="text-sm text-gray-600 mb-4">
            Once you delete your account, there is no going back. Please be certain.
          </p>
          <ButtonComponent variant="danger" @click="handleDeleteAccount">
            Delete Account
          </ButtonComponent>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
