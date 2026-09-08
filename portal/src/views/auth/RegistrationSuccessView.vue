<template>
  <div class="auth-wrapper">
    <div class="auth-card">
      <header class="auth-header">
        <img
          src="@/assets/logo-dark.svg"
          :alt="t('common.logoAlt')"
          class="auth-logo-img"
        />

        <h1 class="auth-title">{{ t('registrationSuccess.title') }}</h1>
        <p class="auth-subtitle">
          {{ t('registrationSuccess.subtitle', { email: emailToShow }) }}
        </p>
      </header>

      <div class="auth-form">
        <p class="input-hint">{{ t('registrationSuccess.checkSpam') }}</p>

        <button class="btn btn-primary btn-full" @click="goToLogin">
          {{ t('registrationSuccess.goToSignIn') }}
        </button>

        <div class="auth-footer">
          <span class="auth-footer-text">
            {{ t('registrationSuccess.wrongEmail') }}
          </span>
          <router-link to="/signup" class="link-inline">
            {{ t('registrationSuccess.startOver') }}
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const emailToShow = computed(() => {
  const q = route.query.email
  if (typeof q === 'string' && q.trim().length > 0) {
    return q
  }
  return t('registrationSuccess.yourEmailAddress')
})

function goToLogin() {
  router.push({ name: 'login' })
}
</script>
