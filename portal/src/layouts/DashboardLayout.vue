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
        <span class="dash-topbar-title">Client Portal</span>
      </div>

      <div class="dash-topbar-right">
        <div class="dash-user-menu" @click="toggleUserMenu">
          <div class="dash-user-info">
            <span class="dash-user-name">{{ userLabel }}</span>
            <span class="dash-user-meta">Signed in</span>
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
              <span>Account</span>
            </button>
            <button
              type="button"
              class="dash-user-menu-item"
              @click.stop="logout"
            >
              <span>Logout</span>
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
            <span class="dash-nav-label">Dashboard</span>
          </router-link>

          <router-link
            to="/subscriptions/add"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
          >
            <span class="dash-nav-icon">➕</span>
            <span class="dash-nav-label">Add subscription</span>
          </router-link>

          <router-link
            to="/subscriptions"
            class="dash-nav-item"
            active-class=""
            exact-active-class="dash-nav-item--active"
          >
            <span class="dash-nav-icon">⏱</span>
            <span class="dash-nav-label">Subscriptions</span>
          </router-link>

          <router-link
            to="/live-chat"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
          >
            <span class="dash-nav-icon">💬</span>
            <span class="dash-nav-label">Live Chat</span>
          </router-link>

          <router-link
            to="/statistics"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
          >
            <span class="dash-nav-icon">📊</span>
            <span class="dash-nav-label">Statistics</span>
          </router-link>

          <router-link
            to="/invoices"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
          >
            <span class="dash-nav-icon">🧾</span>
            <span class="dash-nav-label">Invoices</span>
          </router-link>

          <router-link
            to="/team"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
          >
            <span class="dash-nav-icon">👥</span>
            <span class="dash-nav-label">Team</span>
          </router-link>

          <router-link
            to="/profile"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
          >
            <span class="dash-nav-icon">👤</span>
            <span class="dash-nav-label">Profile</span>
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
            <span class="dash-nav-label">Dashboard</span>
          </router-link>

          <router-link
            to="/subscriptions/add"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
            @click="handleNavClick"
          >
            <span class="dash-nav-icon">➕</span>
            <span class="dash-nav-label">Add subscription</span>
          </router-link>

          <router-link
            to="/subscriptions"
            class="dash-nav-item"
            active-class=""
            exact-active-class="dash-nav-item--active"
            @click="handleNavClick"
          >
            <span class="dash-nav-icon">⏱</span>
            <span class="dash-nav-label">Subscriptions</span>
          </router-link>

          <router-link
            to="/live-chat"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
            @click="handleNavClick"
          >
            <span class="dash-nav-icon">💬</span>
            <span class="dash-nav-label">Live Chat</span>
          </router-link>

          <router-link
            to="/statistics"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
            @click="handleNavClick"
          >
            <span class="dash-nav-icon">📊</span>
            <span class="dash-nav-label">Statistics</span>
          </router-link>

          <router-link
            to="/invoices"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
            @click="handleNavClick"
          >
            <span class="dash-nav-icon">🧾</span>
            <span class="dash-nav-label">Invoices</span>
          </router-link>

          <router-link
            to="/team"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
            @click="handleNavClick"
          >
            <span class="dash-nav-icon">👥</span>
            <span class="dash-nav-label">Team</span>
          </router-link>

          <router-link
            to="/profile"
            class="dash-nav-item"
            active-class="dash-nav-item--active"
            @click="handleNavClick"
          >
            <span class="dash-nav-icon">👤</span>
            <span class="dash-nav-label">Profile</span>
          </router-link>
        </nav>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { authSession } from '@/stores/authSession'

const router = useRouter()

const userLabel = computed(
  () => authSession.user?.display_name || 'User'
)

const userInitial = computed(() => {
  return userLabel.value.trim().charAt(0).toUpperCase()
})

const isMobileNavOpen = ref(false)
const isUserMenuOpen = ref(false)

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
</script>
