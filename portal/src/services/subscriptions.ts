import { apiFetch, extractErrorMessage } from './http'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export type BillingPeriod = 'monthly' | 'annual'

export interface ServicePlan {
  id: number
  service_key: string
  service_name: string
  tier: string
  monthly_price: number
  annual_price: number  // monthly-equivalent price under annual billing
}

export interface Subscription {
  id: number
  service_id: number | null
  service_key: string | null
  service_name: string | null
  tier: string | null
  billing_period: BillingPeriod | null
  paid_price: number | null
  start_date: string | null
  end_date: string | null
  trial_ends_at: string | null
  status: string
  pending_tier: string | null
  pending_billing_period: BillingPeriod | null
}

export interface TrialEligibility {
  welco: boolean
}

// Setup-wizard answers for the welco service.
export type ServiceConfiguration = Record<string, unknown>

export interface ServiceInstance {
  id: number
  subscription_id: number
  service_key: string
  service_name: string
  setup_status: string
  // not_configured | setup_in_progress | pending_review | running | paused | error | cancelled
  tier: string // Basic | Business | Enterprise
  configuration: ServiceConfiguration | null
}

export interface Invoice {
  id: number | string
  number: string | null
  issued_date: string | null
  period: string | null
  amount: number | null
  currency: string | null
  status: string
  pdf_url: string | null
}

export async function getServicePlans(): Promise<ServicePlan[]> {
  const r = await apiFetch(`${API_BASE_URL}/subscriptions/services`, { method: 'GET' })
  const d = await r.json().catch(() => [])
  if (!r.ok) throw new Error('Failed to load service plans')
  return d as ServicePlan[]
}

export async function getSubscriptions(): Promise<Subscription[]> {
  const r = await apiFetch(`${API_BASE_URL}/subscriptions`, { method: 'GET' })
  const d = await r.json().catch(() => [])
  if (!r.ok) throw new Error('Failed to load subscriptions')
  return d as Subscription[]
}

export async function getTrialEligibility(): Promise<TrialEligibility> {
  const r = await apiFetch(`${API_BASE_URL}/subscriptions/trial-eligibility`, { method: 'GET' })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error('Failed to load trial eligibility')
  return d as TrialEligibility
}

export async function createTrialSubscription(serviceKey: string): Promise<Subscription> {
  const r = await apiFetch(`${API_BASE_URL}/subscriptions/trial`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ service_key: serviceKey }),
  })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(extractErrorMessage(d, 'Failed to start trial'))
  return d as Subscription
}

export async function createCheckoutSession(serviceId: number, billingPeriod: BillingPeriod): Promise<string> {
  const r = await apiFetch(`${API_BASE_URL}/subscriptions/checkout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ service_id: serviceId, billing_period: billingPeriod }),
  })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(extractErrorMessage(d, 'Failed to start checkout'))
  return (d as { checkout_url: string }).checkout_url
}

export interface ChangePlanPayload {
  new_service_id: number
  billing_period?: BillingPeriod
}

export async function changePlan(subscriptionId: number, payload: ChangePlanPayload): Promise<Subscription> {
  const r = await apiFetch(`${API_BASE_URL}/subscriptions/${subscriptionId}/change-plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(extractErrorMessage(d, 'Failed to change plan'))
  return d as Subscription
}

export async function getServiceInstances(): Promise<ServiceInstance[]> {
  const r = await apiFetch(`${API_BASE_URL}/subscriptions/service-instances`, { method: 'GET' })
  const d = await r.json().catch(() => [])
  if (!r.ok) throw new Error('Failed to load service instances')
  return (Array.isArray(d) ? d : []) as ServiceInstance[]
}

export interface InstanceSetupUpdate {
  setup_status?: string
  configuration?: ServiceConfiguration
}

export async function updateInstanceSetup(instanceId: number, update: InstanceSetupUpdate): Promise<ServiceInstance> {
  const r = await apiFetch(`${API_BASE_URL}/subscriptions/service-instances/${instanceId}/setup`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(update),
  })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(extractErrorMessage(d, 'Failed to update setup status'))
  return d as ServiceInstance
}

export async function getInvoices(): Promise<Invoice[]> {
  const r = await apiFetch(`${API_BASE_URL}/subscriptions/invoices`, { method: 'GET' })
  const d = await r.json().catch(() => [])
  if (!r.ok) throw new Error('Failed to load invoices')
  return (Array.isArray(d) ? d : []) as Invoice[]
}
