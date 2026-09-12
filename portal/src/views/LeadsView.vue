<template>
  <div class="page">
    <h1>{{ t('leads.title') }}</h1>
    <p class="step-subtitle">{{ t('leads.intro') }}</p>

    <p v-if="error" class="input-hint" role="alert">{{ error }}</p>
    <div v-if="loading" class="input-hint">{{ t('common.loading') }}</div>

    <template v-else>
      <div v-if="leads.length === 0" class="empty-state">
        <p class="empty-text">{{ t('leads.empty') }}</p>
      </div>

      <template v-else>
        <div class="leads-actions">
          <button class="btn btn-outline btn-sm" @click="exportCsv">{{ t('leads.exportCsv') }}</button>
        </div>

        <div class="leads-table-wrap">
          <table class="leads-table">
            <thead>
              <tr>
                <th>{{ t('leads.received') }}</th>
                <th>{{ t('leads.name') }}</th>
                <th>{{ t('leads.contact') }}</th>
                <th>{{ t('leads.message') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="lead in leads" :key="lead.id">
                <td class="nowrap">{{ formatDate(lead.created) }}</td>
                <td>{{ lead.name || '—' }}</td>
                <td>
                  <a v-if="lead.email" :href="`mailto:${lead.email}`">{{ lead.email }}</a>
                  <span v-if="lead.email && lead.whatsapp"> · </span>
                  <span v-if="lead.whatsapp">{{ lead.whatsapp }}</span>
                  <span v-if="!lead.email && !lead.whatsapp">—</span>
                </td>
                <td class="lead-message">{{ lead.message || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getLeads, type Lead } from '@/services/leads'

const { t } = useI18n()

const loading = ref(true)
const error = ref('')
const leads = ref<Lead[]>([])

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString()
}

function exportCsv() {
  const header = ['Received', 'Name', 'Email', 'WhatsApp', 'Message', 'Agent']
  const escape = (v: string | null) => `"${(v ?? '').replace(/"/g, '""')}"`
  const rows = leads.value.map((l) =>
    [l.created, l.name, l.email, l.whatsapp, l.message, l.instance_name].map(escape).join(','),
  )
  const csv = [header.join(','), ...rows].join('\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `welcochat-leads-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  try {
    leads.value = await getLeads()
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('leads.errorLoad')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.step-subtitle { color: rgba(148, 163, 184, 0.85); margin: 0.25rem 0 1.5rem; }
.leads-actions { margin-bottom: 0.9rem; }
.leads-table-wrap { overflow-x: auto; max-width: 960px; }
.leads-table { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
.leads-table th {
  text-align: left;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: rgba(148, 163, 184, 0.8);
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid rgba(148, 163, 184, 0.25);
  white-space: nowrap;
}
.leads-table td {
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  vertical-align: top;
}
.leads-table a { color: var(--blue-2, #60a5fa); }
.nowrap { white-space: nowrap; }
.lead-message { color: rgba(203, 213, 225, 0.9); max-width: 380px; }
</style>
