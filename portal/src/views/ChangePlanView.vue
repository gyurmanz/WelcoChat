<template>
  <div class="page">
    <h1>{{ t('changePlan.title') }}</h1>

    <div v-if="loading" class="input-hint">{{ t('common.loading') }}</div>

    <template v-else-if="loadError">
      <p class="form-error" role="alert">{{ loadError }}</p>
      <router-link to="/subscriptions" class="btn btn-primary">{{ t('addSub.goToServices') }}</router-link>
    </template>

    <template v-else>
      <p class="step-subtitle">
        {{ t('changePlan.currentPlanFor') }} <strong>{{ currentSubscription?.service_name }}</strong>:
        <strong>{{ cap(currentSubscription?.tier ?? '') }}</strong> ({{ cap(currentSubscription?.billing_period ?? '') }})
      </p>
      <p v-if="currentSubscription?.pending_tier" class="pending-note">
        {{ t('changePlan.alreadyScheduled') }} <strong>{{ cap(currentSubscription.pending_tier) }}</strong>
        {{ t('changePlan.on') }} {{ formatDate(currentSubscription.end_date) }}.
      </p>

      <div class="billing-toggle">
        <button class="billing-opt" :class="{ active: billing === 'monthly' }" @click="billing = 'monthly'">{{ t('addSub.monthly') }}</button>
        <button class="billing-opt" :class="{ active: billing === 'annual' }" @click="billing = 'annual'">{{ t('addSub.annual') }}</button>
        <span v-if="billing === 'annual'" class="save-badge">{{ t('addSub.save20') }}</span>
      </div>

      <div class="plan-cards">
        <div
          v-for="plan in plansForService"
          :key="plan.tier"
          class="plan-card"
          :class="{ 'is-selected': selectedPlan?.id === plan.id, 'is-current': isCurrent(plan) }"
          @click="selectedPlan = plan"
          role="button"
          :tabindex="0"
          @keyup.enter="selectedPlan = plan"
        >
          <div class="pc-tier">{{ cap(plan.tier) }}<span v-if="isCurrent(plan)" class="pc-current-badge">{{ t('changePlan.current') }}</span></div>
          <div class="pc-price">{{ t('addSub.pricePerMo', { price: fmt(billing === 'annual' ? plan.annual_price : plan.monthly_price) }) }}</div>
          <div v-if="billing === 'annual'" class="pc-annual">{{ t('addSub.billedAnnually') }}</div>
        </div>
      </div>

      <p v-if="isDowngrade" class="downgrade-warning">
        {{ t('changePlan.downgradeWarning', { date: formatDate(currentSubscription?.end_date), tier: cap(currentSubscription?.tier ?? '') }) }}
      </p>

      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <p v-if="success" class="draft-saved">{{ success }}</p>

      <div class="form-actions">
        <button
          class="btn btn-primary"
          :disabled="!canSubmit || submitting"
          @click="submit"
        >
          {{ submitting ? t('changePlan.changing') : t('changePlan.confirmChange') }}
        </button>
        <router-link to="/subscriptions" class="btn btn-outline">{{ t('changePlan.cancel') }}</router-link>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import {
  getServicePlans, getSubscriptions, changePlan,
  type ServicePlan, type Subscription, type BillingPeriod,
} from '@/services/subscriptions'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const subscriptionId = computed(() => Number(route.params.id))

const loading = ref(true)
const loadError = ref('')
const error = ref('')
const success = ref('')
const submitting = ref(false)

const plans = ref<ServicePlan[]>([])
const currentSubscription = ref<Subscription | null>(null)
const billing = ref<BillingPeriod>('monthly')
const selectedPlan = ref<ServicePlan | null>(null)

const plansForService = computed(() =>
  currentSubscription.value
    ? plans.value.filter((p) => p.service_key.toLowerCase() === currentSubscription.value!.service_key?.toLowerCase())
    : []
)

function isCurrent(plan: ServicePlan): boolean {
  return !!currentSubscription.value
    && plan.tier === currentSubscription.value.tier
    && billing.value === currentSubscription.value.billing_period
}

const isDowngrade = computed(() => {
  if (!selectedPlan.value || !currentSubscription.value) return false
  const rank: Record<string, number> = { basic: 0, business: 1, enterprise: 2 }
  const currentRank = rank[(currentSubscription.value.tier ?? '').toLowerCase()] ?? 0
  const newRank = rank[selectedPlan.value.tier.toLowerCase()] ?? 0
  return newRank < currentRank
})

const canSubmit = computed(() => {
  if (!selectedPlan.value || !currentSubscription.value) return false
  const sameAsCurrent = selectedPlan.value.tier === currentSubscription.value.tier && billing.value === currentSubscription.value.billing_period
  if (!sameAsCurrent) return true
  return !!currentSubscription.value.pending_tier // only useful to cancel a pending downgrade
})

