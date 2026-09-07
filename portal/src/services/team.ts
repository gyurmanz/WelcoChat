import { apiFetch } from './http'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export interface TeamMember {
  id: number
  email: string
  display_name: string | null
  status: string
  created: string
}

export interface TeamListResponse {
  is_owner: boolean
  tier_eligible: boolean
  members: TeamMember[]
}

export interface InviteDetails {
  invite_email: string
  owner_display_name: string
}

export async function getTeam(): Promise<TeamListResponse> {
  const r = await apiFetch(`${API_BASE_URL}/team/members`, { method: 'GET' })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error((d?.detail as string) || 'Failed to load team')
  return d as TeamListResponse
}

export async function inviteMember(email: string, name?: string): Promise<TeamMember> {
  const r = await apiFetch(`${API_BASE_URL}/team/invite`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, name: name || null }),
  })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error((d?.detail as string) || 'Failed to invite team member')
  return d as TeamMember
}

export async function removeMember(id: number): Promise<void> {
  const r = await apiFetch(`${API_BASE_URL}/team/members/${id}`, { method: 'DELETE' })
  if (!r.ok) {
    const d = await r.json().catch(() => ({}))
    throw new Error((d?.detail as string) || 'Failed to remove team member')
  }
}

export async function getInviteDetails(token: string): Promise<InviteDetails> {
  const r = await apiFetch(`${API_BASE_URL}/team/invite/${token}`, { method: 'GET' })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error((d?.detail as string) || 'This invite link is invalid or has expired')
  return d as InviteDetails
}

export async function acceptInvite(
  token: string,
  displayName: string,
  password: string,
): Promise<{ access_token: string; token_type: string }> {
  const r = await apiFetch(`${API_BASE_URL}/team/accept-invite`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, display_name: displayName, password }),
  })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error((d?.detail as string) || 'Failed to accept invite')
  return d as { access_token: string; token_type: string }
}
