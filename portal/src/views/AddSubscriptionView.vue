<template>
  <div class="page">
    <h1>{{ t('addSub.title') }}</h1>

    <!-- Stepper -->
    <div class="stepper" :aria-label="t('addSub.stepperAriaLabel')">
      <div
        v-for="(label, i) in stepLabels"
        :key="i"
        class="stepper-item"
        :class="{ 'is-active': step === i + 1, 'is-done': step > i + 1 }"
      >
        <div class="stepper-dot">{{ step > i + 1 ? '✓' : i + 1 }}</div>
        <span class="stepper-label">{{ label }}</span>
      </div>
    </div>

    <p v-if="error" class="form-error" role="alert">{{ error }}</p>

    <!-- Returning from Stripe Checkout -->
    <section v-if="checkoutStatus === 'finalizing'" class="order-section">
      <div class="confirm-icon">⏳</div>
      <h2 class="confirm-h2">{{ t('addSub.finalizingTitle') }}</h2>
      <p class="confirm-sub">{{ t('addSub.finalizingSub') }}</p>
    </section>
    <section v-else-if="checkoutStatus === 'cancelled'" class="order-section">
      <p class="step-subtitle">{{ t('addSub.checkoutCancelled') }}</p>
      <div class="form-actions">
        <button class="btn btn-primary" @click="checkoutStatus = null">{{ t('addSub.backToPlans') }}</button>
      </div>
    </section>

    <!-- STEP 1: Choose subscription -->
    <section v-if="checkoutStatus === null && step === 1" class="order-section">
      <p class="step-subtitle">{{ t('addSub.step1Subtitle') }}</p>

      <div class="service-cards">
        <div
          v-for="svc in serviceGroups"
          :key="svc.service_key"
          class="service-card"
          @click="selectService(svc)"
          role="button"
          :tabindex="0"
          @keyup.enter="selectService(svc)"
        >
          <div class="sc-name">{{ svc.service_name }}</div>
          <div class="sc-desc">{{ svc.description }}</div>
          <div class="sc-price">{{ t('addSub.fromPrice', { price: fmt(svc.from_monthly) }) }}</div>
          <span class="sc-cta">{{ t('addSub.choose') }}</span>
        </div>
      </div>
    </section>

    <!-- STEP 2: Choose plan -->
    <section v-if="checkoutStatus === null && step === 2" class="order-section">
      <button class="back-btn" @click="step = 1">{{ t('addSub.back') }}</button>
      <p class="step-subtitle">
        {{ t('addSub.step2SubtitlePrefix') }} <strong>{{ selectedService?.service_name }}</strong>.
      </p>

      <div v-if="trialEligibleForSelected" class="trial-banner">
        <div class="trial-banner-text">
          <strong>{{ t('addSub.trialBannerTitle', { name: selectedService?.service_name }) }}</strong>
          <p>{{ t('addSub.trialBannerText') }}</p>
        </div>
        <button class="btn btn-primary" @click="selectTrial">{{ t('addSub.startFreeTrial') }}</button>
      </div>

      <p class="step-subtitle" style="margin-top: 1.5rem;">{{ t('addSub.orChoosePlan') }}</p>

      <div class="billing-toggle">
        <button class="billing-opt" :class="{ active: billing === 'monthly' }" @click="billing = 'monthly'">{{ t('addSub.monthly') }}</button>
        <button class="billing-opt" :class="{ active: billing === 'annual' }" @click="billing = 'annual'">{{ t('addSub.annual') }}</button>
        <span v-if="billing === 'annual'" class="save-badge">{{ t('addSub.save20') }}</span>
      </div>
      <p v-if="billing === 'annual'" class="billing-note">{{ t('addSub.annualNote') }}</p>

      <div class="plan-cards">
        <div
          v-for="plan in plansForService"
          :key="plan.tier"
          class="plan-card"
          :class="{ 'is-selected': selectedPlan?.tier === plan.tier }"
          @click="selectPlan(plan)"
          role="button"
          :tabindex="0"
          @keyup.enter="selectPlan(plan)"
        >
          <div class="pc-tier">{{ cap(plan.tier) }}</div>
          <div class="pc-price">
            {{ t('addSub.pricePerMo', { price: fmt(billing === 'annual' ? plan.annual_price : plan.monthly_price) }) }}
          </div>
          <div v-if="billing === 'annual'" class="pc-annual">
            {{ t('addSub.billedAnnually') }}<br />{{ t('addSub.chargedYearly', { price: fmt(plan.annual_price * 12) }) }}
          </div>
          <button class="btn btn-primary pc-btn" @click.stop="selectPlan(plan)">{{ t('addSub.selectPlan') }}</button>
        </div>
      </div>
    </section>

    <!-- STEP 3: Billing details -->
    <section v-if="checkoutStatus === null && step === 3" class="order-section">
      <button class="back-btn" @click="step = 2">{{ t('addSub.back') }}</button>

      <template v-if="loadingBilling">
        <p class="step-subtitle">{{ t('addSub.loadingBilling') }}</p>
      </template>

      <template v-else-if="!company || !company.name">
        <p class="step-subtitle">{{ t('addSub.noCompanyProfile') }}</p>
        <div class="form-actions">
          <router-link to="/profile" class="btn btn-primary">{{ t('addSub.goToProfile') }}</router-link>
          <button class="btn btn-outline" @click="reloadBilling">{{ t('addSub.checkAgain') }}</button>
        </div>
      </template>

      <template v-else>
        <p class="step-subtitle">{{ t('addSub.billingFromProfile') }}</p>

        <div class="review-block">
          <div class="review-row"><span>{{ t('addSub.company') }}</span><b>{{ company.name }}</b></div>
          <div class="review-row"><span>{{ t('profile.countryLabel') }}</span><b>{{ countryName(company.country_id) }}</b></div>
          <div class="review-row" v-if="company.tax_number"><span>{{ t('addSub.vatNumber') }}</span><b>{{ company.tax_number }}</b></div>
          <div class="review-row"><span>{{ t('profile.postalCodeLabel') }}</span><b>{{ company.postal_code || '-' }}</b></div>
          <div class="review-row"><span>{{ t('profile.cityLabel') }}</span><b>{{ company.city || '-' }}</b></div>
          <div class="review-row"><span>{{ t('addSub.street') }}</span><b>{{ company.address_line || '-' }}</b></div>
          <div class="review-row"><span>{{ t('addSub.billingEmail') }}</span><b>{{ authSession.user?.email }}</b></div>
          <div class="review-row"><span>{{ t('addSub.contactPerson') }}</span><b>{{ authSession.user?.display_name }}</b></div>
          <div class="review-row" v-if="authSession.user?.phone"><span>{{ t('addSub.contactPhone') }}</span><b>{{ authSession.user?.phone }}</b></div>
        </div>
        <p class="field-hint">
          {{ t('addSub.needToChange') }} <router-link to="/profile">{{ t('addSub.editProfile') }}</router-link>.
        </p>

        <div class="form-actions">
          <button class="btn btn-primary" @click="goToReview">{{ t('addSub.continueToReview') }}</button>
        </div>
      </template>
    </section>

    <!-- STEP 4: Review -->
    <section v-if="checkoutStatus === null && step === 4" class="order-section">
      <button class="back-btn" @click="step = 3">{{ t('addSub.back') }}</button>
      <h2 class="review-h2">{{ t('addSub.reviewOrder') }}</h2>

      <div class="review-block">
        <div class="review-block-title">{{ t('addSub.subscription') }}</div>
        <div class="review-row"><span>{{ t('addSub.service') }}</span><b>{{ selectedService?.service_name }}</b></div>
        <div class="review-row"><span>{{ t('addSub.plan') }}</span><b>{{ selectedPlan ? cap(selectedPlan.tier) : '-' }}</b></div>
        <div class="review-row"><span>{{ t('addSub.billing') }}</span><b>{{ cap(billing) }}</b></div>
        <div class="review-row">
          <span>{{ isTrial ? t('addSub.priceAfterTrial') : t('addSub.price') }}</span>
          <b>{{ t('addSub.pricePerMo', { price: fmt(billing === 'annual' ? (selectedPlan?.annual_price ?? 0) : (selectedPlan?.monthly_price ?? 0)) }) }}</b>
        </div>
        <div class="review-row review-vat"><span>{{ t('addSub.vat') }}</span><b>{{ t('addSub.vatNotIncluded') }}</b></div>
      </div>

      <div class="review-block">
        <div class="review-block-title">{{ isTrial ? t('addSub.freeTrial') : t('addSub.payment') }}</div>
        <p v-if="isTrial" class="review-next">
          {{ t('addSub.trialExplain') }}
        </p>
        <p v-else class="review-next">
          {{ t('addSub.paymentExplain') }}
        </p>
      </div>

      <div class="review-block">
        <div class="review-block-title">{{ t('addSub.billingDetails') }}</div>
        <div class="review-row"><span>{{ t('addSub.company') }}</span><b>{{ company?.name }}</b></div>
        <div class="review-row"><span>{{ t('profile.countryLabel') }}</span><b>{{ countryName(company?.country_id ?? null) }}</b></div>
        <div class="review-row" v-if="company?.tax_number"><span>{{ t('addSub.vatNumber') }}</span><b>{{ company?.tax_number }}</b></div>
        <div class="review-row"><span>{{ t('addSub.billingEmail') }}</span><b>{{ authSession.user?.email }}</b></div>
      </div>

      <div class="review-block">
        <div class="review-block-title">{{ t('addSub.whatHappensNext') }}</div>
        <p v-if="isTrial" class="review-next">
          {{ t('addSub.nextTrial') }}
        </p>
        <p v-else class="review-next">
          {{ t('addSub.nextPayment') }}
        </p>
      </div>

      <div class="review-checks">
        <label class="check-row">
          <input type="checkbox" v-model="confirm_details" />
          {{ t('addSub.confirmDetails') }}
        </label>
        <label class="check-row">
          <input type="checkbox" v-model="confirm_tos" />
          {{ t('addSub.acceptPrefix') }}
          <a href="/terms" target="_blank" rel="noopener noreferrer">{{ t('addSub.termsOfService') }}</a>
          {{ t('addSub.and') }}
          <a href="/privacy" target="_blank" rel="noopener noreferrer">{{ t('addSub.privacyPolicy') }}</a>.
        </label>
      </div>

      <div class="form-actions">
        <button
          class="btn btn-primary"
          :disabled="!confirm_details || !confirm_tos || submitting"
          @click="confirmOrder"
        >
          {{ submitting ? (isTrial ? t('addSub.startingTrial') : t('addSub.redirectingToPayment')) : (isTrial ? t('addSub.confirmOrder') : t('addSub.continueToPayment')) }}
        </button>
      </div>
    </section>

    <!-- STEP 5: Confirmation -->
    <section v-if="checkoutStatus === null && step === 5" class="order-section">
      <div class="confirm-icon">✓</div>
      <h2 class="confirm-h2">{{ t('addSub.trialStartedTitle') }}</h2>
      <p class="confirm-sub">{{ t('addSub.trialStartedSub') }}</p>

      <div class="review-block">
        <div class="review-row"><span>{{ t('addSub.subscription') }}</span><b>{{ createdSub?.service_name }}</b></div>
        <div class="review-row"><span>{{ t('addSub.plan') }}</span><b>{{ createdSub ? cap(createdSub.tier ?? '') : '-' }}</b></div>
        <div class="review-row"><span>{{ t('addSub.billing') }}</span><b>{{ createdSub ? cap(createdSub.billing_period ?? '') : '-' }}</b></div>
        <div class="review-row">
          <span>{{ t('addSub.status') }}</span>
          <b class="status-badge status-active">{{ t('addSub.trial') }}</b>
        </div>
        <div class="review-row" v-if="createdSub?.trial_ends_at">
          <span>{{ t('addSub.trialEnds') }}</span>
          <b>{{ formatDate(createdSub.trial_ends_at) }}</b>
        </div>
      </div>

      <p class="confirm-next">
        {{ t('addSub.confirmNext') }}
      </p>

      <div class="confirm-actions">
        <router-link to="/subscriptions" class="btn btn-primary">{{ t('addSub.goToServices') }}</router-link>
        <router-link to="/dashboard" class="btn btn-outline">{{ t('addSub.goToDashboard') }}</router-link>
        <button class="btn btn-ghost" @click="resetFlow">{{ t('addSub.addAnother') }}</button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import {
  getServicePlans, getTrialEligibility, createTrialSubscription, createCheckoutSession, getSubscriptions,
  type ServicePlan, type Subscription, type BillingPeriod, type TrialEligibility,
} from '@/services/subscriptions'
import { getCountries, getCompany, type Country, type Company } from '@/services/billing'
import { authSession } from '@/stores/authSession'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const SERVICE_DESCRIPTIONS = computed<Record<string, string>>(() => ({
  welco: t('addSub.welcoDescription'),
}))

