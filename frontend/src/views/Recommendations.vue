<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useRecommendationStore } from '@/stores/recommendation'
import { useAdminRecommendationStore } from '@/stores/adminRecommendation'
import { useEmailStore } from '@/stores/email'
import AppLayout from '@/components/layout/AppLayout.vue'
import CitySearch from '@/components/weather/CitySearch.vue'
import RecommendationCard from '@/components/recommendations/RecommendationCard.vue'
import StreamingTextDisplay from '@/components/recommendations/StreamingTextDisplay.vue'
import MultiDayDisplay from '@/components/recommendations/MultiDayDisplay.vue'
import UserSelector from '@/components/admin/UserSelector.vue'
import type { City } from '@/types/city'
import type { UserBasicInfo } from '@/types/recommendation'

const router = useRouter()
const authStore = useAuthStore()
const recommendationStore = useRecommendationStore()
const adminRecommendationStore = useAdminRecommendationStore()
const emailStore = useEmailStore()

// Local state
const selectedCity = ref<City | null>(null)
const selectedUser = ref<UserBasicInfo | null>(null)
const useStreaming = ref(true) // Toggle between streaming and non-streaming
const selectedDays = ref<1 | 2 | 3>(1)
const showEmailForm = ref(false)
const emailRecipients = ref('')
const emailSuccess = ref<string | null>(null)
const emailError = ref<string | null>(null)
const showSuccessNotification = ref<boolean>(false)
const successMessage = ref<string>('')
const streamingDayTab = ref(0)

watch(
  () => recommendationStore.streamingCurrentDayIndex,
  () => {
    // Keep UI tab in sync with whichever day the backend is currently streaming
    streamingDayTab.value = recommendationStore.streamingCurrentDayIndex
  }
)

// Quick select cities
const quickCities = [
  { name: '长沙', name_en: 'Changsha', ad_code: '430100' },
  { name: '合肥', name_en: 'Hefei', ad_code: '340100' },
  { name: '北京', name_en: 'Beijing', ad_code: '110000' },
  { name: '上海', name_en: 'Shanghai', ad_code: '310000' },
]

// Computed
const isAdmin = computed(() => {
  const role = authStore.user?.role
  return role === 'super_admin' || role === 'admin'
})

const hasProfile = computed(() => {
  const user = authStore.user
  return !!(
    user?.gender ||
    user?.age ||
    user?.identity ||
    user?.style ||
    user?.temperature_sensitivity
  )
})

const isAdminMode = computed(() => {
  return isAdmin.value && selectedUser.value !== null
})

const canGenerate = computed(() => {
  return selectedCity.value !== null
})

const emailPreviewSubject = computed(() => {
  const rec = recommendationStore.currentRecommendation

  // Use the resolved city name from the generated recommendation if available
  const cityName =
    rec?.city ||
    selectedCity.value?.display_name ||
    selectedCity.value?.location_name_zh ||
    selectedCity.value?.ad_code ||
    ''

  // Get actual number of days from recommendations, fallback to selected days
  const days = rec?.recommendations?.length || selectedDays.value

  if (!cityName) {
    return ''
  }

  const daysLabel = days === 1 ? '今天' : days === 2 ? '未来2天' : '未来3天'
  return `${daysLabel}穿衣推荐 - ${cityName}`
})

const emailPreviewBody = computed(() => {
  const rec = recommendationStore.currentRecommendation
  const userName = authStore.user?.full_name || authStore.user?.email || '用户'

  if (!rec || !rec.recommendations || rec.recommendations.length === 0) {
    return '请先生成穿衣推荐，然后再发送邮件。'
  }

  const days = rec.recommendations.length
  const daysLabel = days === 1 ? '今天' : days === 2 ? '未来2天' : '未来3天'
  const cityName =
    rec.city || selectedCity.value?.display_name || selectedCity.value?.location_name_zh || ''

  let body = `亲爱的${userName}，\n\n这是您在${cityName}的${daysLabel}穿搭推荐：\n\n`

  for (const day of rec.recommendations) {
    const items = day.recommendation?.clothing_items?.join(', ') || '暂无推荐'
    const advice = day.recommendation?.advice || '请根据天气情况选择合适的衣物。'
    body += `--- ${day.date_label} (${day.date}) ---\n`
    body += `天气概况: ${day.weather_summary || '暂无天气信息'}\n`
    body += `推荐穿搭: ${items}\n`
    body += `穿衣建议: ${advice}\n\n`
  }

  body += `此致，\n穿搭推荐助手\n`
  return body
})

