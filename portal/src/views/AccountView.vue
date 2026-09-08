<template>
  <div class="page">
    <h1>{{ t('account.title') }}</h1>
    <p>{{ t('account.intro') }}</p>

    <!-- Profile -->
    <form class="auth-form account-form" @submit.prevent="saveProfile">
      <h2>{{ t('account.profileHeading') }}</h2>

      <div class="input-group">
        <label for="display_name" class="input-label">{{ t('account.displayNameLabel') }}</label>
        <input
          id="display_name"
          v-model="displayName"
          type="text"
          class="input-field"
          autocomplete="name"
          required
        />
      </div>

      <div class="input-group">
        <label for="email" class="input-label">{{ t('login.emailLabel') }}</label>
        <input
          id="email"
          v-model="email"
          type="email"
          class="input-field"
          autocomplete="email"
          :disabled="isGoogle"
        />
        <p class="input-hint" v-if="isGoogle">
          {{ t('account.emailGoogleManaged') }}
        </p>
      </div>

      <div class="input-group">
        <label for="phone" class="input-label">{{ t('account.phoneLabel') }}</label>
        <input
          id="phone"
          v-model="phone"
          type="tel"
          class="input-field"
          autocomplete="tel"
          inputmode="tel"
          pattern="\+[0-9]{7,15}"
          placeholder="+36301234567"
        />
        <p class="input-hint">{{ t('account.phoneHint') }}</p>
      </div>

      <div class="input-group" v-if="profileError || profileSuccess">
        <p class="input-hint">
          <span v-if="profileError">{{ profileError }}</span>
          <span v-else>{{ profileSuccess }}</span>
        </p>
      </div>

      <button type="submit" class="btn btn-primary btn-full" :disabled="profileLoading">
        <span v-if="profileLoading">{{ t('account.savingProfile') }}</span>
        <span v-else>{{ t('account.saveProfile') }}</span>
      </button>
    </form>

    <!-- Password -->
    <form
      v-if="hasPassword"
      class="auth-form account-form"
      @submit.prevent="savePassword"
    >
      <h2>{{ t('account.changePasswordHeading') }}</h2>

      <div class="input-group">
        <label for="current_password" class="input-label">{{ t('account.currentPasswordLabel') }}</label>
        <input
          id="current_password"
          v-model="currentPassword"
          type="password"
          class="input-field"
          autocomplete="current-password"
          required
        />
      </div>

      <div class="input-group">
        <label for="new_password" class="input-label">{{ t('resetPassword.newPasswordLabel') }}</label>
        <input
          id="new_password"
          v-model="newPassword"
          type="password"
          class="input-field"
          autocomplete="new-password"
          minlength="8"
          required
        />
      </div>

      <div class="input-group">
        <label for="confirm_password" class="input-label">{{ t('resetPassword.confirmNewPasswordLabel') }}</label>
        <input
          id="confirm_password"
          v-model="confirmPassword"
          type="password"
          class="input-field"
          autocomplete="new-password"
          required
        />
      </div>

      <div class="input-group" v-if="passwordError || passwordSuccess">
        <p class="input-hint">
          <span v-if="passwordError">{{ passwordError }}</span>
          <span v-else>{{ passwordSuccess }}</span>
        </p>
      </div>

      <button type="submit" class="btn btn-primary btn-full" :disabled="passwordLoading">
        <span v-if="passwordLoading">{{ t('account.changingPassword') }}</span>
        <span v-else>{{ t('account.changePassword') }}</span>
      </button>
    </form>

    <p v-else class="input-hint account-form">
      {{ t('account.googleNoPassword') }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { authSession, initSession } from '@/stores/authSession'
import { updateProfile, changePassword } from '@/services/auth'
import { setAuthToken, isRemembered } from '@/services/tokenStorage'

const { t } = useI18n()

const user = computed(() => authSession.user)
const hasPassword = computed(() => user.value?.has_password ?? false)
const isGoogle = computed(() => !hasPassword.value)

const displayName = ref(user.value?.display_name ?? '')
const email = ref(user.value?.email ?? '')
const phone = ref(user.value?.phone ?? '')

const profileLoading = ref(false)
const profileError = ref('')
const profileSuccess = ref('')

const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const passwordLoading = ref(false)
const passwordError = ref('')
const passwordSuccess = ref('')

async function saveProfile() {
  profileError.value = ''
  profileSuccess.value = ''
  const phoneVal = phone.value.trim()
  if (phoneVal && !/^\+[0-9]{7,15}$/.test(phoneVal)) {
    profileError.value = t('account.errorPhoneFormat')
    return
  }
  profileLoading.value = true
  try {
    const payload: { display_name?: string; email?: string; phone?: string } = {
      display_name: displayName.value,
      phone: phoneVal,
    }
    if (!isGoogle.value) {
      payload.email = email.value
    }
    const result = await updateProfile(payload)
    setAuthToken(result.access_token, result.token_type, isRemembered())
    await initSession()
    if (result.email_change_pending) {
      // Az email csak megerosites utan valtozik; a mezot visszaallitjuk a jelenlegire.
      email.value = user.value?.email ?? email.value
      profileSuccess.value = t('account.emailChangePending')
    } else {
      profileSuccess.value = t('account.profileUpdated')
    }
  } catch (err: unknown) {
    profileError.value =
      err instanceof Error ? err.message : t('account.errorProfileUpdate')
  } finally {
    profileLoading.value = false
  }
}

async function savePassword() {
  passwordError.value = ''
  passwordSuccess.value = ''
  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = t('account.errorPasswordMismatch')
    return
  }
  passwordLoading.value = true
  try {
    await changePassword(currentPassword.value, newPassword.value)
    passwordSuccess.value = t('account.passwordChanged')
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
  } catch (err: unknown) {
    passwordError.value =
      err instanceof Error ? err.message : t('account.errorPasswordChange')
  } finally {
    passwordLoading.value = false
  }
}
</script>

<style scoped>
.account-form {
  max-width: 480px;
  margin-top: 1.5rem;
}
</style>