const step = ref(1)
const stepLabels = computed(() => [
  t('addSub.step1Label'),
  t('addSub.step2Label'),
  t('addSub.step3Label'),
  t('addSub.step4Label'),
  t('addSub.step5Label'),
])

const plans = ref<ServicePlan[]>([])
const error = ref('')
const submitting = ref(false)
const trialEligibility = ref<TrialEligibility>({ welco: false })
// null = normal wizard; 'finalizing' / 'cancelled' = returned from Stripe Checkout
const checkoutStatus = ref<'finalizing' | 'cancelled' | null>(null)

// Step 1
const selectedService = ref<{ service_key: string; service_name: string; description: string; from_monthly: number } | null>(null)

// Step 2
const billing = ref<BillingPeriod>('monthly')
const selectedPlan = ref<ServicePlan | null>(null)
const isTrial = ref(false)

const trialEligibleForSelected = computed(() => {
  const key = selectedService.value?.service_key.toLowerCase()
  if (key === 'welco') return trialEligibility.value.welco
  return false
})

// Step 3
const company = ref<Company | null>(null)
const countries = ref<Country[]>([])
const loadingBilling = ref(true)

function countryName(countryId: number | null): string {
  if (countryId == null) return '-'
  return countries.value.find((c) => c.id === countryId)?.name ?? '-'
}

