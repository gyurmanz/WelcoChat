import { apiFetch, extractErrorMessage } from './http'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export type SupportTopic = 'bug' | 'idea' | 'question'

export async function sendSupportRequest(
  topic: SupportTopic,
  subject: string,
  message: string,
): Promise<void> {
  const r = await apiFetch(`${API_BASE_URL}/support`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, subject, message }),
  })
  if (!r.ok) {
    const data = await r.json().catch(() => ({}))
    throw new Error(extractErrorMessage(data, 'Failed to send your message'))
  }
}
