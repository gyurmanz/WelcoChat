<template>
  <div class="page">
    <h1>{{ t('statistics.title') }}</h1>
    <p class="step-subtitle">{{ t('statistics.intro') }}</p>

    <p v-if="error" class="input-hint" role="alert">{{ error }}</p>
    <div v-if="loading" class="input-hint">{{ t('statistics.loading') }}</div>

    <template v-else>
      <div v-if="welco.length === 0" class="empty-state">
        <p class="empty-text">{{ t('statistics.noAgent') }}</p>
        <div class="empty-actions">
          <router-link to="/subscriptions/add" class="btn btn-primary">{{ t('dashboard.addSubscription') }}</router-link>
        </div>
      </div>

      <section v-for="(w, idx) in welco" :key="`welco-${w.instance_id}`" class="stats-section">
        <h2>WelcoChat<span v-if="welco.length > 1" class="section-index"> #{{ idx + 1 }}</span></h2>

        <div class="tile-row">
          <div class="tile">
            <div class="tile-value">{{ w.total_messages }}</div>
            <div class="tile-label">{{ t('statistics.messagesAnswered') }}</div>
            <div class="tile-sub">{{ t('statistics.inLast30Days', { count: w.messages_last_30d }) }}</div>
          </div>
          <div class="tile">
            <div class="tile-value">{{ w.handoff_rate }}%</div>
            <div class="tile-label">{{ t('statistics.handoffRate') }}</div>
            <div class="tile-sub">{{ t('statistics.passedToHuman') }}</div>
          </div>
          <div class="tile">
            <div class="tile-value">{{ w.total_leads }}</div>
            <div class="tile-label">{{ t('statistics.leadsCaptured') }}</div>
            <div class="tile-sub">{{ t('statistics.inLast30Days', { count: w.leads_last_30d }) }}</div>
          </div>
        </div>

        <div v-if="w.total_messages > 0" class="trend">
          <div class="trend-title">{{ t('statistics.trendTitle') }}</div>
          <div class="trend-bars">
            <div
              v-for="d in w.daily_messages"
              :key="d.date"
              class="trend-bar"
              :title="`${d.date}: ${d.count} ${d.count === 1 ? t('statistics.message') : t('statistics.messages')}`"
              :style="{ height: barHeight(d.count, maxCount(w.daily_messages)) }"
            ></div>
          </div>
        </div>
        <p v-else class="no-data">{{ t('statistics.noData') }}</p>

        <div class="kb-health">
          <span class="badge" :class="kbBadgeClass(w.kb_status)">{{ kbStatusLabel(w.kb_status) }}</span>
          <span v-if="w.page_count" class="kb-detail">
            {{ w.page_count === 1 ? t('statistics.pageCrawledOne', { count: w.page_count }) : t('statistics.pageCrawledMany', { count: w.page_count }) }}
            <template v-if="w.crawled_at"> · {{ t('statistics.lastCrawl', { date: formatDate(w.crawled_at) }) }}</template>
          </span>
          <span class="kb-detail">{{ w.document_count === 1 ? t('statistics.documentUploadedOne', { count: w.document_count }) : t('statistics.documentUploadedMany', { count: w.document_count }) }}</span>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getStats, type WelcoStats, type DailyCount } from '@/services/stats'

const { t } = useI18n()

const loading = ref(true)
const error = ref('')
const welco = ref<WelcoStats[]>([])

function maxCount(series: DailyCount[]): number {
  return Math.max(...series.map((d) => d.count), 1)
}

function barHeight(count: number, max: number): string {
  if (count === 0) return '2px'
  return `${Math.max((count / max) * 100, 8)}%`
}

function kbStatusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: t('statistics.kbPending'),
    crawling: t('statistics.kbCrawling'),
    ready: t('statistics.kbReady'),
    error: t('statistics.kbError'),
  }
  return map[status] ?? status
}