async function reloadBilling() {
  loadingBilling.value = true
  try {
    const [cmp, ctrs] = await Promise.all([getCompany(), getCountries()])
    company.value = cmp
    countries.value = ctrs
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('addSub.errorLoadBilling')
  } finally {
    loadingBilling.value = false
  }
}

// Step 4
const confirm_details = ref(false)
const confirm_tos = ref(false)

// Step 5
const createdSub = ref<Subscription | null>(null)

interface ServiceGroup {
  service_key: string
  service_name: string
  description: string
  from_monthly: number
}

const serviceGroups = computed<ServiceGroup[]>(() => {
  const seen = new Map<string, ServiceGroup>()
  for (const p of plans.value) {
    const key = p.service_key.toLowerCase()
    if (!seen.has(key)) {
      seen.set(key, {
        service_key: p.service_key,
        service_name: p.service_name,
        description: SERVICE_DESCRIPTIONS.value[key] ?? '',
        from_monthly: p.monthly_price,
      })
    } else {
      const g = seen.get(key)!
      if (p.monthly_price < g.from_monthly) g.from_monthly = p.monthly_price
    }
  }
  return Array.from(seen.values())
})

const plansForService = computed(() =>
  selectedService.value
    ? plans.value.filter((p) => p.service_key.toLowerCase() === selectedService.value!.service_key.toLowerCase())
    : []
)