// Load recommendations on mount
onMounted(async () => {
  if (authStore.isAuthenticated) {
    await recommendationStore.listRecommendations()
  }
})

// Handle city selection
function handleCitySelect(city: City) {
  selectedCity.value = city
}

// Handle user selection (admin only)
function handleUserSelect(user: UserBasicInfo | null) {
  selectedUser.value = user
}

// Handle quick select
function handleQuickSelect(quickCity: { name: string; name_en: string; ad_code: string }) {
  const city: City = {
    location_id: quickCity.ad_code,
    location_name_zh: quickCity.name,
    location_name_en: quickCity.name_en,
    ad_code: quickCity.ad_code,
    display_name: `${quickCity.name_en} (${quickCity.name})`,
  }
  selectedCity.value = city
}

// Generate recommendation
async function generateRecommendation() {
  if (!selectedCity.value) {
    alert('Please select a city first')
    return
  }

  if (!hasProfile.value && !isAdminMode.value) {
    if (confirm("You haven't set up your dress preferences yet. Would you like to do that now?")) {
      router.push('/profile/edit')
      return
    }
  }

  // Admin generating for another user (multi-day)
  if (isAdminMode.value && selectedUser.value) {
    try {
      await adminRecommendationStore.generateForUser({
        user_id: selectedUser.value.id,
        city_code: selectedCity.value.ad_code,
        send_email: false,
      })
      showNotification('成功生成3天穿衣推荐！')
    } catch (error: any) {
      console.error('Failed to generate admin recommendations:', error)
      alert(`生成推荐失败: ${adminRecommendationStore.error || error.message}`)
    }
    return
  }

  // Regular user or admin generating for themselves
  recommendationStore.clearCurrentRecommendation()

  if (useStreaming.value) {
    // Use streaming API
    try {
      await recommendationStore.generateRecommendationStream(
        selectedCity.value.ad_code,
        authStore.token || '',
        undefined,
        selectedDays.value
      )
    } catch (err) {
      console.error('Streaming error:', err)
    }
  } else {
    // Use non-streaming API
    try {
      await recommendationStore.generateRecommendation({
        city: selectedCity.value.ad_code,
        days: isAdminMode.value ? 3 : selectedDays.value,
      })
    } catch (err) {
      console.error('Generation error:', err)
    }
  }
}

// Send email for admin multi-day recommendations
async function handleSendAdminEmail() {
  if (!isAdminMode.value || !selectedUser.value || !selectedCity.value) return

  const confirmed = confirm('确定要发送3天推荐邮件给该用户吗？')
  if (!confirmed) return

  try {
    await adminRecommendationStore.generateForUser({
      user_id: selectedUser.value.id,
      city_code: selectedCity.value.ad_code,
      send_email: true,
    })
    showNotification('邮件发送成功！')
  } catch (error: any) {
    console.error('Failed to send email:', error)
    alert(`邮件发送失败: ${adminRecommendationStore.error || error.message}`)
  }
}

// Navigate to profile editor
function goToProfileEditor() {
  router.push('/profile/edit')
}

// Email sending (regular user)
function toggleEmailForm() {
  showEmailForm.value = !showEmailForm.value
  emailError.value = null
  emailSuccess.value = null
}

function validateEmails(emails: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  const emailList = emails
    .split(',')
    .map((e) => e.trim())
    .filter((e) => e)
  return emailList.length > 0 && emailList.every((e) => emailRegex.test(e))
}

async function sendEmail() {
  if (!selectedCity.value) {
    emailError.value = 'Please select a city first'
    return
  }

  const recipients = emailRecipients.value
    .split(',')
    .map((e) => e.trim())
    .filter((e) => e)
  if (recipients.length === 0) {
    emailError.value = 'Please enter at least one email address'
    return
  }

  if (!validateEmails(emailRecipients.value)) {
    emailError.value = 'Please enter valid email addresses (comma-separated)'
    return
  }

  emailError.value = null
  emailSuccess.value = null

  try {
    const response = await emailStore.sendEmail({
      city: selectedCity.value.ad_code,
      recipient_emails: recipients,
    })

    if (response.success) {
      emailSuccess.value = response.message
      emailRecipients.value = ''
      setTimeout(() => {
        showEmailForm.value = false
        emailSuccess.value = null
      }, 3000)
    } else {
      emailError.value = response.message
    }
  } catch (err: any) {
    emailError.value = err.message || 'Failed to send email'
  }
}

