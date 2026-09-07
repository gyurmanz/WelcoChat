<template>
  <div class="page page-auth">
    <div class="auth-wrapper">
      <div class="auth-card">
        <header class="auth-header">
          <div class="auth-logo">
            <div class="logo-circle">CP</div>
          </div>
          <h1 class="auth-title">Forgot your password?</h1>
          <p class="auth-subtitle">
            Enter your email address and we will send you a link to reset your password.
          </p>
        </header>

        <form class="auth-form" @submit.prevent="handleSubmit">
          <!-- Email -->
          <div class="input-group">
            <label for="email" class="input-label">Email address</label>
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
            <span v-if="loading">Sending...</span>
            <span v-else>Send reset link</span>
          </button>
        </form>

        <footer class="auth-footer">
          <span class="auth-footer-text">
            Remembered your password?
          </span>
          <router-link to="/login" class="link-inline">
            Back to sign in
          </router-link>
        </footer>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { forgotPassword } from '@/services/auth'

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

    successMessage.value =
      'If an account with this email exists, we have sent a password reset link.'
  } catch (err: unknown) {
    if (err instanceof Error) {
      errorMessage.value = err.message
    } else {
      errorMessage.value = 'Failed to send password reset email.'
    }
  } finally {
    loading.value = false
  }
}
</script>
