<template>
  <div class="auth-wrapper">
    <div class="auth-card">
      <header class="auth-header">
        <img
          src="@/assets/logo-dark.svg"
          :alt="t('common.logoAlt')"
          class="auth-logo-img"
        />

        <template v-if="loadingInvite">
          <h1 class="auth-title">{{ t('acceptInvite.loading') }}</h1>
        </template>
        <template v-else-if="loadError">
          <h1 class="auth-title">{{ t('acceptInvite.notFoundTitle') }}</h1>
          <p class="auth-subtitle">{{ loadError }}</p>
        </template>
        <template v-else>
          <h1 class="auth-title">{{ t('acceptInvite.joinTitle', { company: invite?.owner_display_name }) }}</h1>
          <p class="auth-subtitle">
            {{ t('acceptInvite.setPassword', { email: invite?.invite_email }) }}
          </p>
        </template>
      </header>

      <form v-if="!loadingInvite && !loadError" class="auth-form" @submit.prevent="handleSubmit">
        <div class="input-group">
          <label for="displayName" class="input-label">{{ t('acceptInvite.yourNameLabel') }}</label>
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
          <label for="password" class="input-label">{{ t('login.passwordLabel') }}</label>
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

        <div class="input-group" v-if="errorMessage">
          <p class="input-hint">{{ errorMessage }}</p>
        </div>

        <button type="submit" class="btn btn-primary btn-full" :disabled="submitting">
          <span v-if="submitting">{{ t('acceptInvite.joining') }}</span>
          <span v-else>{{ t('acceptInvite.accept') }}</span>
        </button>
      </form>

      <footer class="auth-footer" v-if="loadError">
        <router-link to="/login" class="link-inline">{{ t('acceptInvite.goToSignIn') }}</router-link>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { getInviteDetails, acceptInvite, type InviteDetails } from '@/services/team'
import { initSession } from '@/stores/authSession'
import { setAuthToken } from '@/services/tokenStorage'

const { t } = useI18n()
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
    loadError.value = t('acceptInvite.errorMissingToken')
    loadingInvite.value = false
    return
  }
  try {
    invite.value = await getInviteDetails(token)
  } catch (err: unknown) {
    loadError.value = err instanceof Error ? err.message : t('acceptInvite.errorInvalidInvite')
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
    errorMessage.value = err instanceof Error ? err.message : t('acceptInvite.errorGeneric')
  } finally {
    submitting.value = false
  }
}
</script>
