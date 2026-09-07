import { apiFetch } from './http'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export interface DailyCount {
  date: string
  count: number
}

export interface WelcoStats {
  instance_id: number
  total_messages: number
  messages_last_30d: number
  handoff_rate: number
  total_leads: number
  leads_last_30d: number
  page_count: number | null
  document_count: number
  kb_status: string
  crawled_at: string | null
  daily_messages: DailyCount[]
}

export interface StatsResponse {
  welco: WelcoStats[]
}

export async function getStats(): Promise<StatsResponse> {
  const r = await apiFetch(`${API_BASE_URL}/stats`, { method: 'GET' })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error((d?.detail as string) || 'Failed to load statistics')
  return d as StatsResponse
}
