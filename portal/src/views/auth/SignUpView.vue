<template>
  <div class="auth-wrapper">
    <div class="auth-card">
      <header class="auth-header">
        <img
          src="@/assets/logo-dark.svg"
          :alt="t('common.logoAlt')"
          class="auth-logo-img"
        />

        <h1 class="auth-title">{{ t('signup.title') }}</h1>
        <p class="auth-subtitle">{{ t('signup.subtitle') }}</p>
      </header>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <!-- Display name -->
        <div class="input-group">
          <label for="displayName" class="input-label">{{ t('signup.displayNameLabel') }}</label>
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
          <label for="email" class="input-label">{{ t('signup.emailLabel') }}</label>
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
          <label for="password" class="input-label">{{ t('signup.passwordLabel') }}</label>
          <input
            id="password"
            v-model="password"
            type="password"
            class="input-field"
            placeholder="••••••••"
            autocomplete="new-password"
            required
          />
          <p class="input-hint">{{ t('signup.passwordHint') }}</p>
        </div>

        <!-- Confirm password -->
        <div class="input-group">
          <label for="passwordConfirm" class="input-label">{{ t('signup.confirmPasswordLabel') }}</label>
          <input
            id="passwordConfirm"
            v-model="passwordConfirm"
            type="password"
            class="input-field"
            :placeholder="t('signup.confirmPasswordPlaceholder')"
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
            <span>{{ t('signup.acceptTerms') }}</span>
          </label>
        </div>

        <!-- Primary submit button -->
        <button
          type="submit"
          class="btn btn-primary btn-full"
          :disabled="loading"
        >
          <span v-if="loading">{{ t('signup.creating') }}</span>
          <span v-else>{{ t('signup.createAccount') }}</span>
        </button>
      </form>

      <!-- Divider -->
      <div class="auth-divider">
        <span>{{ t('signup.orSignUpWith') }}</span>
      </div>

      <!-- Social sign up buttons (UI only for now) -->
      <div class="social-buttons">
        <button type="button" class="btn btn-outline social-btn social-google">
          <span class="social-icon">G</span>
          <span>{{ t('login.google') }}</span>
        </button>
      </div>

      <!-- Footer text -->
      <footer class="auth-footer">
        <span class="auth-footer-text">
          {{ t('signup.haveAccount') }}
        </span>
        <router-link to="/login" class="link-inline">
          {{ t('login.signIn') }}
        </router-link>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { signup } from '@/services/auth'

const { t } = useI18n()
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
    errorMessage.value = t('signup.errorAcceptTerms')
    return
  }

  if (password.value !== passwordConfirm.value) {
    errorMessage.value = t('signup.errorPasswordMismatch')
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
      errorMessage.value = t('signup.errorGeneric')
    }
  } finally {
    loading.value = false
  }
}
</script>
