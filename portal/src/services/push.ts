import { apiFetch } from './http'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'
const SW_URL = '/portal/sw.js'
const SW_SCOPE = '/portal/'

export type PushPermissionState = 'unsupported' | 'default' | 'granted' | 'denied'

function isSupported(): boolean {
  return typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window
}

export function getPermissionState(): PushPermissionState {
  if (!isSupported()) return 'unsupported'
  return Notification.permission as PushPermissionState
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = atob(base64)
  const outputArray = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; i++) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}

async function getRegistration(): Promise<ServiceWorkerRegistration | null> {
  if (!isSupported()) return null
  try {
    return await navigator.serviceWorker.register(SW_URL, { scope: SW_SCOPE })
  } catch {
    return null
  }
}

export async function getExistingSubscription(): Promise<PushSubscription | null> {
  const reg = await getRegistration()
  if (!reg) return null
  return reg.pushManager.getSubscription()
}

/** Requests Notification permission (must be called from a user gesture), then
 * subscribes via PushManager and registers the subscription with the backend. */
export async function subscribeToPush(): Promise<boolean> {
  if (!isSupported()) return false

  const permission = await Notification.requestPermission()
  if (permission !== 'granted') return false

  const reg = await getRegistration()
  if (!reg) return false

  const keyRes = await apiFetch(`${API_BASE_URL}/push/vapid-public-key`, { method: 'GET' })
  if (!keyRes.ok) return false
  const { public_key: publicKey } = await keyRes.json()
  if (!publicKey) return false

  let subscription = await reg.pushManager.getSubscription()
  if (!subscription) {
    subscription = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey) as BufferSource,
    })
  }

  const json = subscription.toJSON()
  const res = await apiFetch(`${API_BASE_URL}/push/subscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      endpoint: json.endpoint,
      keys: { p256dh: json.keys?.p256dh, auth: json.keys?.auth },
    }),
  })
  return res.ok
}

export async function unsubscribeFromPush(): Promise<void> {
  const subscription = await getExistingSubscription()
  if (!subscription) return
  const endpoint = subscription.endpoint
  await subscription.unsubscribe().catch(() => {})
  await apiFetch(`${API_BASE_URL}/push/unsubscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ endpoint }),
  }).catch(() => {})
}

/** Registers the service worker eagerly (no permission prompt) so it's ready
 * once the user opts in, and so the portal is installable as a PWA. */
export function registerServiceWorker(): void {
  if (!isSupported()) return
  navigator.serviceWorker.register(SW_URL, { scope: SW_SCOPE }).catch(() => {})
}
