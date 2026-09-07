<template>
  <div class="auth-wrapper">
    <div class="auth-card">
      <header class="auth-header">
        <img
          src="@/assets/logo-dark.svg"
          alt="WelcoChat logo"
          class="auth-logo-img"
        />
        <h1 class="auth-title">Signing you in…</h1>
        <p class="auth-subtitle">
          {{ errorMessage ? 'We could not complete Google sign-in.' : 'Please wait while we finish Google sign-in.' }}
        </p>
      </header>

      <p v-if="errorMessage" class="input-hint">{{ errorMessage }}</p>

      <router-link v-if="errorMessage" to="/login" class="btn btn-primary btn-full">
        Back to sign in
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { exchangeGoogleCode, googleRedirectUri } from '@/services/auth'
import { initSession } from '@/stores/authSession'
import { setAuthToken } from '@/services/tokenStorage'

const route = useRoute()
const router = useRouter()
const errorMessage = ref('')

onMounted(async () => {
  const code = route.query.code as string | undefined
  const state = route.query.state as string | undefined
  const expectedState = sessionStorage.getItem('google_oauth_state')
  const remember = sessionStorage.getItem('google_oauth_remember') === '1'
  sessionStorage.removeItem('google_oauth_state')
  sessionStorage.removeItem('google_oauth_remember')

  // The user denied consent, or Google returned an error.
  if (route.query.error) {
    errorMessage.value = 'Google sign-in was cancelled. Please try again.'
    return
  }

  // CSRF: the returned state must match the one we stored before the redirect.
  if (!code || !state || !expectedState || state !== expectedState) {
    errorMessage.value = 'Invalid sign-in response. Please try signing in again.'
    return
  }

  try {
    const result = await exchangeGoogleCode(code, googleRedirectUri())
    setAuthToken(result.access_token, result.token_type, remember)
    await initSession()
    await router.replace('/dashboard')
  } catch (err: unknown) {
    errorMessage.value = err instanceof Error ? err.message : 'Google sign-in failed.'
  }
})
</script>