function showNotification(message: string) {
  successMessage.value = message
  showSuccessNotification.value = true
  setTimeout(() => {
    showSuccessNotification.value = false
  }, 3000)
}

function handleClearAdminRecommendations() {
  const confirmed = confirm('确定要清除当前推荐结果吗？')
  if (confirmed) {
    adminRecommendationStore.clearRecommendations()
    selectedUser.value = null
  }
}
</script>

<template>
  <AppLayout>
    <div
      class="recommendations-page min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4"
    >
      <div class="max-w-6xl mx-auto">
        <!-- Header -->
        <div class="text-center mb-8">
          <h1 class="text-4xl font-bold text-gray-900 mb-2">🤖 Lazy Rabbit AI Agents</h1>
          <p class="text-gray-600">
            {{
              isAdminMode
                ? '为指定用户生成未来三天的穿衣建议（今天、明天、后天）'
                : 'Get personalized clothing suggestions based on weather and your preferences'
            }}
          </p>
        </div>

        <!-- Profile Warning (for regular users only) -->
        <div
          v-if="!hasProfile && !isAdminMode"
          class="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-8 flex items-start"
        >
          <svg class="w-5 h-5 text-yellow-600 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
            <path
              fill-rule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clip-rule="evenodd"
            />
          </svg>
          <div class="flex-1">
            <p class="text-yellow-800 font-medium">Profile not set up</p>
            <p class="text-yellow-700 text-sm mt-1">
              For better recommendations, please set up your dress preferences first.
            </p>
            <button
              class="mt-2 text-yellow-800 font-medium hover:underline"
              @click="goToProfileEditor"
            >
              Set up profile →
            </button>
          </div>
        </div>

        <!-- Input Section -->
        <div class="bg-white rounded-xl shadow-md p-6 mb-8">
          <div class="flex justify-between items-center mb-4">
            <label class="block text-sm font-medium text-gray-700">
              {{ isAdminMode ? '生成推荐' : 'Select City' }}
            </label>
            <div v-if="!isAdminMode" class="flex items-center space-x-4">
              <!-- Days Selector -->
              <div class="flex items-center gap-2">
                <span class="text-sm text-gray-600">Days:</span>
                <select
                  v-model="selectedDays"
                  class="border border-gray-300 rounded-md px-2 py-1 text-sm bg-white"
                >
                  <option :value="1">1</option>
                  <option :value="2">2</option>
                  <option :value="3">3</option>
                </select>
              </div>

              <!-- Streaming Toggle (only for regular mode) -->
              <label class="flex items-center cursor-pointer">
                <input v-model="useStreaming" type="checkbox" class="sr-only peer" />
                <div
                  class="relative w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"
                />
                <span class="ml-3 text-sm font-medium text-gray-700">
                  {{ useStreaming ? '⚡ Streaming Mode' : '📦 Normal Mode' }}
                </span>
              </label>
            </div>
          </div>

          <div class="space-y-6">
            <!-- User Selector (Admin Only) -->
            <div v-if="isAdmin">
              <UserSelector @select="handleUserSelect" />
              <p v-if="selectedUser" class="mt-2 text-sm text-blue-600">
                已选择用户:
                <span class="font-medium">{{ selectedUser.full_name || selectedUser.email }}</span>
              </p>
              <p v-else class="mt-2 text-sm text-gray-500">💡 提示: 不选择用户将为您自己生成推荐</p>
            </div>

            <!-- City Selector -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2"> 选择城市 </label>
              <CitySearch @select="handleCitySelect" />

              <!-- Quick Select Tags -->
              <div class="mt-4">
                <p class="text-xs text-gray-500 mb-2">Quick select:</p>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="city in quickCities"
                    :key="city.ad_code"
                    type="button"
                    class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-full transition-colors"
                    :class="
                      selectedCity?.ad_code === city.ad_code
                        ? 'bg-blue-600 text-white'
                        : 'bg-blue-50 text-blue-700 hover:bg-blue-100'
                    "
                    @click="handleQuickSelect(city)"
                  >
                    <span class="mr-1">📍</span>
                    {{ city.name }}
                    <span v-if="city.name_en" class="ml-1 text-xs opacity-75">{{
                      city.name_en
                    }}</span>
                  </button>
                </div>
              </div>

              <div v-if="selectedCity" class="mt-4 text-sm text-gray-600">
                Selected: <span class="font-medium">{{ selectedCity.display_name }}</span>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="flex space-x-4">
              <button
                :disabled="
                  !canGenerate ||
                  recommendationStore.loading ||
                  recommendationStore.isStreaming ||
                  adminRecommendationStore.loading
                "
                class="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-lg transition-colors flex items-center justify-center"
                @click="generateRecommendation"
              >
                <svg
                  v-if="
                    recommendationStore.loading ||
                    recommendationStore.isStreaming ||
                    adminRecommendationStore.loading
                  "
                  class="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    class="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    stroke-width="4"
                  />
                  <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                {{
                  recommendationStore.isStreaming || adminRecommendationStore.loading
                    ? '⏳ 生成中...'
                    : recommendationStore.loading
                      ? '⏳ Loading...'
                      : isAdminMode
                        ? '✨ 生成3天推荐'
                        : '✨ Generate Recommendation'
                }}
              </button>

              <!-- Admin: Send Email Button -->
              <button
                v-if="isAdminMode && adminRecommendationStore.hasRecommendations"
                :disabled="adminRecommendationStore.loading"
                class="bg-green-600 hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-lg transition-colors flex items-center"
                @click="handleSendAdminEmail"
              >
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
                发送邮件
              </button>

              <!-- Admin: Clear Button -->
              <button
                v-if="isAdminMode && adminRecommendationStore.hasRecommendations"
                class="bg-gray-500 hover:bg-gray-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
                @click="handleClearAdminRecommendations"
              >
                清除
              </button>
            </div>
          </div>

          <!-- Error Display -->
          <div
            v-if="adminRecommendationStore.error"
            class="mt-4 bg-red-50 border-l-4 border-red-400 p-4 rounded"
          >
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
                <p class="text-sm text-red-700">
                  {{ adminRecommendationStore.error }}
                </p>
              </div>
              <div class="ml-auto">
                <button
                  class="text-red-400 hover:text-red-600"
                  @click="adminRecommendationStore.clearError()"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <!-- Send Email Section (Regular User) -->
          <div v-if="!isAdminMode" class="mt-6 pt-6 border-t border-gray-200">
            <button
              class="w-full text-left text-sm font-medium text-gray-700 hover:text-gray-900 flex items-center justify-between"
              @click="toggleEmailForm"
            >
              <span>📧 Send Recommendation via Email</span>
              <svg
                :class="['w-5 h-5 transition-transform', showEmailForm ? 'rotate-180' : '']"
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

            <div v-if="showEmailForm" class="mt-4 space-y-4">
              <!-- Email Preview -->
              <div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <h4 class="text-sm font-semibold text-gray-800 mb-3">Email Preview</h4>

                <div
                  v-if="!recommendationStore.currentRecommendation"
                  class="mb-3 p-3 bg-yellow-50 border border-yellow-200 rounded-md"
                >
                  <p class="text-sm text-yellow-800">⚠️ 请先生成穿衣推荐，预览将自动更新。</p>
                </div>

                <div class="mb-3">
                  <label class="block text-xs font-medium text-gray-600 mb-1">Subject</label>
                  <input
                    :value="emailPreviewSubject"
                    type="text"
                    readonly
                    :class="[
                      'w-full px-3 py-2 border rounded-md text-sm',
                      emailPreviewSubject
                        ? 'border-gray-300 bg-white'
                        : 'border-yellow-300 bg-yellow-50',
                    ]"
                    :placeholder="emailPreviewSubject ? '' : '生成推荐后自动生成主题'"
                  />
                </div>

                <div>
                  <label class="block text-xs font-medium text-gray-600 mb-1"
                    >Body (plain text)</label
                  >
                  <textarea
                    :value="emailPreviewBody"
                    readonly
                    rows="10"
                    :class="[
                      'w-full px-3 py-2 border rounded-md text-sm font-mono',
                      recommendationStore.currentRecommendation
                        ? 'border-gray-300 bg-white'
                        : 'border-yellow-300 bg-yellow-50',
                    ]"
                    :placeholder="
                      recommendationStore.currentRecommendation ? '' : '生成推荐后自动生成邮件内容'
                    "
                  />
                  <p class="mt-1 text-xs text-gray-500">
                    Preview is generated from the current recommendations shown on this page.
                  </p>
                </div>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  Email Recipients (comma-separated)
                </label>
                <input
                  v-model="emailRecipients"
                  type="text"
                  placeholder="email1@example.com, email2@example.com"
                  class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <p class="mt-1 text-xs text-gray-500">
                  Enter one or more email addresses separated by commas
                </p>
              </div>

              <div v-if="emailError" class="bg-red-50 border border-red-200 rounded-lg p-3">
                <p class="text-sm text-red-800">
                  {{ emailError }}
                </p>
              </div>

              <div v-if="emailSuccess" class="bg-green-50 border border-green-200 rounded-lg p-3">
                <p class="text-sm text-green-800">
                  {{ emailSuccess }}
                </p>
              </div>

              <button
                :disabled="!selectedCity || emailStore.sendingEmail || !emailRecipients.trim()"
                class="w-full bg-green-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                @click="sendEmail"
              >
                {{ emailStore.sendingEmail ? '⏳ Sending...' : '📧 Send Email' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Admin Multi-Day Recommendations Display -->
        <div v-if="isAdminMode && adminRecommendationStore.hasRecommendations">
          <div class="bg-white rounded-xl shadow-lg p-6 mb-4">
            <div class="flex items-center justify-between mb-4">
              <div>
                <h2 class="text-2xl font-bold text-gray-900">
                  {{ adminRecommendationStore.currentCity }} - 未来3天推荐
                </h2>
                <p class="text-gray-600 mt-1">
                  用户:
                  {{
                    adminRecommendationStore.currentUser?.full_name ||
                    adminRecommendationStore.currentUser?.email
                  }}
                </p>
              </div>
              <div
                v-if="adminRecommendationStore.emailSent"
                class="flex items-center text-green-600"
              >
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                <span class="text-sm font-medium">邮件已发送</span>
              </div>
            </div>
          </div>

          <MultiDayDisplay :daily-recommendations="adminRecommendationStore.dailyRecommendations" />
        </div>

        <!-- Streaming Display (Regular User) -->
        <div v-if="!isAdminMode && recommendationStore.isStreaming" class="mb-8">
          <div class="bg-white rounded-xl shadow-md p-6">
            <h3 class="text-xl font-semibold text-gray-900 mb-4">🤖 AI is thinking...</h3>

            <!-- Status -->
            <div v-if="recommendationStore.streamingStatus" class="mb-4">
              <div class="flex items-center text-blue-600">
                <svg
                  class="animate-spin h-5 w-5 mr-3"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    class="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    stroke-width="4"
                  />
                  <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                <span class="text-sm">{{ recommendationStore.streamingStatus }}</span>
              </div>
            </div>

            <!-- 3-day streaming: tabs + per-day text -->
            <div v-if="recommendationStore.streamingDays.length > 0">
              <div class="flex gap-2 mb-4">
                <button
                  v-for="d in recommendationStore.streamingDays"
                  :key="d.index"
                  type="button"
                  class="px-3 py-1.5 rounded-full text-sm font-medium transition-colors"
                  :class="
                    streamingDayTab === d.index
                      ? 'bg-blue-600 text-white'
                      : 'bg-blue-50 text-blue-700 hover:bg-blue-100'
                  "
                  @click="streamingDayTab = d.index"
                >
                  {{ d.label || `Day ${d.index + 1}` }}
                </button>
              </div>

              <div class="bg-blue-50 rounded-lg p-4 mb-4">
                <h4 class="font-semibold text-gray-800 mb-2">Weather</h4>
                <div class="text-sm text-gray-700">
                  <div>
                    <span class="text-gray-600">Date:</span>
                    <span class="ml-2 font-medium">{{
                      recommendationStore.streamingDays[streamingDayTab]?.date
                    }}</span>
                  </div>
                  <div class="mt-1">
                    <span class="text-gray-600">Summary:</span>
                    <span class="ml-2 font-medium">
                      {{ recommendationStore.streamingDays[streamingDayTab]?.weather_text }}
                      ({{ recommendationStore.streamingDays[streamingDayTab]?.temperature_low }}°C -
                      {{ recommendationStore.streamingDays[streamingDayTab]?.temperature_high }}°C)
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <h4 class="font-semibold text-gray-800 mb-2">Recommendation</h4>
                <StreamingTextDisplay
                  :text="recommendationStore.streamingDays[streamingDayTab]?.text || ''"
                  :is-streaming="true"
                />
              </div>
            </div>

            <!-- single-day streaming fallback -->
            <div v-else>
              <div
                v-if="recommendationStore.streamingWeather"
                class="bg-blue-50 rounded-lg p-4 mb-4"
              >
                <h4 class="font-semibold text-gray-800 mb-2">Weather</h4>
                <div class="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span class="text-gray-600">City:</span>
                    <span class="ml-2 font-medium">{{
                      recommendationStore.streamingWeather.city
                    }}</span>
                  </div>
                  <div>
                    <span class="text-gray-600">Temperature:</span>
                    <span class="ml-2 font-medium"
                      >{{ recommendationStore.streamingWeather.temperature }}°C</span
                    >
                  </div>
                </div>
              </div>

              <div v-if="recommendationStore.streamingText">
                <h4 class="font-semibold text-gray-800 mb-2">Recommendation</h4>
                <StreamingTextDisplay
                  :text="recommendationStore.streamingText"
                  :is-streaming="true"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Current 3-Day Recommendations (Regular User) -->
        <div
          v-if="
            !isAdminMode &&
            recommendationStore.currentRecommendation &&
            !recommendationStore.isStreaming
          "
        >
          <div class="bg-white rounded-xl shadow-lg p-6 mb-4">
            <div class="flex items-center justify-between mb-4">
              <div>
                <h2 class="text-2xl font-bold text-gray-900">
                  {{ recommendationStore.currentRecommendation.city }} - 未来3天推荐
                </h2>
                <p class="text-gray-600 mt-1">为您生成的个性化穿衣建议</p>
              </div>
            </div>
          </div>

          <MultiDayDisplay
            :daily-recommendations="recommendationStore.currentRecommendation.recommendations"
          />
        </div>

        <!-- Recommendations History (Regular User) -->
        <div v-if="!isAdminMode && recommendationStore.hasRecommendations" class="mt-12">
          <h2 class="text-2xl font-bold text-gray-900 mb-6">Recent Recommendations</h2>
          <div class="space-y-6">
            <RecommendationCard
              v-for="rec in recommendationStore.recommendations.slice(0, 5)"
              :key="rec.id"
              :recommendation="rec"
            />
          </div>
        </div>

        <!-- Empty State -->
        <div
          v-if="
            !isAdminMode &&
            !recommendationStore.hasRecommendations &&
            !recommendationStore.isStreaming &&
            !recommendationStore.currentRecommendation &&
            !adminRecommendationStore.hasRecommendations
          "
          class="bg-white rounded-xl shadow-md p-12 text-center"
        >
          <div class="text-6xl mb-4">🎨</div>
          <h2 class="text-2xl font-semibold text-gray-900 mb-2">No Recommendations Yet</h2>
          <p class="text-gray-600 mb-6">
            Select a city above and click "Generate Recommendation" to get started!
          </p>
        </div>

        <!-- Admin Empty State -->
        <div
          v-if="
            isAdminMode &&
            !adminRecommendationStore.hasRecommendations &&
            !adminRecommendationStore.loading
          "
          class="bg-white rounded-xl shadow-lg p-12 text-center"
        >
          <div class="text-6xl mb-4">🌤️</div>
          <h3 class="text-xl font-semibold text-gray-900 mb-2">选择用户和城市开始生成推荐</h3>
          <p class="text-gray-600">系统将为指定用户生成未来三天的穿衣建议</p>
        </div>

        <!-- Success Notification -->
        <Transition
          enter-active-class="transition ease-out duration-300"
          enter-from-class="transform opacity-0 translate-y-2"
          enter-to-class="transform opacity-100 translate-y-0"
          leave-active-class="transition ease-in duration-200"
          leave-from-class="transform opacity-100 translate-y-0"
          leave-to-class="transform opacity-0 translate-y-2"
        >
          <div
            v-if="showSuccessNotification"
            class="fixed bottom-4 right-4 bg-green-500 text-white px-6 py-4 rounded-lg shadow-lg flex items-center z-50"
          >
            <svg class="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span class="font-medium">{{ successMessage }}</span>
          </div>
        </Transition>
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
.recommendations-page {
  min-height: calc(100vh - 64px);
}
</style>
