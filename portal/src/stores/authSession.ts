import { reactive } from 'vue'
import { getMe, type MeResponse } from '@/services/auth'
import { getAuthToken } from '@/services/tokenStorage'

export type AuthStatus = 'unknown' | 'authenticated' | 'anonymous'

export const authSession = reactive<{
  status: AuthStatus
  user: MeResponse | null
}>({
  status: 'unknown',
  user: null,
})

export async function initSession(): Promise<void> {
  const token = getAuthToken()

  if (!token) {
    authSession.status = 'anonymous'
    authSession.user = null
    return
  }

  try {
    const me = await getMe()

    if (!me.is_active) {
      throw new Error('User inactive')
    }

    authSession.user = me
    authSession.status = 'authenticated'
  } catch {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_token_type')

    authSession.user = null
    authSession.status = 'anonymous'
  }
}
