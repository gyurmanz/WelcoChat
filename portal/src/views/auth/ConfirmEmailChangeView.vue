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
          v-if="status === 'success' || status === 'error' || status === 'missing'"
          class="btn btn-primary btn-full"
          @click="goToLogin"
        >
          {{ t('verifyEmail.goToSignIn') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { confirmEmailChange } from '@/services/auth'

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
  if (status.value === 'success') return t('confirmEmailChange.titleSuccess')
  if (status.value === 'missing') return t('confirmEmailChange.titleMissing')
  if (status.value === 'error') return t('confirmEmailChange.titleError')
  return t('confirmEmailChange.titleLoading')
})

const subtitle = computed(() => {
  if (status.value === 'success') return t('confirmEmailChange.subtitleSuccess')
  if (status.value === 'missing') return t('confirmEmailChange.subtitleMissing')
  if (status.value === 'error') return t('confirmEmailChange.subtitleError')
  return t('confirmEmailChange.subtitleLoading')
})

const details = computed(() => {
  if (status.value === 'success') return t('confirmEmailChange.detailsSuccess')
  if (status.value === 'missing') return t('confirmEmailChange.detailsMissing')
  if (status.value === 'error') return errorMessage.value || t('confirmEmailChange.detailsError')
  return t('confirmEmailChange.detailsLoading')
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
