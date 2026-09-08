<template>
  <div class="page">
    <h1>{{ t('liveChat.title') }}</h1>
    <p class="step-subtitle">{{ t('liveChat.intro') }}</p>

    <p v-if="error" class="input-hint" role="alert">{{ error }}</p>

    <div class="live-chat-layout">
      <aside class="conv-list">
        <div class="conv-filters">
          <input v-model="searchQuery" type="text" class="input conv-search" :placeholder="t('liveChat.searchPlaceholder')" />
          <select v-model="statusFilter" class="input conv-status-filter">
            <option value="all">{{ t('liveChat.filterAll') }}</option>
            <option value="waiting">{{ t('liveChat.statusWaiting') }}</option>
            <option value="active">{{ t('liveChat.statusActive') }}</option>
            <option value="resolved_by_email">{{ t('liveChat.statusResolvedByEmail') }}</option>
            <option value="closed">{{ t('liveChat.statusClosed') }}</option>
          </select>
        </div>
        <div v-if="loadingList" class="input-hint">{{ t('common.loading') }}</div>
        <p v-else-if="groupedConversations.length === 0" class="empty-text">
          {{ conversations.length === 0 ? t('liveChat.noConversations') : t('liveChat.noMatches') }}
        </p>
        <template v-for="group in groupedConversations" :key="group.instanceId">
          <div class="conv-group-header">
            <span>{{ group.instanceName }}</span>
            <span class="conv-group-count">{{ group.items.length }}</span>
          </div>
          <button
            v-for="c in group.items"
            :key="c.id"
            type="button"
            class="conv-row"
            :class="{ 'conv-row--active': c.id === selectedId }"
            @click="select(c.id)"
          >
            <div class="conv-row-top">
              <span class="badge" :class="badgeClass(c.status)">{{ statusLabel(c.status) }}</span>
              <span class="channel-icon" :title="c.channel === 'whatsapp' ? 'WhatsApp' : t('liveChat.website')">
                {{ c.channel === 'whatsapp' ? '📱' : '💬' }}
              </span>
              <span class="conv-time">{{ formatTime(lastActivity(c)) }}</span>
            </div>
            <div v-if="c.channel === 'whatsapp'" class="conv-phone">{{ c.visitor_phone }}</div>
            <div class="conv-preview">{{ c.preview || '—' }}</div>
          </button>
        </template>
      </aside>

      <section class="conv-detail">
        <p v-if="!selectedId" class="empty-text">{{ t('liveChat.selectConversation') }}</p>
        <template v-else-if="detail">
          <div class="conv-detail-header">
            <div class="conv-detail-who">
              <span class="channel-icon">{{ detail.channel === 'whatsapp' ? '📱' : '💬' }}</span>
              <span>{{ detail.channel === 'whatsapp' ? detail.visitor_phone : t('liveChat.websiteVisitor') }}</span>
            </div>
            <div class="conv-detail-instance">{{ detail.instance_name }}</div>
          </div>
          <div class="conv-thread" ref="threadEl">
            <div v-for="m in detail.messages" :key="m.id" class="msg" :class="msgClass(m.sender)">
              <div v-if="m.sender !== 'visitor'" class="msg-label">
                {{ m.sender === 'human' ? (m.sender_name || t('liveChat.you')) : t('liveChat.assistant') }}
              </div>
              <div class="msg-bubble">{{ m.content }}</div>
            </div>
          </div>

          <form v-if="detail.status !== 'closed'" class="reply-form" @submit.prevent="onReply">
            <input v-model="replyText" class="input" :placeholder="t('liveChat.replyPlaceholder')" :disabled="sending" />
            <button class="btn btn-primary" :disabled="sending || !replyText.trim()">{{ t('liveChat.send') }}</button>
            <button type="button" class="btn btn-outline" :disabled="closing" @click="onClose">{{ t('liveChat.close') }}</button>
          </form>
          <p v-else class="field-hint">{{ t('liveChat.conversationClosed') }}</p>
        </template>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  getConversations, getConversation, sendReply, closeConversation,
  type ConversationSummary, type ConversationDetail,
} from '@/services/liveChat'

const { t } = useI18n()

const conversations = ref<ConversationSummary[]>([])
const selectedId = ref<number | null>(null)
const detail = ref<ConversationDetail | null>(null)
const loadingList = ref(true)
const error = ref('')
const replyText = ref('')
const sending = ref(false)
const closing = ref(false)
const threadEl = ref<HTMLElement | null>(null)
const searchQuery = ref('')
const statusFilter = ref<'all' | 'waiting' | 'active' | 'resolved_by_email' | 'closed'>('all')

