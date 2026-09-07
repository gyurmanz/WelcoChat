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
          v-if="status === 'success' || status === 'error' || status === 'missing'"
          class="btn btn-primary btn-full"
          @click="goToLogin"
        >
          Go to sign in
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { confirmEmailChange } from '@/services/auth'

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
  if (status.value === 'success') return 'Email address updated'
  if (status.value === 'missing') return 'Invalid link'
  if (status.value === 'error') return 'Confirmation failed'
  return 'Confirming your new email'
})

const subtitle = computed(() => {
  if (status.value === 'success') {
    return 'Your new email address has been confirmed.'
  }
  if (status.value === 'missing') {
    return 'The confirmation link is missing or invalid.'
  }
  if (status.value === 'error') {
    return 'We could not confirm your new email address.'
  }
  return 'Please wait while we confirm your new email address.'
})

const details = computed(() => {
  if (status.value === 'success') {
    return 'Please sign in again using your new email address.'
  }
  if (status.value === 'missing') {
    return 'The confirmation URL did not contain a valid token. Please use the link from your email.'
  }
  if (status.value === 'error') {
    return (
      errorMessage.value ||
      'The confirmation link may have expired or has already been used.'
    )
  }
  return 'This will only take a moment.'
})

function goToLogin() {
  router.push({ name: 'login' })
}

onMounted(async () => {
  if (!token.value) {
    status.value = 'missing'
    return
  }

  try {
    status.value = 'loading'
    await confirmEmailChange(token.value)
    status.value = 'success'
  } catch (err: unknown) {
    status.value = 'error'
    if (err instanceof Error) {
      errorMessage.value = err.message
    }
  }
})
</script>
