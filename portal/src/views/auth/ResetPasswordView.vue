<template>
  <div class="page page-auth">
    <div class="auth-wrapper">
      <div class="auth-card">
        <header class="auth-header">
          <div class="auth-logo">
            <div class="logo-circle">CP</div>
          </div>
          <h1 class="auth-title">{{ t('resetPassword.title') }}</h1>
          <p class="auth-subtitle">{{ t('resetPassword.subtitle') }}</p>
        </header>

        <form class="auth-form" @submit.prevent="handleSubmit">
          <!-- Token missing / invalid -->
          <div class="input-group" v-if="!token">
            <p class="input-hint">{{ t('resetPassword.invalidLink') }}</p>
          </div>

          <!-- Email (read-only if present) -->
          <div class="input-group" v-if="email">
            <label for="email" class="input-label">{{ t('login.emailLabel') }}</label>
            <input
              id="email"
              type="email"
              class="input-field"
              :value="email"
              disabled
            />
          </div>

          <!-- New password -->
          <div class="input-group">
            <label for="password" class="input-label">{{ t('resetPassword.newPasswordLabel') }}</label>
            <input
              id="password"
              v-model="password"
              type="password"
              class="input-field"
              placeholder="••••••••"
              autocomplete="new-password"
              :disabled="!token || loading"
              required
            />
            <p class="input-hint">{{ t('signup.passwordHint') }}</p>
          </div>

          <!-- Confirm new password -->
          <div class="input-group">
            <label for="passwordConfirm" class="input-label">{{ t('resetPassword.confirmNewPasswordLabel') }}</label>
            <input
              id="passwordConfirm"
              v-model="passwordConfirm"
              type="password"
              class="input-field"
              :placeholder="t('signup.confirmPasswordPlaceholder')"
              autocomplete="new-password"
              :disabled="!token || loading"
              required
            />
          </div>

          <!-- Error / success -->
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
            :disabled="!token || loading"
          >
            <span v-if="loading">{{ t('resetPassword.updating') }}</span>
            <span v-else>{{ t('resetPassword.update') }}</span>
          </button>
        </form>

        <footer class="auth-footer">
          <span class="auth-footer-text">
            {{ t('resetPassword.backTo') }}
          </span>
          <router-link to="/login" class="link-inline">
            {{ t('login.signIn') }}
          </router-link>
        </footer>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { resetPassword } from '@/services/auth'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

// token & email from query parameters
const token = computed(() => route.query.token as string)
const email = computed(() => route.query.email as string)

const password = ref('')
const passwordConfirm = ref('')
const loading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

async function handleSubmit() {
  if (!token.value) {
    errorMessage.value = t('resetPassword.invalidLinkShort')
    return
  }

  errorMessage.value = ''
  successMessage.value = ''

  if (password.value.length < 8) {
    errorMessage.value = t('resetPassword.errorTooShort')
    return
  }

  if (password.value !== passwordConfirm.value) {
    errorMessage.value = t('signup.errorPasswordMismatch')
    return
  }

  loading.value = true

  try {
    await resetPassword(
      token.value,
      email.value,
      password.value,
    )

    successMessage.value = t('resetPassword.successMessage')

    setTimeout(() => {
      router.push('/login')
    }, 1500)

  } catch (err: unknown) {
    if (err instanceof Error) {
      errorMessage.value = err.message
    } else {
      errorMessage.value = t('resetPassword.errorGeneric')
    }
  } finally {
    loading.value = false
  }
}
</script>
