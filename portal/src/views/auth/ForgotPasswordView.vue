<template>
  <div class="page page-auth">
    <div class="auth-wrapper">
      <div class="auth-card">
        <header class="auth-header">
          <div class="auth-logo">
            <div class="logo-circle">CP</div>
          </div>
          <h1 class="auth-title">{{ t('forgotPassword.title') }}</h1>
          <p class="auth-subtitle">{{ t('forgotPassword.subtitle') }}</p>
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

          <!-- Message -->
          <div class="input-group" v-if="errorMessage || successMessage">
            <p class="input-hint">
              <span v-if="errorMessage">{{ errorMessage }}</span>
              <span v-else>{{ successMessage }}</span>
            </p>
          </div>

          <!-- Submit -->
          <button
            type="submit"
            class="btn btn-primary btn-full"
            :disabled="loading"
          >
            <span v-if="loading">{{ t('forgotPassword.sending') }}</span>
            <span v-else>{{ t('forgotPassword.sendLink') }}</span>
          </button>
        </form>

        <footer class="auth-footer">
          <span class="auth-footer-text">
            {{ t('forgotPassword.remembered') }}
          </span>
          <router-link to="/login" class="link-inline">
            {{ t('forgotPassword.backToSignIn') }}
          </router-link>
        </footer>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { forgotPassword } from '@/services/auth'

const { t } = useI18n()

const email = ref('')
const loading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

async function handleSubmit() {
  errorMessage.value = ''
  successMessage.value = ''

  loading.value = true
  try {
    await forgotPassword(email.value)

    successMessage.value = t('forgotPassword.successMessage')
  } catch (err: unknown) {
    if (err instanceof Error) {
      errorMessage.value = err.message
    } else {
      errorMessage.value = t('forgotPassword.errorGeneric')
    }
  } finally {
    loading.value = false
  }
}
</script>
