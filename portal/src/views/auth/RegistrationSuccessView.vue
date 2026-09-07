<template>
  <div class="auth-wrapper">
    <div class="auth-card">
      <header class="auth-header">
        <img
          src="@/assets/logo-dark.svg"
          alt="WelcoChat logo"
          class="auth-logo-img"
        />

        <h1 class="auth-title">Check your email</h1>
        <p class="auth-subtitle">
          We have sent a confirmation link to
          <strong>{{ emailToShow }}</strong>. Please follow the instructions
          in the email to finish setting up your account.
        </p>
      </header>

      <div class="auth-form">
        <p class="input-hint">
          If you don't see the email in a few minutes, please also check your
          spam or promotions folder.
        </p>

        <button class="btn btn-primary btn-full" @click="goToLogin">
          Go to sign in
        </button>

        <div class="auth-footer">
          <span class="auth-footer-text">
            Used the wrong email address?
          </span>
          <router-link to="/signup" class="link-inline">
            Start over
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const emailToShow = computed(() => {
  const q = route.query.email
  if (typeof q === 'string' && q.trim().length > 0) {
    return q
  }
  return 'your email address'
})

function goToLogin() {
  router.push({ name: 'login' })
}
</script>
