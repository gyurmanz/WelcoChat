import { apiFetch } from './http'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export interface Lead {
  id: number
  instance_id: number
  instance_name: string
  name: string | null
  email: string | null
  whatsapp: string | null
  message: string | null
  created: string
}

export async function getLeads(): Promise<Lead[]> {
  const r = await apiFetch(`${API_BASE_URL}/welco/leads`, { method: 'GET' })
  const d = await r.json().catch(() => [])
  if (!r.ok) throw new Error('Failed to load leads')
  return d as Lead[]
}