function selectService(svc: ServiceGroup) {
  selectedService.value = svc
  selectedPlan.value = null
  isTrial.value = false
  step.value = 2
}

function selectPlan(plan: ServicePlan) {
  selectedPlan.value = plan
  isTrial.value = false
  step.value = 3
  reloadBilling()
}

function selectTrial() {
  const businessPlan = plansForService.value.find((p) => p.tier.toLowerCase() === 'business')
  if (!businessPlan) return
  selectedPlan.value = businessPlan
  billing.value = 'monthly'
  isTrial.value = true
  step.value = 3
  reloadBilling()
}

function goToReview() {
  step.value = 4
}

async function confirmOrder() {
  if (!selectedService.value || !selectedPlan.value) return
  submitting.value = true
  error.value = ''
  try {
    if (isTrial.value) {
      const sub = await createTrialSubscription(selectedService.value.service_key)
      createdSub.value = sub
      step.value = 5
    } else {
      // Remember how many subscriptions exist now, so on return from Stripe we
      // can tell a new one has actually appeared rather than guessing.
      const before = await getSubscriptions()
      sessionStorage.setItem('welcochat_checkout_pending_count', String(before.length))
      const checkoutUrl = await createCheckoutSession(selectedPlan.value.id, billing.value)
      window.location.href = checkoutUrl
    }
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('addSub.errorPlaceOrder')
  } finally {
    submitting.value = false
  }
}

function resetFlow() {
  step.value = 1
  selectedService.value = null
  selectedPlan.value = null
  billing.value = 'monthly'
  isTrial.value = false
  confirm_details.value = false
  confirm_tos.value = false
  createdSub.value = null
  error.value = ''
  checkoutStatus.value = null
}

