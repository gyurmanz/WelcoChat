<template>
  <div class="layout layout-dashboard">
    <!-- Top bar -->
    <header class="dash-topbar">
      <div class="dash-topbar-left">
        <!-- Mobile-only menu button -->
        <button
          type="button"
          class="dash-topbar-menu-btn"
          @click="toggleMobileNav"
        >
          <span></span>
          <span></span>
          <span></span>
        </button>

        <img
          src="@/assets/logo-dark.svg"
          alt="WelcoChat logo"
          class="dash-topbar-logo"
        />
        <span class="dash-topbar-title">{{ t('nav.clientPortal') }}</span>
      </div>

      <div class="dash-topbar-right">
        <button
          v-if="pushPermission !== 'unsupported'"
          type="button"
          class="dash-push-btn"
          :class="{ 'dash-push-btn--active': pushEnabled }"
          :title="pushEnabled ? t('nav.pushOn') : t('nav.pushOff')"
          :aria-label="pushEnabled ? t('nav.pushOn') : t('nav.pushOff')"
          :aria-pressed="pushEnabled"
          @click="togglePush"
        >
          <span aria-hidden="true">{{ pushEnabled ? '🔔' : '🔕' }}</span>
        </button>
        <LanguageSwitcher />
        <div class="dash-user-menu" @click="toggleUserMenu">
          <div class="dash-user-info">
            <span class="dash-user-name">{{ userLabel }}</span>
            <span class="dash-user-meta">{{ t('nav.signedIn') }}</span>
          </div>
          <div class="avatar-small">
            <span>{{ userInitial }}</span>
          </div>

          <div
            v-if="isUserMenuOpen"
            class="dash-user-menu-dropdown"
          >
            <button
              type="button"
              class="dash-user-menu-item"
              @click.stop="goToAccount"
            >
              <span>{{ t('nav.account') }}</span>
            </button>
            <button
              type="button"
              class="dash-user-menu-item"
              @click.stop="logout"
            >
              <span>{{ t('nav.logout') }}</span>
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Body: left sidebar + main content -->
    <div class="dash-body">
      <!-- Desktop sidebar -->
      <aside class="dash-sidebar">
        <nav class="dash-sidebar-nav">
          <router-link
            to="/dashboard"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
          >
            <span class="dash-nav-icon">▣</span>
            <span class="dash-nav-label">{{ t('nav.dashboard') }}</span>
          </router-link>

          <router-link
            to="/subscriptions/add"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
          >
            <span class="dash-nav-icon">➕</span>
            <span class="dash-nav-label">{{ t('nav.addSubscription') }}</span>
          </router-link>

          <router-link
            to="/subscriptions"
            class="dash-nav-item"
            active-class=""
            exact-active-class="dash-nav-item--active"
          >
            <span class="dash-nav-icon">⏱</span>
            <span class="dash-nav-label">{{ t('nav.subscriptions') }}</span>
          </router-link>

          <router-link
            to="/live-chat"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
          >
            <span class="dash-nav-icon">💬</span>
            <span class="dash-nav-label">{{ t('nav.liveChat') }}</span>
            <span v-if="waitingCount > 0" class="dash-nav-badge">{{ waitingCount }}</span>
          </router-link>

          <router-link
            to="/statistics"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
          >
            <span class="dash-nav-icon">📊</span>
            <span class="dash-nav-label">{{ t('nav.statistics') }}</span>
          </router-link>

          <router-link
            to="/leads"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
          >
            <span class="dash-nav-icon">🎯</span>
            <span class="dash-nav-label">{{ t('nav.leads') }}</span>
          </router-link>

          <router-link
            to="/invoices"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
          >
            <span class="dash-nav-icon">🧾</span>
            <span class="dash-nav-label">{{ t('nav.invoices') }}</span>
          </router-link>

          <router-link
            to="/team"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
          >
            <span class="dash-nav-icon">👥</span>
            <span class="dash-nav-label">{{ t('nav.team') }}</span>
          </router-link>

          <router-link
            to="/profile"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
          >
            <span class="dash-nav-icon">👤</span>
            <span class="dash-nav-label">{{ t('nav.companyProfile') }}</span>
          </router-link>
        </nav>
      </aside>

      <!-- Main content -->
      <main class="dash-main">
        <slot />
      </main>
    </div>

    <!-- Mobile drawer menu -->
    <div
      v-if="isMobileNavOpen"
      class="dash-mobile-drawer-overlay"
      @click.self="closeMobileNav"
    >
      <div class="dash-mobile-drawer">
        <nav class="dash-sidebar-nav">
          <router-link
            to="/dashboard"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
            @click="handleNavClick"
          >
            <span class="dash-nav-icon">▣</span>
            <span class="dash-nav-label">{{ t('nav.dashboard') }}</span>
          </router-link>

          <router-link
            to="/subscriptions/add"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
            @click="handleNavClick"
          >
            <span class="dash-nav-icon">➕</span>
            <span class="dash-nav-label">{{ t('nav.addSubscription') }}</span>
          </router-link>

          <router-link
            to="/subscriptions"
            class="dash-nav-item"
            active-class=""
            exact-active-class="dash-nav-item--active"
            @click="handleNavClick"
          >
            <span class="dash-nav-icon">⏱</span>
            <span class="dash-nav-label">{{ t('nav.subscriptions') }}</span>
          </router-link>

          <router-link
            to="/live-chat"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
            @click="handleNavClick"
          >
            <span class="dash-nav-icon">💬</span>
            <span class="dash-nav-label">{{ t('nav.liveChat') }}</span>
            <span v-if="waitingCount > 0" class="dash-nav-badge">{{ waitingCount }}</span>
          </router-link>

          <router-link
            to="/statistics"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
            @click="handleNavClick"
          >
            <span class="dash-nav-icon">📊</span>
            <span class="dash-nav-label">{{ t('nav.statistics') }}</span>
          </router-link>

          <router-link
            to="/leads"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
            @click="handleNavClick"
          >
            <span class="dash-nav-icon">🎯</span>
            <span class="dash-nav-label">{{ t('nav.leads') }}</span>
          </router-link>

          <router-link
            to="/invoices"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
            @click="handleNavClick"
          >
            <span class="dash-nav-icon">🧾</span>
            <span class="dash-nav-label">{{ t('nav.invoices') }}</span>
          </router-link>

          <router-link
            to="/team"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
            @click="handleNavClick"
          >
            <span class="dash-nav-icon">👥</span>
            <span class="dash-nav-label">{{ t('nav.team') }}</span>
          </router-link>

          <router-link
            to="/profile"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
            @click="handleNavClick"
          >
            <span class="dash-nav-icon">👤</span>
            <span class="dash-nav-label">{{ t('nav.companyProfile') }}</span>
          </router-link>
        </nav>
      </div>
    </div>

    <!-- Live handoff warning toast -->
    <div v-if="showToast" class="handoff-toast" role="status">
      <span class="handoff-toast-icon" aria-hidden="true">💬</span>
      <span class="handoff-toast-text">{{ t('nav.handoffToast') }}</span>
      <button type="button" class="handoff-toast-action" @click="goToLiveChat">{{ t('nav.handoffToastView') }}</button>
      <button type="button" class="handoff-toast-close" :aria-label="t('nav.dismiss')" @click="showToast = false">✕</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { authSession } from '@/stores/authSession'