async function submit() {
  if (!selectedPlan.value) return
  const hadPendingBefore = !!currentSubscription.value?.pending_tier
  submitting.value = true
  error.value = ''
  success.value = ''
  try {
    const updated = await changePlan(subscriptionId.value, { new_service_id: selectedPlan.value.id, billing_period: billing.value })
    if (updated.pending_tier) {
      success.value = t('changePlan.downgradeScheduled', { tier: cap(updated.pending_tier), date: formatDate(updated.end_date) })
    } else if (hadPendingBefore) {
      success.value = t('changePlan.downgradeCancelled')
    } else {
      success.value = t('changePlan.planChanged')
    }
    setTimeout(() => router.push('/subscriptions'), 1600)
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('changePlan.errorChangePlan')
  } finally {
    submitting.value = false
  }
}

function cap(s: string) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : '' }
function fmt(n: number) { return Math.round(n).toLocaleString('en-US') }
function formatDate(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

onMounted(async () => {
  loading.value = true
  loadError.value = ''
  try {
    const [allPlans, subs] = await Promise.all([getServicePlans(), getSubscriptions()])
    plans.value = allPlans
    const sub = subs.find((s) => s.id === subscriptionId.value)
    if (!sub) {
      loadError.value = t('changePlan.errorNotFound')
      return
    }
    currentSubscription.value = sub
    billing.value = (sub.billing_period as BillingPeriod) || 'monthly'
  } catch (err: unknown) {
    loadError.value = err instanceof Error ? err.message : t('changePlan.errorLoadOptions')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.step-subtitle { color: rgba(148, 163, 184, 0.85); margin: 0.25rem 0 1.25rem; }
.pending-note {
  font-size: 0.85rem; color: #fbbf24; background: rgba(234, 179, 8, 0.1);
  border: 1px solid rgba(234, 179, 8, 0.3); border-radius: 8px; padding: 0.6rem 0.9rem; margin: -0.5rem 0 1.25rem;
}

.billing-toggle { display: inline-flex; align-items: center; gap: 0.5rem; margin: 0.75rem 0 1rem; flex-wrap: wrap; }
.billing-opt {
  padding: 0.35rem 1rem; border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  background: transparent; color: inherit; cursor: pointer;
  font-weight: 600; font-size: 0.85rem;
}
.billing-opt.active { background: rgba(59, 130, 246, 0.15); border-color: rgba(59, 130, 246, 0.5); color: var(--blue-2, #60a5fa); }
.save-badge { background: #16a34a; color: #fff; font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 999px; }

.plan-cards { display: flex; flex-wrap: wrap; gap: 1rem; margin-top: 0.5rem; max-width: 640px; }
.plan-card {
  flex: 1 1 180px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 10px; padding: 1.1rem;
  display: flex; flex-direction: column; gap: 0.5rem;
  cursor: pointer; transition: border-color 0.15s;
}
.plan-card:hover, .plan-card.is-selected { border-color: rgba(59, 130, 246, 0.6); }
.plan-card.is-current { border-style: dashed; }
.pc-tier { font-weight: 700; font-size: 0.95rem; display: flex; align-items: center; gap: 0.5rem; }
.pc-current-badge { font-size: 0.68rem; font-weight: 700; background: rgba(148, 163, 184, 0.15); color: rgba(148, 163, 184, 0.9); padding: 1px 7px; border-radius: 999px; }
.pc-price { color: var(--blue-2, #60a5fa); font-weight: 700; font-size: 1.05rem; }
.pc-annual { font-size: 0.78rem; color: rgba(148, 163, 184, 0.8); }

.downgrade-warning {
  margin-top: 1rem; max-width: 640px; font-size: 0.85rem; color: #fbbf24;
  background: rgba(234, 179, 8, 0.1); border: 1px solid rgba(234, 179, 8, 0.3);
  border-radius: 8px; padding: 0.75rem 1rem;
}

.form-error { color: #f87171; margin-bottom: 1rem; font-size: 0.9rem; }
.draft-saved { color: #4ade80; font-size: 0.85rem; margin-top: 0.75rem; }
.form-actions { margin-top: 1.25rem; display: flex; gap: 0.75rem; flex-wrap: wrap; }

.btn { display: inline-flex; align-items: center; justify-content: center; padding: 0.55rem 1.1rem; border-radius: 6px; font: inherit; font-weight: 600; font-size: 0.88rem; cursor: pointer; border: 1px solid transparent; text-decoration: none; transition: opacity 0.15s; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: var(--primary, #2563eb); color: #fff; }
.btn-outline { background: transparent; border-color: rgba(148, 163, 184, 0.4); color: inherit; }

@media (max-width: 600px) {
  .plan-cards { flex-direction: column; }
}
</style>
