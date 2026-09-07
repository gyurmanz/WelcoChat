<template>
  <div class="auth-wrapper">
    <div class="auth-card">
      <header class="auth-header">
        <img
          src="@/assets/logo-dark.svg"
          alt="WelcoChat logo"
          class="auth-logo-img"
        />

        <h1 class="auth-title">Create your account</h1>
        <p class="auth-subtitle">
          Set up your client portal access in a few quick steps.
        </p>
      </header>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <!-- Display name -->
        <div class="input-group">
          <label for="displayName" class="input-label">Display name</label>
          <input
            id="displayName"
            v-model="displayName"
            type="text"
            class="input-field"
            placeholder="John Doe"
            autocomplete="nickname"
            required
          />
        </div>

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

        <!-- Password -->
        <div class="input-group">
          <label for="password" class="input-label">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            class="input-field"
            placeholder="••••••••"
            autocomplete="new-password"
            required
          />
          <p class="input-hint">
            Use at least 8 characters, including a number.
          </p>
        </div>

        <!-- Confirm password -->
        <div class="input-group">
          <label for="passwordConfirm" class="input-label">Confirm password</label>
          <input
            id="passwordConfirm"
            v-model="passwordConfirm"
            type="password"
            class="input-field"
            placeholder="Re-enter your password"
            autocomplete="new-password"
            required
          />
        </div>

        <!-- Error message (lokális validáció / API hiba) -->
        <div class="input-group" v-if="errorMessage">
          <p class="input-hint">
            {{ errorMessage }}
          </p>
        </div>

        <!-- Terms -->
        <div class="auth-options-row">
          <label class="checkbox">
            <input v-model="acceptedTerms" type="checkbox" />
            <span>I agree to the Terms and Privacy Policy</span>
          </label>
        </div>

        <!-- Primary submit button -->
        <button
          type="submit"
          class="btn btn-primary btn-full"
          :disabled="loading"
        >
          <span v-if="loading">Creating request...</span>
          <span v-else>Create account</span>
        </button>
      </form>

      <!-- Divider -->
      <div class="auth-divider">
        <span>or sign up with</span>
      </div>

      <!-- Social sign up buttons (UI only for now) -->
      <div class="social-buttons">
        <button type="button" class="btn btn-outline social-btn social-google">
          <span class="social-icon">G</span>
          <span>Google</span>
        </button>
      </div>

      <!-- Footer text -->
      <footer class="auth-footer">
        <span class="auth-footer-text">
          Already have an account?
        </span>
        <router-link to="/login" class="link-inline">
          Sign in
        </router-link>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { signup } from '@/services/auth'

const router = useRouter()

const displayName = ref('')
const email = ref('')
const password = ref('')
const passwordConfirm = ref('')
const acceptedTerms = ref(false)

const loading = ref(false)
const errorMessage = ref('')

async function handleSubmit() {
  errorMessage.value = ''

  if (!acceptedTerms.value) {
    errorMessage.value = 'You must accept the Terms and Privacy Policy.'
    return
  }

  if (password.value !== passwordConfirm.value) {
    errorMessage.value = 'Passwords do not match.'
    return
  }

  loading.value = true

  try {
    await signup({
      display_name: displayName.value,
      email: email.value,
      password: password.value,
    })

    // Sikeres request → átirányítás a success oldalra
    await router.push({
      name: 'signup-success',
      query: { email: email.value },
    })
  } catch (err: unknown) {
    if (err instanceof Error) {
      errorMessage.value = err.message
    } else {
      errorMessage.value = 'Registration failed. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>
