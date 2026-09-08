<template>
  <div class="page">
    <h1>{{ t('subscriptions.title') }}</h1>

    <p v-if="error" class="input-hint" role="alert">{{ error }}</p>

    <div v-if="loading" class="input-hint">{{ t('subscriptions.loading') }}</div>

    <!-- Empty state: no subscription -->
    <div v-else-if="instances.length === 0" class="empty-state">
      <p class="empty-text">{{ t('subscriptions.noSubscriptions') }}</p>
      <div class="empty-actions">
        <router-link to="/subscriptions/add" class="btn btn-primary">{{ t('dashboard.addSubscription') }}</router-link>
      </div>
    </div>

    <!-- Service instance cards -->
    <section v-else class="services-grid">
      <article v-for="inst in instances" :key="inst.id" class="svc-card">
        <div class="svc-header">
          <div class="svc-name">{{ inst.service_name }}</div>
          <span class="svc-status-badge" :class="statusClass(inst.setup_status)">
            {{ statusLabel(inst.setup_status) }}
          </span>
        </div>
        <div class="svc-meta">
          <span class="svc-tier-badge">{{ inst.tier }}</span>
          <span v-if="subscriptionFor(inst.subscription_id)?.status === 'trialing'" class="svc-trial-badge">
            {{ t('subscriptions.trialEnds', { date: formatDate(subscriptionFor(inst.subscription_id)?.trial_ends_at) }) }}
          </span>
        </div>
        <div v-if="subscriptionFor(inst.subscription_id)?.start_date" class="svc-dates">
          {{ t('subscriptions.started', { date: formatDate(subscriptionFor(inst.subscription_id)?.start_date) }) }}
          <span v-if="subscriptionFor(inst.subscription_id)?.pending_tier">
            · {{ t('subscriptions.downgradesTo', { tier: subscriptionFor(inst.subscription_id)?.pending_tier, date: formatDate(subscriptionFor(inst.subscription_id)?.end_date) }) }}
          </span>
          <span v-else-if="subscriptionFor(inst.subscription_id)?.end_date">
            · {{ t('subscriptions.renews', { date: formatDate(subscriptionFor(inst.subscription_id)?.end_date) }) }}
          </span>
        </div>
        <div class="svc-footer">
          <button
            class="btn"
            :class="ctaClass(inst.setup_status)"
            @click="handleCta(inst)"
          >
            {{ ctaLabel(inst.setup_status) }}
          </button>
          <router-link :to="`/subscriptions/${inst.subscription_id}/change-plan`" class="btn btn-outline">{{ t('subscriptions.changePlan') }}</router-link>
        </div>
      </article>
    </section>

    <div v-if="!loading && instances.length > 0" class="services-actions">
      <router-link to="/subscriptions/add" class="btn btn-outline">{{ t('dashboard.addSubscription') }}</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { getServiceInstances, getSubscriptions, type ServiceInstance, type Subscription } from '@/services/subscriptions'

const { t } = useI18n()
const router = useRouter()
const instances = ref<ServiceInstance[]>([])
const subscriptions = ref<Subscription[]>([])
const loading = ref(true)
const error = ref('')

function subscriptionFor(subId: number): Subscription | undefined {
  return subscriptions.value.find((s) => s.id === subId)
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    not_configured: t('serviceStatus.notConfigured'),
    setup_in_progress: t('serviceStatus.setupInProgress'),
    pending_review: t('serviceStatus.pendingReview'),
    running: t('serviceStatus.running'),
    paused: t('serviceStatus.paused'),
    error: t('subscriptions.needsAttention'),
    cancelled: t('serviceStatus.cancelled'),
  }
  return map[status] ?? status
}

function statusClass(status: string): string {
  if (status === 'running') return 'badge-running'
  if (status === 'error') return 'badge-error'
  if (status === 'not_configured') return 'badge-neutral'
  if (status === 'setup_in_progress' || status === 'pending_review') return 'badge-progress'
  return 'badge-neutral'
}

function ctaLabel(status: string): string {
  if (status === 'not_configured') return t('dashboard.ctaSetUp')
  if (status === 'setup_in_progress') return t('dashboard.ctaContinueSetup')
  if (status === 'running') return t('dashboard.ctaManage')
  if (status === 'error') return t('dashboard.ctaFixIssue')
  return t('dashboard.ctaViewDetails')
}

function ctaClass(status: string): string {
  if (status === 'running') return 'btn-outline'
  if (status === 'error') return 'btn-error'
  return 'btn-primary'
}

function handleCta(inst: ServiceInstance) {
  router.push(`/setup/${inst.service_key}/${inst.id}`)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [inst, subs] = await Promise.all([getServiceInstances(), getSubscriptions()])
    instances.value = inst
    subscriptions.value = subs
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('subscriptions.errorLoad')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.services-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1rem;
  margin-top: 1.25rem;
  max-width: 900px;
}
.svc-card {
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 10px;
  padding: 1rem 1.1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.svc-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}
.svc-name { font-weight: 700; font-size: 0.95rem; flex: 1; }
.svc-footer { margin-top: 0.5rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }

.svc-meta { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.svc-tier-badge {
  padding: 2px 9px; border-radius: 999px; font-size: 0.72rem; font-weight: 700;
  background: rgba(37, 99, 235, 0.12); color: var(--blue-2, #60a5fa); border: 1px solid rgba(37, 99, 235, 0.3);
}
.svc-trial-badge {
  padding: 2px 9px; border-radius: 999px; font-size: 0.72rem; font-weight: 700;
  background: rgba(234, 179, 8, 0.15); color: #fbbf24; border: 1px solid rgba(234, 179, 8, 0.3);
}
.svc-dates { font-size: 0.78rem; color: rgba(148, 163, 184, 0.75); }

.svc-status-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  white-space: nowrap;
  flex-shrink: 0;
}
.badge-running { background: rgba(22, 163, 74, 0.15); color: #4ade80; border: 1px solid rgba(22, 163, 74, 0.3); }
.badge-error { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
.badge-progress { background: rgba(234, 179, 8, 0.15); color: #fbbf24; border: 1px solid rgba(234, 179, 8, 0.3); }
.badge-neutral { background: rgba(148, 163, 184, 0.1); color: rgba(148, 163, 184, 0.85); border: 1px solid rgba(148, 163, 184, 0.2); }

.empty-state { margin-top: 2rem; }
.empty-text { color: rgba(148, 163, 184, 0.85); margin-bottom: 1.1rem; }
.empty-actions { display: flex; gap: 0.75rem; flex-wrap: wrap; }

.services-actions { margin-top: 1.5rem; }

.btn { display: inline-flex; align-items: center; justify-content: center; padding: 0.5rem 1rem; border-radius: 6px; font: inherit; font-weight: 600; font-size: 0.85rem; cursor: pointer; border: 1px solid transparent; text-decoration: none; transition: opacity 0.15s; }
.btn-primary { background: var(--primary, #2563eb); color: #fff; }
.btn-outline { background: transparent; border-color: rgba(148, 163, 184, 0.35); color: inherit; }
.btn-error { background: rgba(239, 68, 68, 0.15); color: #f87171; border-color: rgba(239, 68, 68, 0.3); }

@media (max-width: 600px) {
  .services-grid { grid-template-columns: 1fr; }
}
</style>
