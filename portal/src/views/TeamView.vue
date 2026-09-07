<template>
  <div class="page">
    <h1>Team</h1>
    <p class="step-subtitle">Everyone listed here can see and manage your WelcoChat subscriptions.</p>

    <p v-if="error" class="input-hint" role="alert">{{ error }}</p>

    <div v-if="loading" class="input-hint">Loading…</div>

    <template v-else>
      <section class="team-list">
        <article v-for="m in members" :key="m.id" class="team-row">
          <div class="team-info">
            <div class="team-name">{{ m.display_name || m.email }}</div>
            <div class="team-email">{{ m.email }}</div>
          </div>
          <span class="badge" :class="statusClass(m.status)">{{ statusLabel(m.status) }}</span>
          <button
            v-if="isOwner && m.id !== 0"
            class="btn btn-outline btn-sm"
            :disabled="removingId === m.id"
            @click="onRemove(m.id)"
          >
            {{ removingId === m.id ? 'Removing…' : 'Remove' }}
          </button>
        </article>
      </section>

      <section v-if="isOwner && tierEligible" class="invite-section">
        <h2 class="invite-h2">Invite a teammate</h2>
        <form class="invite-form" @submit.prevent="onInvite">
          <input v-model="inviteName" class="input" placeholder="Name (optional)" />
          <input v-model="inviteEmail" class="input" type="email" placeholder="teammate@company.com" required />
          <button class="btn btn-primary" :disabled="inviting">
            {{ inviting ? 'Sending…' : 'Send invite' }}
          </button>
        </form>
        <p v-if="inviteSent" class="draft-saved">Invite sent to {{ inviteSent }}.</p>
      </section>

      <div v-else-if="isOwner && !tierEligible" class="invite-section locked-feature">
        <p class="field-hint">Team accounts are available on the Business plan and up.</p>
        <router-link to="/subscriptions" class="btn btn-outline btn-sm">Upgrade a subscription</router-link>
      </div>

      <p v-else class="field-hint">Only the account owner can invite or remove team members.</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getTeam, inviteMember, removeMember, type TeamMember } from '@/services/team'

const loading = ref(true)
const error = ref('')
const isOwner = ref(false)
const tierEligible = ref(false)
const members = ref<TeamMember[]>([])

const inviteName = ref('')
const inviteEmail = ref('')
const inviting = ref(false)
const inviteSent = ref('')
const removingId = ref<number | null>(null)

function statusLabel(status: string): string {
  const map: Record<string, string> = { active: 'Active', invited: 'Invite sent' }
  return map[status] ?? status
}

function statusClass(status: string): string {
  return status === 'active' ? 'badge-active' : 'badge-pending'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await getTeam()
    isOwner.value = result.is_owner
    tierEligible.value = result.tier_eligible
    members.value = result.members
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Failed to load your team.'
  } finally {
    loading.value = false
  }
}

async function onInvite() {
  inviting.value = true
  inviteSent.value = ''
  error.value = ''
  try {
    const member = await inviteMember(inviteEmail.value, inviteName.value || undefined)
    inviteSent.value = member.email
    inviteName.value = ''
    inviteEmail.value = ''
    await load()
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Failed to send invite.'
  } finally {
    inviting.value = false
  }
}

async function onRemove(id: number) {
  removingId.value = id
  error.value = ''
  try {
    await removeMember(id)
    members.value = members.value.filter((m) => m.id !== id)
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Failed to remove team member.'
  } finally {
    removingId.value = null
  }
}

onMounted(load)
</script>

<style scoped>
.step-subtitle { color: rgba(148, 163, 184, 0.85); margin: 0.25rem 0 1.5rem; }

.team-list { display: flex; flex-direction: column; gap: 0.6rem; max-width: 640px; }
.team-row {
  display: flex; align-items: center; gap: 1rem; padding: 0.9rem 1.1rem;
  border: 1px solid rgba(148, 163, 184, 0.25); border-radius: 10px;
}
.team-info { flex: 1; min-width: 0; }
.team-name { font-weight: 600; font-size: 0.92rem; }
.team-email { font-size: 0.8rem; color: rgba(148, 163, 184, 0.75); }

.badge { padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 700; flex-shrink: 0; }
.badge-active { background: rgba(22, 163, 74, 0.15); color: #4ade80; border: 1px solid rgba(22, 163, 74, 0.3); }
.badge-pending { background: rgba(234, 179, 8, 0.15); color: #fbbf24; border: 1px solid rgba(234, 179, 8, 0.3); }

.invite-section { margin-top: 2rem; max-width: 480px; }
.invite-h2 { font-size: 1rem; margin: 0 0 0.9rem; }
.invite-form { display: flex; flex-direction: column; gap: 0.75rem; }
.input {
  width: 100%; box-sizing: border-box; padding: 0.55rem 0.75rem; border-radius: 6px;
  border: 1px solid rgba(148, 163, 184, 0.3); background: rgba(30, 41, 59, 0.6);
  color: inherit; font: inherit; font-size: 0.9rem;
}
.field-hint { font-size: 0.85rem; color: rgba(148, 163, 184, 0.7); margin-top: 1.5rem; }
.locked-feature { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
.locked-feature .field-hint { margin-top: 0; }
.draft-saved { color: #4ade80; font-size: 0.85rem; margin-top: 0.75rem; }

.btn { display: inline-flex; align-items: center; justify-content: center; padding: 0.55rem 1.1rem; border-radius: 6px; font: inherit; font-weight: 600; font-size: 0.88rem; cursor: pointer; border: 1px solid transparent; transition: opacity 0.15s; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: var(--primary, #2563eb); color: #fff; }
.btn-outline { background: transparent; border-color: rgba(148, 163, 184, 0.4); color: inherit; }
.btn-sm { padding: 0.4rem 0.8rem; font-size: 0.8rem; flex-shrink: 0; }

@media (max-width: 500px) {
  .team-row { flex-wrap: wrap; }
}
</style>
