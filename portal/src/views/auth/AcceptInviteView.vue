<template>
  <div class="auth-wrapper">
    <div class="auth-card">
      <header class="auth-header">
        <img
          src="@/assets/logo-dark.svg"
          alt="WelcoChat logo"
          class="auth-logo-img"
        />

        <template v-if="loadingInvite">
          <h1 class="auth-title">Loading invite…</h1>
        </template>
        <template v-else-if="loadError">
          <h1 class="auth-title">Invite not found</h1>
          <p class="auth-subtitle">{{ loadError }}</p>
        </template>
        <template v-else>
          <h1 class="auth-title">Join {{ invite?.owner_display_name }}'s WelcoChat account</h1>
          <p class="auth-subtitle">
            Set a password for {{ invite?.invite_email }} to get started.
          </p>
        </template>
      </header>

      <form v-if="!loadingInvite && !loadError" class="auth-form" @submit.prevent="handleSubmit">
        <div class="input-group">
          <label for="displayName" class="input-label">Your name</label>
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
          <p class="input-hint">Use at least 8 characters, including a number.</p>
        </div>

        <div class="input-group" v-if="errorMessage">
          <p class="input-hint">{{ errorMessage }}</p>
        </div>

        <button type="submit" class="btn btn-primary btn-full" :disabled="submitting">
          <span v-if="submitting">Joining…</span>
          <span v-else>Accept invite</span>
        </button>
      </form>

      <footer class="auth-footer" v-if="loadError">
        <router-link to="/login" class="link-inline">Go to sign in</router-link>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getInviteDetails, acceptInvite, type InviteDetails } from '@/services/team'
import { initSession } from '@/stores/authSession'
import { setAuthToken } from '@/services/tokenStorage'

const route = useRoute()
const router = useRouter()
const token = String(route.query.token || '')

const loadingInvite = ref(true)
const loadError = ref('')
const invite = ref<InviteDetails | null>(null)

const displayName = ref('')
const password = ref('')
const submitting = ref(false)
const errorMessage = ref('')

onMounted(async () => {
  if (!token) {
    loadError.value = 'This invite link is missing its token.'
    loadingInvite.value = false
    return
  }
  try {
    invite.value = await getInviteDetails(token)
  } catch (err: unknown) {
    loadError.value = err instanceof Error ? err.message : 'This invite link is invalid or has expired.'
  } finally {
    loadingInvite.value = false
  }
})

async function handleSubmit() {
  errorMessage.value = ''
  submitting.value = true
  try {
    const result = await acceptInvite(token, displayName.value, password.value)
    setAuthToken(result.access_token, result.token_type, true)
    await initSession()
    await router.push('/dashboard')
  } catch (err: unknown) {
    errorMessage.value = err instanceof Error ? err.message : 'Failed to accept invite. Please try again.'
  } finally {
    submitting.value = false
  }
}
</script>