interface ConvGroup {
  instanceId: number
  instanceName: string
  items: ConversationSummary[]
}

const filteredConversations = computed(() => {
  let list = conversations.value
  if (statusFilter.value !== 'all') {
    list = list.filter((c) => c.status === statusFilter.value)
  }
  const q = searchQuery.value.trim().toLowerCase()
  if (q) {
    list = list.filter(
      (c) =>
        c.instance_name.toLowerCase().includes(q) ||
        (c.visitor_phone || '').toLowerCase().includes(q) ||
        (c.preview || '').toLowerCase().includes(q),
    )
  }
  return list
})

// Groups are ordered by first appearance in the already-priority-sorted list
// from the server (waiting > active > resolved_by_email > closed, then most
// recent activity) — so the agent with the most urgent conversation floats
// to the top, not just alphabetical order.
const groupedConversations = computed<ConvGroup[]>(() => {
  const groups: ConvGroup[] = []
  const byInstance = new Map<number, ConvGroup>()
  for (const c of filteredConversations.value) {
    let group = byInstance.get(c.instance_id)
    if (!group) {
      group = { instanceId: c.instance_id, instanceName: c.instance_name, items: [] }
      byInstance.set(c.instance_id, group)
      groups.push(group)
    }
    group.items.push(c)
  }
  return groups
})

let listTimer: ReturnType<typeof setInterval> | null = null
let detailTimer: ReturnType<typeof setInterval> | null = null

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    waiting: t('liveChat.statusWaiting'),
    active: t('liveChat.statusActive'),
    resolved_by_email: t('liveChat.statusResolvedByEmail'),
    closed: t('liveChat.statusClosed'),
  }
  return map[status] ?? status
}

function badgeClass(status: string): string {
  if (status === 'waiting') return 'badge-warn'
  if (status === 'active') return 'badge-good'
  return 'badge-neutral'
}

function msgClass(sender: string): string {
  return sender === 'visitor' ? 'msg--visitor' : sender === 'human' ? 'msg--human' : 'msg--agent'
}

function lastActivity(c: ConversationSummary): string {
  return [c.last_agent_message_at, c.last_visitor_message_at, c.created]
    .filter((v): v is string => !!v)
    .sort()
    .pop() as string
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString()
}

async function scrollToBottom() {
  await nextTick()
  if (threadEl.value) threadEl.value.scrollTop = threadEl.value.scrollHeight
}

async function loadList(silent = false) {
  try {
    conversations.value = await getConversations(silent)
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('liveChat.errorLoadConversations')
  } finally {
    loadingList.value = false
  }
}

async function loadDetail(silent = false) {
  if (selectedId.value === null) return
  try {
    detail.value = await getConversation(selectedId.value, silent)
    scrollToBottom()
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('liveChat.errorLoadConversation')
  }
}

function select(id: number) {
  selectedId.value = id
  detail.value = null
  loadDetail()
}

async function onReply() {
  if (!selectedId.value || !replyText.value.trim()) return
  sending.value = true
  error.value = ''
  try {
    await sendReply(selectedId.value, replyText.value.trim())
    replyText.value = ''
    await loadDetail()
    await loadList()
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('liveChat.errorSendReply')
  } finally {
    sending.value = false
  }
}

async function onClose() {
  if (!selectedId.value) return
  closing.value = true
  error.value = ''
  try {
    await closeConversation(selectedId.value)
    await loadDetail()
    await loadList()
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('liveChat.errorCloseConversation')
  } finally {
    closing.value = false
  }
}

onMounted(() => {
  loadList()
  listTimer = setInterval(() => loadList(true), 5000)
  detailTimer = setInterval(() => {
    if (selectedId.value !== null) loadDetail(true)
  }, 3000)
})

onUnmounted(() => {
  if (listTimer) clearInterval(listTimer)
  if (detailTimer) clearInterval(detailTimer)
})
</script>

<style scoped>
.step-subtitle { color: rgba(148, 163, 184, 0.85); margin: 0.25rem 0 1.5rem; }

.live-chat-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 1.25rem;
  max-width: 900px;
  height: 560px;
}

