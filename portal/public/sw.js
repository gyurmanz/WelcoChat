// WelcoChat client portal service worker — enables PWA installability and
// Web Push notifications (e.g. a live handoff that needs a human reply)
// while the portal isn't the focused tab, or the app is closed.

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

self.addEventListener('push', (event) => {
  let payload = {}
  try {
    payload = event.data ? event.data.json() : {}
  } catch {
    payload = { title: 'WelcoChat', body: event.data ? event.data.text() : '' }
  }

  const title = payload.title || 'WelcoChat'
  const url = payload.url || '/portal/live-chat'

  event.waitUntil(
    self.registration.showNotification(title, {
      body: payload.body || '',
      icon: '/portal/icon-192.png',
      badge: '/portal/icon-192.png',
      tag: 'welcochat-handoff',
      renotify: true,
      data: { url },
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = (event.notification.data && event.notification.data.url) || '/portal/live-chat'

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.includes('/portal') && 'focus' in client) {
          client.postMessage({ type: 'welcochat-notification-click', url })
          return client.focus()
        }
      }
      if (self.clients.openWindow) return self.clients.openWindow(url)
      return undefined
    }),
  )
})
