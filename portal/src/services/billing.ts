import { apiFetch, extractErrorMessage } from './http'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export interface Country {
  id: number
  name: string
  code: string
}

export interface Company {
  id: number
  name: string
  country_id: number | null
  postal_code: string | null
  city: string | null
  address_line: string | null
  tax_number: string | null
}

export interface CompanyPayload {
  name: string
  country_id?: number | null
  postal_code?: string | null
  city?: string | null
  address_line?: string | null
  tax_number?: string | null
}

export async function getCountries(): Promise<Country[]> {
  const r = await apiFetch(`${API_BASE_URL}/billing/countries`, { method: 'GET' })
  const data = await r.json().catch(() => [])
  if (!r.ok) throw new Error('Failed to load countries')
  return data as Country[]
}

export async function getCompany(): Promise<Company | null> {
  const r = await apiFetch(`${API_BASE_URL}/billing/company`, { method: 'GET' })
  const data = await r.json().catch(() => null)
  if (!r.ok) throw new Error('Failed to load company')
  return data as Company | null
}

export async function saveCompany(payload: CompanyPayload): Promise<Company> {
  const r = await apiFetch(`${API_BASE_URL}/billing/company`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) {
    throw new Error(extractErrorMessage(data, 'Failed to save billing details'))
  }
  return data as Company
}

export async function getPortalSessionUrl(): Promise<string> {
  const r = await apiFetch(`${API_BASE_URL}/billing/portal-session`, { method: 'POST' })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) {
    throw new Error(extractErrorMessage(data, 'Failed to open billing portal'))
  }
  return (data as { url: string }).url
}