import LanguageSwitcher from '@/components/LanguageSwitcher.vue'
import { getConversations } from '@/services/liveChat'
import {
  getExistingSubscription,
  getPermissionState,
  subscribeToPush,
  unsubscribeFromPush,
  type PushPermissionState,
} from '@/services/push'

const { t } = useI18n()
const router = useRouter()

const userLabel = computed(
  () => authSession.user?.display_name || 'User'
)

const userInitial = computed(() => {
  return userLabel.value.trim().charAt(0).toUpperCase()
})

const isMobileNavOpen = ref(false)
const isUserMenuOpen = ref(false)

// Live handoff warning: a lightweight poll (not the 5s Live Chat page one)
// that runs on every portal page, so a handoff is never missed just because
// the user isn't looking at Live Chat right now.
const waitingCount = ref(0)
const showToast = ref(false)
const pushPermission = ref<PushPermissionState>(getPermissionState())
const pushEnabled = ref(false)
let toastTimer: ReturnType<typeof setTimeout> | null = null
let pollTimer: ReturnType<typeof setInterval> | null = null
let hasPolledOnce = false

async function pollHandoffs() {
  try {
    const convs = await getConversations(true)
    const waiting = convs.filter((c) => c.status === 'waiting').length
    if (hasPolledOnce && waiting > waitingCount.value) {
      showToast.value = true
      if (toastTimer) clearTimeout(toastTimer)
      toastTimer = setTimeout(() => {
        showToast.value = false
      }, 8000)
    }
    waitingCount.value = waiting
    hasPolledOnce = true
  } catch {
    // transient — keep polling on the next tick
  }
}

function goToLiveChat() {
  showToast.value = false
  router.push('/live-chat')
}

async function togglePush() {
  if (pushEnabled.value) {
    await unsubscribeFromPush()
    pushEnabled.value = false
  } else {
    const ok = await subscribeToPush()
    pushEnabled.value = ok
    pushPermission.value = getPermissionState()
  }
}

function handleServiceWorkerMessage(event: MessageEvent) {
  if (event.data?.type === 'welcochat-notification-click') {
    router.push('/live-chat')
  }
}

function toggleMobileNav() {
  isMobileNavOpen.value = !isMobileNavOpen.value
}

function closeMobileNav() {
  isMobileNavOpen.value = false
}

function handleNavClick() {
  isMobileNavOpen.value = false
}

function toggleUserMenu() {
  isUserMenuOpen.value = !isUserMenuOpen.value
}

function closeUserMenu() {
  isUserMenuOpen.value = false
}

function goToAccount() {
  closeUserMenu()
  // ide majd jöhet egy valódi account oldal
  router.push('/account')
}

async function logout() {
  // Leiratkozás a push-értesítésekről, amíg még hitelesítve vagyunk — így egy
  // megosztott böngészőn a következő bejelentkező felhasználó nem kap
  // véletlenül az előző cég élő átadásairól szóló értesítéseket.
  if (pushEnabled.value) {
    await unsubscribeFromPush().catch(() => {})
  }

  // token + user info törlése
  if (typeof window !== 'undefined') {
    window.localStorage.removeItem('auth_token')
    window.localStorage.removeItem('auth_token_type')
    window.localStorage.removeItem('user_email')
  }

  isUserMenuOpen.value = false
  isMobileNavOpen.value = false

  await router.push('/login')
}

onMounted(async () => {
  pollHandoffs()
  pollTimer = setInterval(pollHandoffs, 20000)

  const existing = await getExistingSubscription()
  pushEnabled.value = !!existing

  if (typeof navigator !== 'undefined' && navigator.serviceWorker) {
    navigator.serviceWorker.addEventListener('message', handleServiceWorkerMessage)
  }
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  if (toastTimer) clearTimeout(toastTimer)
  if (typeof navigator !== 'undefined' && navigator.serviceWorker) {
    navigator.serviceWorker.removeEventListener('message', handleServiceWorkerMessage)
  }
})
</script>
