<template>
  <div class="page">
    <h1>{{ t('profile.title') }}</h1>

    <p v-if="loadingData" class="input-hint">{{ t('common.loading') }}</p>

    <form v-else class="profile-form" @submit.prevent="save" novalidate>

      <section class="profile-section">
        <h2 class="section-h2">{{ t('profile.companyDetails') }}</h2>
        <div class="form-row">
          <label class="form-label" for="company_name">{{ t('profile.companyNameLabel') }}</label>
          <input id="company_name" v-model="form.name" class="input" :class="{ 'is-err': ve.name }" />
          <span v-if="ve.name" class="field-err">{{ ve.name }}</span>
        </div>
      </section>

      <section class="profile-section">
        <h2 class="section-h2">{{ t('profile.billingAddress') }}</h2>
        <div class="form-row">
          <label class="form-label" for="country">{{ t('profile.countryLabel') }}</label>
          <CountrySelect v-model="form.country_id" :countries="countries" />
        </div>
        <div class="form-row two-col">
          <div>
            <label class="form-label" for="postal_code">{{ t('profile.postalCodeLabel') }}</label>
            <input id="postal_code" v-model="form.postal_code" class="input" />
          </div>
          <div>
            <label class="form-label" for="city">{{ t('profile.cityLabel') }}</label>
            <input id="city" v-model="form.city" class="input" />
          </div>
        </div>
        <div class="form-row">
          <label class="form-label" for="address_line">{{ t('profile.streetLabel') }}</label>
          <input id="address_line" v-model="form.address_line" class="input" />
        </div>
      </section>

      <section class="profile-section">
        <h2 class="section-h2">{{ t('profile.taxDetails') }}</h2>
        <div class="form-row">
          <label class="form-label" for="tax_number">{{ t('profile.taxNumberLabel') }}</label>
          <input id="tax_number" v-model="form.tax_number" class="input" />
        </div>
      </section>

      <div v-if="error" class="form-msg form-err" role="alert">{{ error }}</div>
      <div v-if="success" class="form-msg form-ok" role="status">{{ success }}</div>

      <div class="form-actions">
        <button type="submit" class="btn btn-primary" :disabled="saving">
          {{ saving ? t('profile.saving') : t('profile.saveChanges') }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getCountries, getCompany, saveCompany, type Country } from '@/services/billing'
import CountrySelect from '@/components/CountrySelect.vue'

const { t } = useI18n()

const countries = ref<Country[]>([])
const loadingData = ref(true)
const saving = ref(false)
const error = ref('')
const success = ref('')
const ve = reactive<Record<string, string>>({})

const form = reactive({
  name: '',
  country_id: null as number | null,
  postal_code: '',
  city: '',
  address_line: '',
  tax_number: '',
})

onMounted(async () => {
  try {
    const [ctrs, company] = await Promise.all([getCountries(), getCompany()])
    countries.value = ctrs
    if (company) {
      form.name = company.name ?? ''
      form.country_id = company.country_id ?? null
      form.postal_code = company.postal_code ?? ''
      form.city = company.city ?? ''
      form.address_line = company.address_line ?? ''
      form.tax_number = company.tax_number ?? ''
    }
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('profile.errorLoad')
  } finally {
    loadingData.value = false
  }
})

async function save() {
  error.value = ''
  success.value = ''
  Object.keys(ve).forEach((k) => delete ve[k])

  if (!form.name.trim()) ve.name = t('profile.errorNameRequired')
  if (Object.keys(ve).length) return

  saving.value = true
  try {
    await saveCompany({
      name: form.name,
      country_id: form.country_id,
      postal_code: form.postal_code || null,
      city: form.city || null,
      address_line: form.address_line || null,
      tax_number: form.tax_number || null,
    })
    success.value = t('profile.successSave')
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('profile.errorSave')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.profile-form { max-width: 520px; margin-top: 1rem; }
.profile-section { margin-bottom: 1.75rem; }
.section-h2 { font-size: 0.95rem; font-weight: 700; margin: 0 0 0.9rem; color: rgba(148, 163, 184, 0.8); text-transform: uppercase; letter-spacing: 0.04em; }
.form-row { display: flex; flex-direction: column; gap: 0.3rem; margin-bottom: 0.9rem; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.form-label { display: block; font-size: 0.85rem; font-weight: 600; }
.two-col > div { display: flex; flex-direction: column; gap: 0.3rem; }
.input {
  display: block;
  width: 100%;
  box-sizing: border-box;
  padding: 0.55rem 0.75rem;
  border-radius: 6px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  background: rgba(30, 41, 59, 0.6);
  color: inherit;
  font: inherit;
  font-size: 0.9rem;
}
.input.is-err { border-color: #f87171; }
.field-err { font-size: 0.78rem; color: #f87171; }
.form-msg { font-size: 0.88rem; margin-bottom: 0.75rem; padding: 0.5rem 0.75rem; border-radius: 6px; }
.form-ok { background: rgba(22, 163, 74, 0.12); color: #4ade80; border: 1px solid rgba(22, 163, 74, 0.3); }
.form-err { background: rgba(239, 68, 68, 0.12); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
.form-actions { margin-top: 0.5rem; }
.btn { display: inline-flex; align-items: center; padding: 0.55rem 1.1rem; border-radius: 6px; font: inherit; font-weight: 600; font-size: 0.9rem; cursor: pointer; border: 1px solid transparent; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: var(--primary, #2563eb); color: #fff; }
@media (max-width: 500px) { .two-col { grid-template-columns: 1fr; } }
</style>
