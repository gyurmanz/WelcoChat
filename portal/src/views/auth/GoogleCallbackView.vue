<template>
  <div class="auth-wrapper">
    <div class="auth-card">
      <header class="auth-header">
        <img
          src="@/assets/logo-dark.svg"
          :alt="t('common.logoAlt')"
          class="auth-logo-img"
        />
        <h1 class="auth-title">{{ t('googleCallback.title') }}</h1>
        <p class="auth-subtitle">
          {{ errorMessage ? t('googleCallback.subtitleError') : t('googleCallback.subtitleLoading') }}
        </p>
      </header>

      <p v-if="errorMessage" class="input-hint">{{ errorMessage }}</p>

      <router-link v-if="errorMessage" to="/login" class="btn btn-primary btn-full">
        {{ t('googleCallback.backToSignIn') }}
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { exchangeGoogleCode, googleRedirectUri } from '@/services/auth'
import { initSession } from '@/stores/authSession'
import { setAuthToken } from '@/services/tokenStorage'

const { t } = useI18n()
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
    errorMessage.value = t('googleCallback.errorCancelled')
    return
  }

  // CSRF: the returned state must match the one we stored before the redirect.
  if (!code || !state || !expectedState || state !== expectedState) {
    errorMessage.value = t('googleCallback.errorInvalidResponse')
    return
  }

  try {
    const result = await exchangeGoogleCode(code, googleRedirectUri())
    setAuthToken(result.access_token, result.token_type, remember)
    await initSession()
    await router.replace('/dashboard')
  } catch (err: unknown) {
    errorMessage.value = err instanceof Error ? err.message : t('googleCallback.errorGeneric')
  }
})
</script>