.conv-list {
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 10px;
  overflow-y: auto;
  padding: 0.4rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.empty-text { color: rgba(148, 163, 184, 0.75); font-size: 0.85rem; padding: 0.5rem; }

.conv-filters { display: flex; flex-direction: column; gap: 0.35rem; padding: 0.15rem 0.15rem 0.35rem; position: sticky; top: 0; }
.conv-search, .conv-status-filter { font-size: 0.8rem; padding: 0.4rem 0.55rem; }

.conv-group-header {
  display: flex; align-items: center; justify-content: space-between; gap: 0.5rem;
  padding: 0.35rem 0.6rem 0.2rem; margin-top: 0.4rem;
  font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.02em;
  color: rgba(148, 163, 184, 0.75);
}
.conv-group-header:first-of-type { margin-top: 0; }
.conv-group-count {
  background: rgba(148, 163, 184, 0.15); color: rgba(148, 163, 184, 0.9);
  border-radius: 999px; padding: 0 7px; font-size: 0.68rem;
}

.conv-row {
  text-align: left;
  border: 1px solid transparent;
  background: transparent;
  border-radius: 8px;
  padding: 0.6rem 0.7rem;
  cursor: pointer;
  color: inherit;
  font: inherit;
}
.conv-row:hover { background: rgba(148, 163, 184, 0.08); }
.conv-row--active { border-color: rgba(37, 99, 235, 0.4); background: rgba(37, 99, 235, 0.08); }
.conv-row-top { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; margin-bottom: 0.3rem; }
.conv-time { font-size: 0.72rem; color: rgba(148, 163, 184, 0.7); white-space: nowrap; margin-left: auto; }
.conv-preview { font-size: 0.8rem; color: rgba(148, 163, 184, 0.85); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.conv-phone { font-size: 0.75rem; color: rgba(148, 163, 184, 0.9); font-weight: 600; margin-bottom: 0.15rem; }
.channel-icon { font-size: 0.85rem; }
.conv-detail-header {
  display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; flex-wrap: wrap;
  font-size: 0.85rem; font-weight: 600; margin-bottom: 0.6rem; padding-bottom: 0.6rem;
  border-bottom: 1px solid rgba(148, 163, 184, 0.15);
}
.conv-detail-who { display: flex; align-items: center; gap: 0.4rem; }
.conv-detail-instance { font-size: 0.75rem; font-weight: 600; color: rgba(148, 163, 184, 0.75); }

.conv-detail {
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0.75rem;
}
.conv-thread { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 0.6rem; padding: 0.25rem; }

.msg { max-width: 75%; }
.msg--visitor { align-self: flex-start; }
.msg--agent, .msg--human { align-self: flex-end; }
.msg-label { font-size: 0.7rem; font-weight: 600; color: rgba(148, 163, 184, 0.75); margin-bottom: 2px; text-align: right; }
.msg-bubble { padding: 0.5rem 0.7rem; border-radius: 8px; font-size: 0.85rem; line-height: 1.4; }
.msg--visitor .msg-bubble { background: rgba(148, 163, 184, 0.12); }
.msg--agent .msg-bubble { background: rgba(148, 163, 184, 0.12); }
.msg--human .msg-bubble { background: var(--primary, #2563eb); color: #fff; }

.reply-form { display: flex; gap: 0.5rem; margin-top: 0.75rem; }
.reply-form .input { flex: 1; }
.field-hint { font-size: 0.85rem; color: rgba(148, 163, 184, 0.7); margin-top: 0.75rem; }

.input {
  box-sizing: border-box; padding: 0.55rem 0.75rem; border-radius: 6px;
  border: 1px solid rgba(148, 163, 184, 0.3); background: rgba(30, 41, 59, 0.6);
  color: inherit; font: inherit; font-size: 0.9rem;
}

.badge { padding: 2px 10px; border-radius: 999px; font-size: 0.72rem; font-weight: 700; flex-shrink: 0; white-space: nowrap; }
.badge-good { background: rgba(22, 163, 74, 0.15); color: #4ade80; border: 1px solid rgba(22, 163, 74, 0.3); }
.badge-warn { background: rgba(234, 179, 8, 0.15); color: #fbbf24; border: 1px solid rgba(234, 179, 8, 0.3); }
.badge-neutral { background: rgba(148, 163, 184, 0.1); color: rgba(148, 163, 184, 0.85); border: 1px solid rgba(148, 163, 184, 0.2); }

.btn { display: inline-flex; align-items: center; justify-content: center; padding: 0.55rem 1.1rem; border-radius: 6px; font: inherit; font-weight: 600; font-size: 0.85rem; cursor: pointer; border: 1px solid transparent; transition: opacity 0.15s; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: var(--primary, #2563eb); color: #fff; }
.btn-outline { background: transparent; border-color: rgba(148, 163, 184, 0.4); color: inherit; }

@media (max-width: 700px) {
  .live-chat-layout { grid-template-columns: 1fr; height: auto; }
  .conv-list { max-height: 220px; }
  .conv-detail { height: 420px; }
}
</style>
