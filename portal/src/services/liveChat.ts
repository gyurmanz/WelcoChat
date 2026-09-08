import { apiFetch, extractErrorMessage } from './http'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export interface ConvMessage {
  id: number
  sender: 'visitor' | 'agent' | 'human'
  sender_name: string | null
  content: string
  created: string
}

export interface ConversationSummary {
  id: number
  instance_id: number
  instance_name: string
  status: 'waiting' | 'active' | 'resolved_by_email' | 'closed'
  channel: 'widget' | 'whatsapp'
  visitor_phone: string | null
  created: string
  last_visitor_message_at: string | null
  last_agent_message_at: string | null
  preview: string | null
}

export interface ConversationDetail {
  id: number
  instance_id: number
  instance_name: string
  status: 'waiting' | 'active' | 'resolved_by_email' | 'closed'
  channel: 'widget' | 'whatsapp'
  visitor_phone: string | null
  messages: ConvMessage[]
}

export async function getConversations(silent = false): Promise<ConversationSummary[]> {
  const r = await apiFetch(`${API_BASE_URL}/live-chat`, { method: 'GET' }, { silent })
  const d = await r.json().catch(() => [])
  if (!r.ok) throw new Error('Failed to load conversations')
  return (Array.isArray(d) ? d : []) as ConversationSummary[]
}

export async function getConversation(id: number, silent = false): Promise<ConversationDetail> {
  const r = await apiFetch(`${API_BASE_URL}/live-chat/${id}`, { method: 'GET' }, { silent })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(extractErrorMessage(d, 'Failed to load conversation'))
  return d as ConversationDetail
}

export async function sendReply(id: number, content: string): Promise<ConvMessage> {
  const r = await apiFetch(`${API_BASE_URL}/live-chat/${id}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(extractErrorMessage(d, 'Failed to send reply'))
  return d as ConvMessage
}

export async function closeConversation(id: number): Promise<ConversationDetail> {
  const r = await apiFetch(`${API_BASE_URL}/live-chat/${id}/close`, { method: 'POST' })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(extractErrorMessage(d, 'Failed to close conversation'))
  return d as ConversationDetail
}
