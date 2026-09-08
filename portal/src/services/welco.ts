import { apiFetch, extractErrorMessage } from './http'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export interface WelcoStatus {
  status: string // pending | crawling | ready | error
  page_count: number | null
  error_message: string | null
  embed_snippet: string | null
  whatsapp_webhook_url: string | null
}

export async function activateWelco(instanceId: number): Promise<WelcoStatus> {
  const r = await apiFetch(`${API_BASE_URL}/welco/instances/${instanceId}/activate`, { method: 'POST' })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(extractErrorMessage(d, 'Failed to activate Welco'))
  return d as WelcoStatus
}

export async function getWelcoStatus(instanceId: number, silent = false): Promise<WelcoStatus> {
  const r = await apiFetch(`${API_BASE_URL}/welco/instances/${instanceId}/status`, { method: 'GET' }, { silent })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(extractErrorMessage(d, 'Failed to load Welco status'))
  return d as WelcoStatus
}

export interface WelcoDocument {
  id: number
  file_name: string
  char_count: number | null
  uploaded_at: string
}

export interface WelcoDocumentUploadResult {
  file_name: string
  id: number | null
  char_count: number | null
  error: string | null
}

export async function getWelcoDocuments(instanceId: number): Promise<WelcoDocument[]> {
  const r = await apiFetch(`${API_BASE_URL}/welco/instances/${instanceId}/documents`, { method: 'GET' })
  const d = await r.json().catch(() => [])
  if (!r.ok) throw new Error(extractErrorMessage(d, 'Failed to load documents'))
  return d as WelcoDocument[]
}

export async function uploadWelcoDocuments(instanceId: number, files: File[]): Promise<WelcoDocumentUploadResult[]> {
  const formData = new FormData()
  for (const file of files) formData.append('files', file)
  const r = await apiFetch(`${API_BASE_URL}/welco/instances/${instanceId}/documents`, {
    method: 'POST',
    body: formData,
  })
  const d = await r.json().catch(() => [])
  if (!r.ok) throw new Error(extractErrorMessage(d, 'Failed to upload documents'))
  return d as WelcoDocumentUploadResult[]
}

export async function deleteWelcoDocument(instanceId: number, docId: number): Promise<void> {
  const r = await apiFetch(`${API_BASE_URL}/welco/instances/${instanceId}/documents/${docId}`, { method: 'DELETE' })
  if (!r.ok) {
    const d = await r.json().catch(() => ({}))
    throw new Error(extractErrorMessage(d, 'Failed to delete document'))
  }
}

export async function uploadWelcoLogo(instanceId: number, file: File): Promise<string> {
  const formData = new FormData()
  formData.append('file', file)
  const r = await apiFetch(`${API_BASE_URL}/welco/instances/${instanceId}/logo`, {
    method: 'POST',
    body: formData,
  })
  const d = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(extractErrorMessage(d, 'Failed to upload logo'))
  return (d as { logo_url: string }).logo_url
}

export async function removeWelcoLogo(instanceId: number): Promise<void> {
  const r = await apiFetch(`${API_BASE_URL}/welco/instances/${instanceId}/logo`, { method: 'DELETE' })
  if (!r.ok) {
    const d = await r.json().catch(() => ({}))
    throw new Error(extractErrorMessage(d, 'Failed to remove logo'))
  }
}

export async function testWelcoNotification(instanceId: number, channelType: string, webhookUrl: string): Promise<void> {
  const r = await apiFetch(`${API_BASE_URL}/welco/instances/${instanceId}/test-notification`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ channel_type: channelType, webhook_url: webhookUrl }),
  })
  if (!r.ok) {
    const d = await r.json().catch(() => ({}))
    throw new Error(extractErrorMessage(d, 'Failed to send test notification'))
  }
}
