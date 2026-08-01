<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/components/layout/AppLayout.vue'
import InputField from '@/components/forms/InputField.vue'
import ButtonComponent from '@/components/forms/ButtonComponent.vue'
import { validateEmail, validatePassword, validateFullName } from '@/utils/validators'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const fullName = ref('')
const emailError = ref<string | null>(null)
const passwordError = ref<string | null>(null)
const fullNameError = ref<string | null>(null)
const serverError = ref<string | null>(null)
const pendingApproval = ref(false)

const isFormValid = computed(() => {
  return (
    email.value &&
    password.value &&
    !emailError.value &&
    !passwordError.value &&
    !fullNameError.value
  )
})

const validateForm = () => {
  emailError.value = validateEmail(email.value)
  passwordError.value = validatePassword(password.value)
  fullNameError.value = validateFullName(fullName.value)
  return !emailError.value && !passwordError.value && !fullNameError.value
}

const handleSubmit = async () => {
  serverError.value = null
  pendingApproval.value = false

  if (!validateForm()) {
    return
  }

  try {
    await authStore.signup({
      email: email.value,
      password: password.value,
      full_name: fullName.value || undefined,
    })

    router.push('/profile')
  } catch (error: any) {
    const errorMessage = error.message || ''
    // Check if the error is about account pending approval
    if (
      errorMessage.toLowerCase().includes('inactive') &&
      errorMessage.toLowerCase().includes('pending')
    ) {
      pendingApproval.value = true
    } else {
      serverError.value = errorMessage || 'Signup failed. Please try again.'
    }
  }
}
</script>

<template>
  <AppLayout>
    <div class="flex min-h-full flex-col justify-center px-6 py-12 lg:px-8">
      <div class="sm:mx-auto sm:w-full sm:max-w-md">
        <h2 class="text-center text-3xl font-bold tracking-tight text-gray-900">
          Create your account
        </h2>
        <p class="mt-2 text-center text-sm text-gray-600">
          Already have an account?
          <RouterLink to="/signin" class="font-medium text-primary-600 hover:text-primary-500">
            Sign in
          </RouterLink>
        </p>
      </div>

      <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div class="bg-white px-6 py-8 shadow sm:rounded-lg sm:px-10">
          <!-- Pending Approval Notice -->
          <div v-if="pendingApproval" class="rounded-md bg-blue-50 border border-blue-200 p-4 mb-6">
            <div class="flex">
              <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fill-rule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                    clip-rule="evenodd"
                  />
                </svg>
              </div>
              <div class="ml-3">
                <h3 class="text-sm font-medium text-blue-800">Account Created Successfully!</h3>
                <div class="mt-2 text-sm text-blue-700">
                  <p>Your account has been created and is pending approval by an administrator.</p>
                  <p class="mt-2">
                    Please contact the administrator to activate your account. Once approved, you'll
                    be able to sign in.
                  </p>
                </div>
                <div class="mt-4">
                  <RouterLink
                    to="/signin"
                    class="text-sm font-medium text-blue-600 hover:text-blue-500"
                  >
                    Go to Sign In →
                  </RouterLink>
                </div>
              </div>
            </div>
          </div>

          <form v-if="!pendingApproval" class="space-y-6" @submit.prevent="handleSubmit">
            <div v-if="serverError" class="rounded-md bg-red-50 p-4">
              <p class="text-sm text-red-800">
                {{ serverError }}
              </p>
            </div>

            <InputField
              v-model="email"
              label="Email"
              type="email"
              placeholder="you@example.com"
              :error="emailError"
              required
              @blur="emailError = validateEmail(email)"
            />

            <InputField
              v-model="fullName"
              label="Full Name"
              type="text"
              placeholder="John Doe"
              :error="fullNameError"
              @blur="fullNameError = validateFullName(fullName)"
            />

            <InputField
              v-model="password"
              label="Password"
              type="password"
              placeholder="••••••••"
              :error="passwordError"
              required
              @blur="passwordError = validatePassword(password)"
            />

            <ButtonComponent
              type="submit"
              :disabled="!isFormValid || authStore.loading"
              :loading="authStore.loading"
              full-width
            >
              Sign up
            </ButtonComponent>
          </form>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
