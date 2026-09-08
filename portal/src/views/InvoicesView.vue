<template>
  <div class="page">
    <div class="page-header">
      <h1>{{ t('invoices.title') }}</h1>
      <button class="btn btn-outline" :disabled="openingPortal" @click="openPortal">
        {{ openingPortal ? t('invoices.opening') : t('invoices.manageBilling') }}
      </button>
    </div>

    <div class="input-group" v-if="error">
      <p class="input-hint" role="alert" aria-live="polite">{{ error }}</p>
    </div>

    <section class="subs-section" :aria-busy="loading ? 'true' : 'false'">
      <p v-if="loading" class="input-hint">{{ t('invoices.loading') }}</p>

      <div v-else-if="invoices.length === 0" class="empty-state">
        <p class="empty-title">{{ t('invoices.emptyTitle') }}</p>
        <p class="empty-sub">{{ t('invoices.emptySub') }}</p>
        <router-link to="/subscriptions/add" class="btn btn-primary">{{ t('dashboard.addSubscription') }}</router-link>
      </div>

      <div v-else class="table-wrap">
        <table class="subs-table">
          <caption class="sr-only">{{ t('invoices.tableCaption') }}</caption>
          <thead>
            <tr>
              <th scope="col">{{ t('invoices.invoiceNumber') }}</th>
              <th scope="col">{{ t('invoices.date') }}</th>
              <th scope="col">{{ t('invoices.amount') }}</th>
              <th scope="col">{{ t('invoices.status') }}</th>
              <th scope="col">{{ t('invoices.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="inv in invoices" :key="inv.id">
              <td>{{ inv.number ?? '-' }}</td>
              <td>{{ formatDate(inv.issued_date) }}</td>
              <td>{{ formatAmount(inv.amount, inv.currency) }}</td>
              <td>
                <span class="inv-badge" :class="statusClass(inv.status)">{{ statusLabel(inv.status) }}</span>
              </td>
              <td class="inv-actions">
                <a
                  v-if="inv.pdf_url"
                  :href="inv.pdf_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="inv-link"
                >{{ t('invoices.downloadPdf') }}</a>
                <span v-else class="inv-muted">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getInvoices, type Invoice } from '@/services/subscriptions'
import { getPortalSessionUrl } from '@/services/billing'

const { t } = useI18n()

const invoices = ref<Invoice[]>([])
const loading = ref(true)
const error = ref('')
const openingPortal = ref(false)

async function openPortal() {
  openingPortal.value = true
  error.value = ''
  try {
    const url = await getPortalSessionUrl()
    window.location.href = url
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('invoices.errorOpenPortal')
  } finally {
    openingPortal.value = false
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString('en-GB')
}

function formatAmount(amount: number | null, currency: string | null): string {
  if (amount == null) return '-'
  const cur = (currency ?? '').toUpperCase()
  if (/^[A-Z]{3}$/.test(cur)) {
    try {
      return new Intl.NumberFormat('en-GB', { style: 'currency', currency: cur }).format(amount)
    } catch {
      // invalid ISO currency code -> fall through to plain formatting
    }
  }
  return `${amount.toLocaleString('en-GB')}${cur ? ' ' + cur : ''}`
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    paid: t('invoices.statusPaid'),
    unpaid: t('invoices.statusUnpaid'),
    overdue: t('invoices.statusOverdue'),
    cancelled: t('invoices.statusCancelled'),
  }
  return map[(status ?? '').toLowerCase()] ?? status ?? '-'
}

function statusClass(status: string): string {
  const s = (status ?? '').toLowerCase()
  if (s === 'paid') return 'badge-paid'
  if (s === 'overdue') return 'badge-overdue'
  if (s === 'unpaid') return 'badge-unpaid'
  return 'badge-neutral'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    invoices.value = await getInvoices()
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('invoices.errorLoad')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}
.subs-section {
  margin-top: 1.5rem;
  max-width: 820px;
}
.table-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.subs-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 560px;
}
.subs-table th,
.subs-table td {
  text-align: left;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
}
.empty-state { margin-top: 1.5rem; }
.empty-title { font-weight: 600; margin-bottom: 0.4rem; }
.empty-sub { color: rgba(148, 163, 184, 0.8); font-size: 0.88rem; margin-bottom: 1.1rem; }
.btn { display: inline-flex; align-items: center; padding: 0.5rem 1.1rem; border-radius: 6px; font: inherit; font-weight: 600; font-size: 0.88rem; cursor: pointer; border: 1px solid transparent; text-decoration: none; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: var(--primary, #2563eb); color: #fff; }
.btn-outline { background: transparent; border-color: rgba(148, 163, 184, 0.4); color: inherit; }
.inv-actions { white-space: nowrap; }
.inv-badge {
  padding: 2px 8px; border-radius: 999px; font-size: 0.78rem; font-weight: 700;
}
.badge-paid { background: rgba(22, 163, 74, 0.15); color: #4ade80; border: 1px solid rgba(22, 163, 74, 0.3); }
.badge-overdue { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
.badge-unpaid { background: rgba(234, 179, 8, 0.15); color: #fbbf24; border: 1px solid rgba(234, 179, 8, 0.3); }
.badge-neutral { background: rgba(148, 163, 184, 0.1); color: rgba(148, 163, 184, 0.8); border: 1px solid rgba(148, 163, 184, 0.2); }
.inv-link { color: var(--primary, #2563eb); text-decoration: none; font-size: 0.85rem; }
.inv-link:hover { text-decoration: underline; }
.inv-muted { color: rgba(148, 163, 184, 0.5); }
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
