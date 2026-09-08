import { ref, computed } from 'vue'
import { getAuthToken, getAuthTokenType } from './tokenStorage'

const pendingRequests = ref(0)

export const isGlobalLoading = computed(() => pendingRequests.value > 0)

/**
 * FastAPI's `detail` is a plain string for a raised HTTPException, but a
 * list of {loc, msg, type} objects for a Pydantic validation error (422).
 * Reading it as a string unconditionally stringifies that array into
 * "[object Object],[object Object]" — this normalizes either shape into
 * one readable message.
 */
export function extractErrorMessage(data: unknown, fallback: string): string {
  const detail = (data as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail) && detail.length) {
    const messages = detail
      .map((e) => (e && typeof e === 'object' && 'msg' in e ? String((e as { msg: unknown }).msg) : null))
      .filter((m): m is string => !!m)
    if (messages.length) return messages.join(' ')
  }
  const message = (data as { message?: unknown } | null)?.message
  if (typeof message === 'string' && message) return message
  return fallback
}

export async function apiFetch(
  input: RequestInfo | URL,
  init: RequestInit = {},
  opts: { silent?: boolean } = {},
): Promise<Response> {
  if (!opts.silent) pendingRequests.value++

  try {
    const headers = new Headers(init.headers || {})

    const token = getAuthToken()
    const tokenType = getAuthTokenType() || 'bearer'

    if (token) {
      headers.set('Authorization', `${tokenType} ${token}`)
    }

    const response = await fetch(input, {
      ...init,
      headers,
    })

    return response
  } finally {
    if (!opts.silent) pendingRequests.value--
  }
}
