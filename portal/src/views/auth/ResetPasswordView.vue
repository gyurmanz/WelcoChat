<template>
  <div class="page page-auth">
    <div class="auth-wrapper">
      <div class="auth-card">
        <header class="auth-header">
          <div class="auth-logo">
            <div class="logo-circle">CP</div>
          </div>
          <h1 class="auth-title">Set a new password</h1>
          <p class="auth-subtitle">
            Choose a strong password to secure your account.
          </p>
        </header>

        <form class="auth-form" @submit.prevent="handleSubmit">
          <!-- Token missing / invalid -->
          <div class="input-group" v-if="!token">
            <p class="input-hint">
              The reset link is invalid or has expired. Please request a new password reset.
            </p>
          </div>

          <!-- Email (read-only if present) -->
          <div class="input-group" v-if="email">
            <label for="email" class="input-label">Email address</label>
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
            <label for="password" class="input-label">New password</label>
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
            <p class="input-hint">
              Use at least 8 characters, including a number.
            </p>
          </div>

          <!-- Confirm new password -->
          <div class="input-group">
            <label for="passwordConfirm" class="input-label">Confirm new password</label>
            <input
              id="passwordConfirm"
              v-model="passwordConfirm"
              type="password"
              class="input-field"
              placeholder="Re-enter your password"
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
            <span v-if="loading">Updating password...</span>
            <span v-else>Update password</span>
          </button>
        </form>

        <footer class="auth-footer">
          <span class="auth-footer-text">
            Back to
          </span>
          <router-link to="/login" class="link-inline">
            Sign in
          </router-link>
        </footer>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { resetPassword } from '@/services/auth'

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
    errorMessage.value = 'The reset link is invalid or has expired.'
    return
  }

  errorMessage.value = ''
  successMessage.value = ''

  if (password.value.length < 8) {
    errorMessage.value = 'Password must be at least 8 characters long.'
    return
  }

  if (password.value !== passwordConfirm.value) {
    errorMessage.value = 'Passwords do not match.'
    return
  }

  loading.value = true

  try {
    await resetPassword(
      token.value,
      email.value,
      password.value,
    )

    successMessage.value = 'Your password has been updated successfully. Redirecting...'

    setTimeout(() => {
      router.push('/login')
    }, 1500)

  } catch (err: unknown) {
    if (err instanceof Error) {
      errorMessage.value = err.message
    } else {
      errorMessage.value = 'Failed to reset password. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>
