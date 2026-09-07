<template>
  <div class="auth-wrapper">
    <div class="auth-card">
      <header class="auth-header">
        <img
          src="@/assets/logo-dark.svg"
          alt="WelcoChat logo"
          class="auth-logo-img"
        />

        <h1 class="auth-title">
          {{ title }}
        </h1>
        <p class="auth-subtitle">
          {{ subtitle }}
        </p>
      </header>

      <div class="auth-form">
        <p class="input-hint">
          {{ details }}
        </p>

        <button
          v-if="status === 'success'"
          class="btn btn-primary btn-full"
          @click="goToLogin"
        >
          Go to sign in
        </button>

        <button
          v-else-if="status === 'error' || status === 'missing'"
          class="btn btn-outline btn-full"
          @click="goToSignup"
        >
          Back to sign up
        </button>
      </div>

      <footer class="auth-footer">
        <span class="auth-footer-text">
          Already verified your email?
        </span>
        <router-link to="/login" class="link-inline">
          Sign in
        </router-link>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { verifyEmail } from '@/services/auth'

type Status = 'loading' | 'success' | 'error' | 'missing'

const route = useRoute()
const router = useRouter()

const status = ref<Status>('loading')
const errorMessage = ref('')

const token = computed(() => {
  const t = route.query.token
  return typeof t === 'string' ? t : ''
})

const title = computed(() => {
  if (status.value === 'success') return 'Email verified'
  if (status.value === 'missing') return 'Invalid link'
  if (status.value === 'error') return 'Verification failed'
  return 'Verifying your email'
})

const subtitle = computed(() => {
  if (status.value === 'success') {
    return 'Your email address has been confirmed. You can now sign in to your account.'
  }
  if (status.value === 'missing') {
    return 'The verification link is missing or invalid.'
  }
  if (status.value === 'error') {
    return 'We could not verify your email address.'
  }
  return 'Please wait while we verify your email address.'
})

const details = computed(() => {
  if (status.value === 'success') {
    return 'You will be able to access your client portal once you sign in with your verified email address.'
  }
  if (status.value === 'missing') {
    return 'The verification URL did not contain a valid token. Please use the link from your email, or request a new one.'
  }
  if (status.value === 'error') {
    return (
      errorMessage.value ||
      'The verification link may have expired or has already been used. Please request a new verification email or contact support if the problem persists.'
    )
  }
  return 'This will only take a moment.'
})

function goToLogin() {
  router.push({ name: 'login' })
}

function goToSignup() {
  router.push({ name: 'signup' })
}

onMounted(async () => {
  if (!token.value) {
    status.value = 'missing'
    return
  }

  try {
    status.value = 'loading'
    await verifyEmail(token.value)
    status.value = 'success'
  } catch (err: unknown) {
    status.value = 'error'
    if (err instanceof Error) {
      errorMessage.value = err.message
    }
  }
})
</script>
