import { ref, computed } from 'vue'
import { getAuthToken, getAuthTokenType } from './tokenStorage'

const pendingRequests = ref(0)

export const isGlobalLoading = computed(() => pendingRequests.value > 0)

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
