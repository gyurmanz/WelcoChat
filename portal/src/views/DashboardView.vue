<template>
  <div class="page">
    <h1>Dashboard</h1>
    <p class="dash-intro">
      Welcome to your WelcoChat portal. Manage your subscriptions, services, invoices and
      workflow setup from here.
    </p>

    <p v-if="error" class="input-hint">{{ error }}</p>

    <!-- Summary cards -->
    <div class="summary-cards" v-if="!loading">
      <div class="summary-card">
        <div class="sc-value">{{ activeSubscriptions }}</div>
        <div class="sc-label">Active subscriptions</div>
      </div>
      <div class="summary-card">
        <div class="sc-value">{{ servicesToSetUp }}</div>
        <div class="sc-label">Services to set up</div>
      </div>
      <div class="summary-card">
        <div class="sc-value">{{ runningServices }}</div>
        <div class="sc-label">Running services</div>
      </div>
      <div class="summary-card">
        <div class="sc-value">{{ openInvoices > 0 ? openInvoices : '—' }}</div>
        <div class="sc-label">{{ openInvoices > 0 ? 'Open invoices' : 'No open invoices' }}</div>
      </div>
    </div>

    <!-- Your services -->
    <section class="dash-section">
      <h2 class="dash-h2">Your services</h2>

      <div v-if="loading" class="input-hint">Loading…</div>

      <!-- No subscription -->
      <div v-else-if="instances.length === 0" class="empty-state">
        <p class="empty-text">You do not have any active WelcoChat subscriptions yet.</p>
        <div class="empty-actions">
          <router-link to="/subscriptions/add" class="btn btn-primary">Add subscription</router-link>
        </div>
      </div>

      <!-- Service status cards -->
      <div v-else class="svc-cards">
        <article v-for="inst in instances" :key="inst.id" class="svc-card">
          <div class="svc-top">
            <div class="svc-name">{{ inst.service_name }}</div>
            <span class="svc-badge" :class="badgeClass(inst.setup_status)">
              {{ statusLabel(inst.setup_status) }}
            </span>
          </div>
          <div class="svc-meta">Included in: {{ subscriptionLabel(inst.subscription_id) }}</div>
          <button class="btn" :class="ctaClass(inst.setup_status)" @click="router.push(`/setup/${inst.service_key}/${inst.id}`)">
            {{ ctaLabel(inst.setup_status) }}
          </button>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getSubscriptions, getServiceInstances, getInvoices, type Subscription, type ServiceInstance } from '@/services/subscriptions'

const router = useRouter()
const subscriptions = ref<Subscription[]>([])
const instances = ref<ServiceInstance[]>([])
const invoiceCount = ref(0)
const loading = ref(true)
const error = ref('')

const activeSubscriptions = computed(() => subscriptions.value.filter((s) => s.status === 'active' || s.status === 'trialing').length)
const servicesToSetUp = computed(() => instances.value.filter((i) => i.setup_status === 'not_configured' || i.setup_status === 'setup_in_progress').length)
const runningServices = computed(() => instances.value.filter((i) => i.setup_status === 'running').length)
const openInvoices = computed(() => invoiceCount.value)

function subscriptionLabel(subId: number): string {
  const sub = subscriptions.value.find((s) => s.id === subId)
  if (!sub) return 'your subscription'
  const name = sub.service_name ?? 'WelcoChat'
  const tier = sub.tier ? ` ${sub.tier.charAt(0).toUpperCase() + sub.tier.slice(1)}` : ''
  return `${name}${tier}`
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    not_configured: 'Not configured',
    setup_in_progress: 'Setup in progress',
    pending_review: 'Pending review',
    running: 'Running',
    paused: 'Paused',
    error: 'Needs attention',
    cancelled: 'Cancelled',
  }
  return map[status] ?? status
}

function badgeClass(status: string): string {
  if (status === 'running') return 'badge-running'
  if (status === 'error') return 'badge-error'
  if (status === 'setup_in_progress' || status === 'pending_review') return 'badge-progress'
  return 'badge-neutral'
}

function ctaLabel(status: string): string {
  if (status === 'not_configured') return 'Set up'
  if (status === 'setup_in_progress') return 'Continue setup'
  if (status === 'running') return 'Manage'
  if (status === 'error') return 'Fix issue'
  return 'View details'
}

function ctaClass(status: string): string {
  if (status === 'running') return 'btn-outline'
  return 'btn-primary'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [subs, inst, inv] = await Promise.all([
      getSubscriptions(),
      getServiceInstances(),
      getInvoices().catch(() => []),
    ])
    subscriptions.value = subs
    instances.value = inst
    invoiceCount.value = inv.filter((i) => i.status && ['unpaid', 'overdue'].includes(i.status)).length
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Failed to load dashboard.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.dash-intro {
  color: rgba(148, 163, 184, 0.85);
  margin: 0.25rem 0 1.5rem;
  max-width: 600px;
}
.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
  max-width: 760px;
}
.summary-card {
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 10px;
  padding: 1rem 1.1rem;
  background: rgba(30, 41, 59, 0.4);
}
.sc-value {
  font-size: 1.8rem;
  font-weight: 700;
  line-height: 1.1;
  margin-bottom: 0.25rem;
}
.sc-label { font-size: 0.8rem; color: rgba(148, 163, 184, 0.75); }

.dash-section { max-width: 900px; }
.dash-h2 { font-size: 1.05rem; margin: 0 0 0.75rem; }

.empty-state { margin-top: 0.5rem; }
.empty-text { color: rgba(148, 163, 184, 0.85); margin-bottom: 1rem; }
.empty-actions { display: flex; gap: 0.75rem; flex-wrap: wrap; }

.svc-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1rem;
}
.svc-card {
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 10px;
  padding: 1rem 1.1rem;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.svc-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem; }
.svc-name { font-weight: 700; font-size: 0.92rem; flex: 1; }
.svc-meta { font-size: 0.78rem; color: rgba(148, 163, 184, 0.7); }

.svc-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 700;
  white-space: nowrap;
  flex-shrink: 0;
}
.badge-running { background: rgba(22, 163, 74, 0.15); color: #4ade80; border: 1px solid rgba(22, 163, 74, 0.3); }
.badge-error { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
.badge-progress { background: rgba(234, 179, 8, 0.15); color: #fbbf24; border: 1px solid rgba(234, 179, 8, 0.3); }
.badge-neutral { background: rgba(148, 163, 184, 0.1); color: rgba(148, 163, 184, 0.8); border: 1px solid rgba(148, 163, 184, 0.2); }

.btn { display: inline-flex; align-items: center; padding: 0.45rem 0.9rem; border-radius: 6px; font: inherit; font-weight: 600; font-size: 0.82rem; cursor: pointer; border: 1px solid transparent; text-decoration: none; width: fit-content; }
.btn-primary { background: var(--primary, #2563eb); color: #fff; }
.btn-outline { background: transparent; border-color: rgba(148, 163, 184, 0.35); color: inherit; }

@media (max-width: 600px) {
  .summary-cards { grid-template-columns: repeat(2, 1fr); }
  .svc-cards { grid-template-columns: 1fr; }
}
</style>
