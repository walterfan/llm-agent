import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Home from '@/views/Home.vue'
import SignIn from '@/views/auth/SignIn.vue'
import SignUp from '@/views/auth/SignUp.vue'
import UserProfile from '@/views/user/UserProfile.vue'
import Weather from '@/views/Weather.vue'
import Recommendations from '@/views/Recommendations.vue'
import ProfileEditor from '@/views/user/ProfileEditor.vue'
import EmailPreferences from '@/views/EmailPreferences.vue'
import Secretary from '@/views/Secretary.vue'
import Learning from '@/views/Learning.vue'
import MedicalPaper from '@/views/MedicalPaper.vue'
import Translation from '@/views/Translation.vue'
import PhilosophyMaster from '@/views/PhilosophyMaster.vue'
import Coach from '@/views/Coach.vue'
import KnowledgeBase from '@/views/KnowledgeBase.vue'
import LearningPlan from '@/views/LearningPlan.vue'
import CalculatorTool from '@/views/tools/CalculatorTool.vue'
import DateTimeTool from '@/views/tools/DateTimeTool.vue'
import NotesTool from '@/views/tools/NotesTool.vue'
import TasksTool from '@/views/tools/TasksTool.vue'
import RemindersTool from '@/views/tools/RemindersTool.vue'
import AgentFactory from '@/views/AgentFactory.vue'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'home',
    component: Home,
    meta: { requiresAuth: false },
  },
  {
    path: '/signin',
    name: 'signin',
    component: SignIn,
    meta: { requiresAuth: false, guestOnly: true },
  },
  {
    path: '/signup',
    name: 'signup',
    component: SignUp,
    meta: { requiresAuth: false, guestOnly: true },
  },
  {
    path: '/profile',
    name: 'profile',
    component: UserProfile,
    meta: { requiresAuth: true },
  },
  {
    path: '/profile/edit',
    name: 'profile-edit',
    component: ProfileEditor,
    meta: { requiresAuth: true },
  },
  {
    path: '/profile/email-preferences',
    name: 'email-preferences',
    component: EmailPreferences,
    meta: { requiresAuth: true },
  },
  {
    path: '/admin/users',
    name: 'user-management',
    component: () => import('@/views/admin/UserManagement.vue'),
    meta: { requiresAuth: true, requiresSuperAdmin: true },
  },
  {
    path: '/admin/email-management',
    name: 'admin-email-management',
    component: () => import('@/views/admin/AdminEmailManagement.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/admin/scheduler',
    name: 'admin-scheduler',
    component: () => import('@/views/admin/JobScheduler.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/admin/llm-settings',
    name: 'admin-llm-settings',
    component: () => import('@/views/admin/LLMSettings.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/rbac/roles',
    name: 'role-management',
    component: () => import('@/views/rbac/RoleManagement.vue'),
    meta: { requiresAuth: true, requiresSuperAdmin: true },
  },
  {
    path: '/rbac/permissions',
    name: 'permission-management',
    component: () => import('@/views/rbac/PermissionManagement.vue'),
    meta: { requiresAuth: true, requiresSuperAdmin: true },
  },
  {
    path: '/weather',
    name: 'weather',
    component: Weather,
    meta: { requiresAuth: true },
  },
  {
    path: '/recommendations',
    name: 'recommendations',
    component: Recommendations,
    meta: { requiresAuth: true },
  },
  {
    path: '/secretary',
    name: 'secretary',
    component: Secretary,
    meta: { requiresAuth: true },
  },
  {
    path: '/learning',
    name: 'learning',
    component: Learning,
    meta: { requiresAuth: true },
  },
  {
    path: '/medical-paper',
    name: 'medical-paper',
    component: MedicalPaper,
    meta: { requiresAuth: true },
  },
  {
    path: '/translation',
    name: 'translation',
    component: Translation,
    meta: { requiresAuth: true },
  },
  {
    path: '/philosophy',
    name: 'philosophy-master',
    component: PhilosophyMaster,
    meta: { requiresAuth: true },
  },
  // AI Coach
  {
    path: '/coach',
    name: 'coach',
    component: Coach,
    meta: { requiresAuth: true },
  },
  {
    path: '/knowledge',
    name: 'knowledge-base',
    component: KnowledgeBase,
    meta: { requiresAuth: true },
  },
  {
    path: '/learning-plan',
    name: 'learning-plan',
    component: LearningPlan,
    meta: { requiresAuth: true },
  },
  // AI Agent Factory
  {
    path: '/factory',
    name: 'agent-factory',
    component: AgentFactory,
    meta: { requiresAuth: true },
  },
  // Tool pages
  {
    path: '/tools/calculator',
    name: 'calculator-tool',
    component: CalculatorTool,
    meta: { requiresAuth: true },
  },
  {
    path: '/tools/datetime',
    name: 'datetime-tool',
    component: DateTimeTool,
    meta: { requiresAuth: true },
  },
  {
    path: '/tools/notes',
    name: 'notes-tool',
    component: NotesTool,
    meta: { requiresAuth: true },
  },
  {
    path: '/tools/tasks',
    name: 'tasks-tool',
    component: TasksTool,
    meta: { requiresAuth: true },
  },
  {
    path: '/tools/reminders',
    name: 'reminders-tool',
    component: RemindersTool,
    meta: { requiresAuth: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFound.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

// Navigation guard for authentication and authorization
router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.meta.requiresAuth
  const guestOnly = to.meta.guestOnly
  const requiresSuperAdmin = to.meta.requiresSuperAdmin
  const requiresAdmin = to.meta.requiresAdmin

  if (requiresAuth && !authStore.isAuthenticated) {
    // Redirect to signin if route requires auth and user is not authenticated
    next({ name: 'signin', query: { redirect: to.fullPath } })
  } else if (guestOnly && authStore.isAuthenticated) {
    // Redirect to profile if route is for guests only and user is authenticated
    next({ name: 'profile' })
  } else if (requiresSuperAdmin && !authStore.isSuperAdmin) {
    // Redirect to home if route requires super_admin role and user doesn't have it
    next({ name: 'home' })
  } else if (requiresAdmin && !authStore.isAdmin) {
    // Redirect to home if route requires admin role and user doesn't have it
    next({ name: 'home' })
  } else {
    next()
  }
})

export default router
