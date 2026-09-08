<template>
  <div class="auth-wrapper">
    <div class="auth-card">
      <header class="auth-header">
        <img
          src="@/assets/logo-dark.svg"
          :alt="t('common.logoAlt')"
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
          {{ t('verifyEmail.goToSignIn') }}
        </button>

        <button
          v-else-if="status === 'error' || status === 'missing'"
          class="btn btn-outline btn-full"
          @click="goToSignup"
        >
          {{ t('verifyEmail.backToSignup') }}
        </button>
      </div>

      <footer class="auth-footer">
        <span class="auth-footer-text">
          {{ t('verifyEmail.alreadyVerified') }}
        </span>
        <router-link to="/login" class="link-inline">
          {{ t('login.signIn') }}
        </router-link>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { verifyEmail } from '@/services/auth'

type Status = 'loading' | 'success' | 'error' | 'missing'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const status = ref<Status>('loading')
const errorMessage = ref('')

const token = computed(() => {
  const tok = route.query.token
  return typeof tok === 'string' ? tok : ''
})

const title = computed(() => {
  if (status.value === 'success') return t('verifyEmail.titleSuccess')
  if (status.value === 'missing') return t('verifyEmail.titleMissing')
  if (status.value === 'error') return t('verifyEmail.titleError')
  return t('verifyEmail.titleLoading')
})

const subtitle = computed(() => {
  if (status.value === 'success') return t('verifyEmail.subtitleSuccess')
  if (status.value === 'missing') return t('verifyEmail.subtitleMissing')
  if (status.value === 'error') return t('verifyEmail.subtitleError')
  return t('verifyEmail.subtitleLoading')
})

const details = computed(() => {
  if (status.value === 'success') return t('verifyEmail.detailsSuccess')
  if (status.value === 'missing') return t('verifyEmail.detailsMissing')
  if (status.value === 'error') return errorMessage.value || t('verifyEmail.detailsError')
  return t('verifyEmail.detailsLoading')
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