function kbBadgeClass(status: string): string {
  if (status === 'ready') return 'badge-good'
  if (status === 'error') return 'badge-bad'
  if (status === 'crawling') return 'badge-warn'
  return 'badge-neutral'
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString()
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await getStats()
    welco.value = result.welco
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('statistics.errorLoad')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.step-subtitle { color: rgba(148, 163, 184, 0.85); margin: 0.25rem 0 1.5rem; }

.stats-section {
  max-width: 760px;
  margin-bottom: 2.5rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid rgba(148, 163, 184, 0.15);
}
.stats-section:last-child { border-bottom: none; }
.stats-section h2 { font-size: 1.05rem; margin: 0 0 1rem; }
.section-index { color: rgba(148, 163, 184, 0.7); font-weight: 500; }

.tile-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.75rem; }
.tile {
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 10px;
  padding: 0.9rem 1rem;
}
.tile-value { font-size: 1.6rem; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1.2; }
.tile-label { font-size: 0.82rem; font-weight: 600; margin-top: 0.2rem; }
.tile-sub { font-size: 0.75rem; color: rgba(148, 163, 184, 0.75); margin-top: 0.15rem; }

.trend { margin-top: 1.25rem; }
.trend-title { font-size: 0.8rem; color: rgba(148, 163, 184, 0.85); margin-bottom: 0.5rem; }
.trend-bars {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 64px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
  padding-bottom: 1px;
}
.trend-bar {
  flex: 1;
  min-width: 2px;
  background: var(--primary, #2563eb);
  border-radius: 2px 2px 0 0;
  opacity: 0.85;
}
.trend-bar:hover { opacity: 1; }

.no-data { margin-top: 1.25rem; font-size: 0.85rem; color: rgba(148, 163, 184, 0.75); }

.kb-health {
  margin-top: 1.25rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  font-size: 0.82rem;
}
.kb-detail { color: rgba(148, 163, 184, 0.8); }

.badge { padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 700; flex-shrink: 0; }
.badge-good { background: rgba(22, 163, 74, 0.15); color: #4ade80; border: 1px solid rgba(22, 163, 74, 0.3); }
.badge-warn { background: rgba(234, 179, 8, 0.15); color: #fbbf24; border: 1px solid rgba(234, 179, 8, 0.3); }
.badge-bad { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
.badge-neutral { background: rgba(148, 163, 184, 0.1); color: rgba(148, 163, 184, 0.85); border: 1px solid rgba(148, 163, 184, 0.2); }

.breakdown-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-top: 1.5rem; }
.breakdown-title { font-size: 0.8rem; color: rgba(148, 163, 184, 0.85); margin-bottom: 0.5rem; }
.breakdown-list { display: flex; flex-direction: column; gap: 0.4rem; }
.breakdown-item { display: grid; grid-template-columns: 90px 1fr 28px; align-items: center; gap: 0.6rem; }
.breakdown-label { font-size: 0.8rem; text-transform: capitalize; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.breakdown-bar-track { height: 8px; border-radius: 4px; background: rgba(148, 163, 184, 0.15); overflow: hidden; }
.breakdown-bar-fill { height: 100%; background: var(--primary, #2563eb); border-radius: 4px; }
.breakdown-count { font-size: 0.78rem; font-variant-numeric: tabular-nums; text-align: right; color: rgba(148, 163, 184, 0.85); }

.empty-state { margin-top: 2rem; }
.empty-text { color: rgba(148, 163, 184, 0.85); margin-bottom: 1.1rem; }
.empty-actions { display: flex; gap: 0.75rem; flex-wrap: wrap; }

.btn { display: inline-flex; align-items: center; justify-content: center; padding: 0.5rem 1rem; border-radius: 6px; font: inherit; font-weight: 600; font-size: 0.85rem; cursor: pointer; border: 1px solid transparent; text-decoration: none; transition: opacity 0.15s; }
.btn-primary { background: var(--primary, #2563eb); color: #fff; }

@media (max-width: 500px) {
  .breakdown-item { grid-template-columns: 70px 1fr 24px; }
}
</style>
