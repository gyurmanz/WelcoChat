<template>
  <div class="auth-wrapper">
    <div class="auth-card">
      <header class="auth-header">
        <img
          src="@/assets/logo-dark.svg"
          :alt="t('common.logoAlt')"
          class="auth-logo-img"
        />

        <h1 class="auth-title">{{ t('login.title') }}</h1>
        <p class="auth-subtitle">{{ t('login.subtitle') }}</p>
      </header>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <!-- Email -->
        <div class="input-group">
          <label for="email" class="input-label">{{ t('login.emailLabel') }}</label>
          <input
            id="email"
            v-model="email"
            type="email"
            class="input-field"
            placeholder="you@example.com"
            autocomplete="email"
            required
          />
        </div>

        <!-- Password -->
        <div class="input-group">
          <div class="input-label-row">
            <label for="password" class="input-label">{{ t('login.passwordLabel') }}</label>
            <router-link to="/forgot-password" class="link-inline">
              {{ t('login.forgotPassword') }}
            </router-link>
          </div>
          <input
            id="password"
            v-model="password"
            type="password"
            class="input-field"
            placeholder="••••••••"
            autocomplete="current-password"
            required
          />
          <p v-if="errorMessage" class="input-hint">
            {{ errorMessage }}
          </p>
        </div>

        <!-- Remember me -->
        <div class="auth-options-row">
          <label class="checkbox">
            <input v-model="rememberMe" type="checkbox" />
            <span>{{ t('login.rememberMe') }}</span>
          </label>
        </div>

        <!-- Primary submit button -->
        <button
          type="submit"
          class="btn btn-primary btn-full"
          :disabled="loading"
        >
          <span v-if="loading">{{ t('login.signingIn') }}</span>
          <span v-else>{{ t('login.signIn') }}</span>
        </button>
      </form>

      <!-- Divider -->
      <div class="auth-divider">
        <span>{{ t('login.orContinueWith') }}</span>
      </div>

      <!-- Social login buttons -->
      <div class="social-buttons">
        <button type="button" class="btn btn-outline social-btn social-google" @click="startGoogleLogin">
          <span class="social-icon">G</span>
          <span>{{ t('login.google') }}</span>
        </button>
      </div>

      <!-- Footer text -->
      <footer class="auth-footer">
        <span class="auth-footer-text">
          {{ t('login.noAccount') }}
        </span>
        <router-link to="/signup" class="link-inline">
          {{ t('login.createAccount') }}
        </router-link>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { login, buildGoogleAuthUrl } from '@/services/auth'
import { initSession } from '@/stores/authSession'
import { setAuthToken } from '@/services/tokenStorage'

const { t } = useI18n()

const email = ref('')
const password = ref('')
const rememberMe = ref(false)
const loading = ref(false)
const errorMessage = ref('')

const router = useRouter()
const route = useRoute()

async function handleSubmit() {
  errorMessage.value = ''
  loading.value = true

  try {
    const result = await login(email.value, password.value)

    // 🔑 ITT kap szerepet a remember me
    setAuthToken(
      result.access_token,
      result.token_type,
      rememberMe.value,
    )

    await initSession()

    const redirect = (route.query.redirect as string) || '/dashboard'
    await router.push(redirect)
  } catch (err: unknown) {
    errorMessage.value = err instanceof Error ? err.message : t('login.loginFailed')
  } finally {
    loading.value = false
  }
}

function startGoogleLogin() {
  // CSRF nonce: verified on the callback against the value stored here. Keep the
  // "remember me" choice across the redirect so the session storage type matches.
  const state =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2)
  sessionStorage.setItem('google_oauth_state', state)
  sessionStorage.setItem('google_oauth_remember', rememberMe.value ? '1' : '0')
  window.location.href = buildGoogleAuthUrl(state)
}
</script>