async function pollForNewSubscription() {
  const beforeRaw = sessionStorage.getItem('welcochat_checkout_pending_count')
  const before = beforeRaw ? Number(beforeRaw) : -1
  for (let attempt = 0; attempt < 10; attempt++) {
    await new Promise((resolve) => setTimeout(resolve, 2000))
    try {
      const subs = await getSubscriptions()
      if (before === -1 || subs.length > before) break
    } catch {
      // transient — keep trying until attempts run out
    }
  }
  sessionStorage.removeItem('welcochat_checkout_pending_count')
  router.push('/subscriptions')
}

function cap(s: string) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : '' }
function fmt(n: number) { return Math.round(n).toLocaleString('en-US') }
function formatDate(iso: string) { return new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) }

onMounted(async () => {
  if (route.query.checkout === 'success') {
    checkoutStatus.value = 'finalizing'
    pollForNewSubscription()
    return
  }
  if (route.query.checkout === 'cancelled') {
    checkoutStatus.value = 'cancelled'
    return
  }
  try {
    const [svcPlans, eligibility] = await Promise.all([getServicePlans(), getTrialEligibility()])
    plans.value = svcPlans
    trialEligibility.value = eligibility
  } catch {
    error.value = t('addSub.errorLoadOptions')
  }
})
</script>

