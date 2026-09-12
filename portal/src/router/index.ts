import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { initSession, authSession } from '@/stores/authSession'

import LoginView from '@/views/auth/LoginView.vue'
import SignUpView from '@/views/auth/SignUpView.vue'
import ForgotPasswordView from '@/views/auth/ForgotPasswordView.vue'
import ResetPasswordView from '@/views/auth/ResetPasswordView.vue'
import RegistrationSuccessView from '@/views/auth/RegistrationSuccessView.vue'
import VerifyEmailView from '@/views/auth/VerifyEmailView.vue'
import ConfirmEmailChangeView from '@/views/auth/ConfirmEmailChangeView.vue'
import GoogleCallbackView from '@/views/auth/GoogleCallbackView.vue'
import AcceptInviteView from '@/views/auth/AcceptInviteView.vue'

let sessionInitialized = false

const DashboardView = () => import('@/views/DashboardView.vue')
const AccountView = () => import('@/views/AccountView.vue')
const ProfileView = () => import('@/views/ProfileView.vue')
const SubscriptionsView = () => import('@/views/SubscriptionsView.vue')
const AddSubscriptionView = () => import('@/views/AddSubscriptionView.vue')
const ChangePlanView = () => import('@/views/ChangePlanView.vue')
const InvoicesView = () => import('@/views/InvoicesView.vue')
const WelcoSetupView = () => import('@/views/WelcoSetupView.vue')
const TeamView = () => import('@/views/TeamView.vue')
const StatisticsView = () => import('@/views/StatisticsView.vue')
const LeadsView = () => import('@/views/LeadsView.vue')
const LiveChatView = () => import('@/views/LiveChatView.vue')

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: {
      public: true,
      layout: 'auth',
    },
  },
  {
    path: '/signup',
    name: 'signup',
    component: SignUpView,
    meta: {
      public: true,
      layout: 'auth',
    },
  },
  {
    path: '/signup/success',
    name: 'signup-success',
    component: RegistrationSuccessView,
    meta: {
      public: true,
      layout: 'auth',
    },
  },
  {
    path: '/forgot-password',
    name: 'forgot-password',
    component: ForgotPasswordView,
    meta: {
      public: true,
      layout: 'auth',
    },
  },
  {
    path: '/reset-password',
    name: 'reset-password',
    component: ResetPasswordView,
    meta: {
      public: true,
      layout: 'auth',
    },
  },
  {
  path: '/verify-email',
  name: 'verify-email',
  component: VerifyEmailView,
	  meta: {
		public: true,
		layout: 'auth',
	  },
  },
  {
    path: '/auth/google/callback',
    name: 'google-callback',
    component: GoogleCallbackView,
    meta: {
      public: true,
      layout: 'auth',
    },
  },
  {
    path: '/confirm-email-change',
    name: 'confirm-email-change',
    component: ConfirmEmailChangeView,
    meta: {
      public: true,
      layout: 'auth',
    },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: DashboardView,
    meta: {
      requiresAuth: true,
      layout: 'dashboard',
    },
  },
  {
    path: '/account',
    name: 'account',
    component: AccountView,
    meta: {
      requiresAuth: true,
      layout: 'dashboard',
    },
  },
  {
    path: '/profile',
    name: 'profile',
    component: ProfileView,
    meta: {
      requiresAuth: true,
      layout: 'dashboard',
    },
  },
  {
    path: '/subscriptions',
    name: 'subscriptions',
    component: SubscriptionsView,
    meta: {
      requiresAuth: true,
      layout: 'dashboard',
    },
  },
  {
    path: '/subscriptions/add',
    name: 'add-subscription',
    component: AddSubscriptionView,
    meta: {
      requiresAuth: true,
      layout: 'dashboard',
    },
  },
  {
    path: '/subscriptions/:id/change-plan',
    name: 'change-plan',
    component: ChangePlanView,
    meta: {
      requiresAuth: true,
      layout: 'dashboard',
    },
  },
  {
    path: '/invoices',
    name: 'invoices',
    component: InvoicesView,
    meta: {
      requiresAuth: true,
      layout: 'dashboard',
    },
  },
  {
    path: '/setup/welco/:id',
    name: 'setup-welco',
    component: WelcoSetupView,
    meta: {
      requiresAuth: true,
      layout: 'dashboard',
    },
  },
  {
    path: '/statistics',
    name: 'statistics',
    component: StatisticsView,
    meta: {
      requiresAuth: true,
      layout: 'dashboard',
    },
  },
  {
    path: '/leads',
    name: 'leads',
    component: LeadsView,
    meta: {
      requiresAuth: true,
      layout: 'dashboard',
    },
  },
  {
    path: '/live-chat',
    name: 'live-chat',
    component: LiveChatView,
    meta: {
      requiresAuth: true,
      layout: 'dashboard',
    },
  },
  {
    path: '/team',
    name: 'team',
    component: TeamView,
    meta: {
      requiresAuth: true,
      layout: 'dashboard',
    },
  },
  {
    path: '/accept-invite',
    name: 'accept-invite',
    component: AcceptInviteView,
    meta: {
      public: true,
      layout: 'auth',
    },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard',
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

// ---- AUTH GUARD ----

router.beforeEach(async (to) => {
  if (!sessionInitialized) {
    await initSession()
    sessionInitialized = true
  }

  if (to.meta.requiresAuth && authSession.status !== 'authenticated') {
    return {
      path: '/login',
      query: { redirect: to.fullPath },
    }
  }
})
// ---------------------

export default router