<style scoped>
.stepper {
  display: flex;
  gap: 0;
  margin: 1.25rem 0 2rem;
  overflow-x: auto;
}
.stepper-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  min-width: 60px;
  gap: 0.35rem;
  position: relative;
}
.stepper-item + .stepper-item::before {
  content: '';
  position: absolute;
  top: 14px;
  right: 50%;
  width: 100%;
  height: 2px;
  background: rgba(148, 163, 184, 0.25);
  z-index: 0;
}
.stepper-item.is-done + .stepper-item::before { background: var(--primary, #2563eb); }
.stepper-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid rgba(148, 163, 184, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.78rem;
  font-weight: 700;
  background: var(--surface, #1e293b);
  position: relative;
  z-index: 1;
}
.stepper-item.is-active .stepper-dot { border-color: var(--primary, #2563eb); color: var(--primary, #2563eb); }
.stepper-item.is-done .stepper-dot { border-color: var(--primary, #2563eb); background: var(--primary, #2563eb); color: #fff; }
.stepper-label {
  font-size: 0.7rem;
  color: rgba(148, 163, 184, 0.7);
  text-align: center;
  white-space: nowrap;
}
.stepper-item.is-active .stepper-label { color: var(--primary, #2563eb); font-weight: 600; }

.order-section { max-width: 760px; }
.step-subtitle { color: rgba(148, 163, 184, 0.85); margin: 0.25rem 0 1.25rem; }
.back-btn {
  background: none; border: 0; color: var(--blue-2, #60a5fa);
  cursor: pointer; font: inherit; padding: 0; margin-bottom: 1rem;
}

/* Step 1 – service cards */
.service-cards { display: flex; flex-wrap: wrap; gap: 1rem; }
.service-card {
  flex: 1 1 200px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 10px;
  padding: 1rem 1.1rem;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  position: relative;
  transition: border-color 0.15s, transform 0.1s;
}
.service-card:hover { border-color: rgba(59, 130, 246, 0.6); transform: translateY(-2px); }
.sc-name { font-weight: 700; font-size: 0.95rem; }
.sc-desc { font-size: 0.82rem; color: rgba(148, 163, 184, 0.85); }
.sc-price { color: var(--blue-2, #60a5fa); font-weight: 700; font-size: 0.9rem; }
.sc-cta { font-size: 0.82rem; color: var(--blue-2, #60a5fa); font-weight: 600; }

/* Step 2 – trial banner */
.trial-banner {
  display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap;
  border: 1px solid rgba(22, 163, 74, 0.35); background: rgba(22, 163, 74, 0.08);
  border-radius: 10px; padding: 1rem 1.25rem; margin: 0.75rem 0 0;
}
.trial-banner-text strong { font-size: 0.95rem; }
.trial-banner-text p { margin: 0.2rem 0 0; font-size: 0.82rem; color: rgba(148, 163, 184, 0.85); }

/* Step 2 – plan cards */
.billing-toggle { display: inline-flex; align-items: center; gap: 0.5rem; margin: 0.75rem 0 0.4rem; flex-wrap: wrap; }
.billing-opt {
  padding: 0.35rem 1rem; border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  background: transparent; color: inherit; cursor: pointer;
  font-weight: 600; font-size: 0.85rem;
}
.billing-opt.active { background: rgba(59, 130, 246, 0.15); border-color: rgba(59, 130, 246, 0.5); color: var(--blue-2, #60a5fa); }
.save-badge { background: #16a34a; color: #fff; font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 999px; }
.billing-note { font-size: 0.8rem; color: rgba(148, 163, 184, 0.75); margin: 0 0 0.75rem; }
.plan-cards { display: flex; flex-wrap: wrap; gap: 1rem; margin-top: 0.75rem; }
.plan-card {
  flex: 1 1 190px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 10px; padding: 1.1rem;
  display: flex; flex-direction: column; gap: 0.5rem;
  cursor: pointer; transition: border-color 0.15s;
}
.plan-card:hover, .plan-card.is-selected { border-color: rgba(59, 130, 246, 0.6); }
.pc-tier { font-weight: 700; font-size: 0.95rem; }
.pc-price { color: var(--blue-2, #60a5fa); font-weight: 700; font-size: 1.05rem; }
.pc-annual { font-size: 0.78rem; color: rgba(148, 163, 184, 0.8); }
.pc-btn { margin-top: auto; }

/* Step 3 – billing details (read-only, from company profile) */
.field-hint { font-size: 0.82rem; color: rgba(148, 163, 184, 0.75); margin: 0.5rem 0 0; }
.field-hint a { color: var(--blue-2, #60a5fa); }
.form-actions { margin-top: 0.5rem; display: flex; gap: 0.75rem; flex-wrap: wrap; }

/* Step 4 – review */
.review-h2 { font-size: 1.1rem; margin: 0 0 1rem; }
.review-block { border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
.review-block-title { font-weight: 700; font-size: 0.85rem; color: rgba(148, 163, 184, 0.8); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.6rem; }
.review-row { display: flex; justify-content: space-between; gap: 1rem; font-size: 0.88rem; padding: 0.2rem 0; }
.review-row span { color: rgba(148, 163, 184, 0.8); }
.review-vat { font-size: 0.78rem; opacity: 0.7; }
.review-next { font-size: 0.85rem; color: rgba(148, 163, 184, 0.85); margin: 0.4rem 0; }
.review-checks { display: flex; flex-direction: column; gap: 0.6rem; margin: 1.25rem 0 1rem; }
.check-row { display: flex; align-items: flex-start; gap: 0.6rem; font-size: 0.88rem; cursor: pointer; }
.check-row input { margin-top: 2px; flex-shrink: 0; }
.check-row a { color: var(--blue-2, #60a5fa); text-decoration: underline; }

/* Step 5 – confirmation */
.confirm-icon { font-size: 2.5rem; color: #4ade80; margin-bottom: 0.5rem; }
.confirm-h2 { font-size: 1.3rem; margin: 0 0 0.4rem; }
.confirm-sub { color: rgba(148, 163, 184, 0.85); margin: 0 0 1.25rem; }
.confirm-next { font-size: 0.85rem; color: rgba(148, 163, 184, 0.85); margin: 1rem 0 0; }
.confirm-actions { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-top: 1.25rem; }
.status-badge { padding: 2px 8px; border-radius: 999px; font-size: 0.78rem; font-weight: 700; }
.status-active { background: rgba(22, 163, 74, 0.15); color: #4ade80; border: 1px solid rgba(22, 163, 74, 0.3); }

.form-error { color: #f87171; margin-bottom: 1rem; font-size: 0.9rem; }

.btn { display: inline-flex; align-items: center; justify-content: center; padding: 0.55rem 1.1rem; border-radius: 6px; font: inherit; font-weight: 600; font-size: 0.88rem; cursor: pointer; border: 1px solid transparent; text-decoration: none; transition: opacity 0.15s; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: var(--primary, #2563eb); color: #fff; }
.btn-outline { background: transparent; border-color: rgba(148, 163, 184, 0.4); color: inherit; }
.btn-ghost { background: transparent; color: var(--blue-2, #60a5fa); }

@media (max-width: 600px) {
  .stepper-label { display: none; }
  .service-cards, .plan-cards { flex-direction: column; }
  .confirm-actions { flex-direction: column; }
}
</style>
