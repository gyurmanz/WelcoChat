import { apiFetch, extractErrorMessage } from './/http'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

/* ============================
   Types
   ============================ */

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface MeResponse {
  email: string
  display_name: string
  phone: string | null
  id: number
  is_active: boolean
  has_password: boolean
}

export interface UpdateProfileResult {
  user: MeResponse
  access_token: string
  token_type: string
  email_change_pending: boolean
}

export interface RegistrationRequestPayload {
  email: string
  display_name: string
  password: string
}

/* ============================
   Auth API calls
   ============================ */

export async function login(email: string, password: string): Promise<LoginResponse> {
  const body = new URLSearchParams()
  body.append('username', email)
  body.append('password', password)

  const response = await apiFetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(extractErrorMessage(data, 'Invalid email or password'))
  }

  return {
    access_token: data.access_token as string,
    token_type: data.token_type as string,
  }
}

export async function getMe(): Promise<MeResponse> {
  const response = await apiFetch(`${API_BASE_URL}/auth/me`, { method: 'GET' })
  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(extractErrorMessage(data, 'Unauthorized'))
  }

  return {
    email: data.email,
    display_name: data.display_name,
    phone: data.phone ?? null,
    id: data.id,
    is_active: data.is_active,
    has_password: data.has_password,
  }
}

/* ============================
   Account / profile
   ============================ */

export async function updateProfile(payload: {
  display_name?: string
  email?: string
  phone?: string
}): Promise<UpdateProfileResult> {
  const response = await apiFetch(`${API_BASE_URL}/auth/me`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, 'Failed to update profile'))
  }
  return data as UpdateProfileResult
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  const response = await apiFetch(`${API_BASE_URL}/auth/change-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, 'Failed to change password'))
  }
}

/* ============================
   Registration (RegistrationRequest)
   ============================ */

export async function signup(
  payload: RegistrationRequestPayload,
): Promise<void> {
  const response = await apiFetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(extractErrorMessage(data, 'Registration failed'))
  }
}

/* ============================
   Email verification
   ============================ */

export async function verifyEmail(token: string): Promise<void> {
  const response = await apiFetch(
    `${API_BASE_URL}/auth/verify-email?token=${encodeURIComponent(token)}`,
    { method: 'GET' },
  )

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(extractErrorMessage(data, 'Email verification failed'))
  }
}

/* ============================
   Password reset
   ============================ */

export async function forgotPassword(email: string): Promise<void> {
  const response = await apiFetch(`${API_BASE_URL}/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(extractErrorMessage(data, 'Failed to send password reset email'))
  }
}

export async function resetPassword(token: string, email: string, newPassword: string): Promise<void> {
  const response = await apiFetch(`${API_BASE_URL}/auth/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, password: newPassword, email }),
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(extractErrorMessage(data, 'Password reset failed'))
  }
}

export async function confirmEmailChange(token: string): Promise<void> {
  const response = await apiFetch(
    `${API_BASE_URL}/auth/confirm-email-change?token=${encodeURIComponent(token)}`,
    { method: 'GET' },
  )
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(extractErrorMessage(data, 'Email change confirmation failed'))
  }
}

/* ============================
   Google OAuth (authorization-code flow)
   ============================ */

const GOOGLE_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/v2/auth'
// From Zoli's Google Cloud project; placeholder env var, never a committed secret.
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

/** Same redirect_uri for the Google authorize redirect AND the backend code exchange. */
export function googleRedirectUri(): string {
  // BASE_URL is '/portal/' in production (see vite.config.ts) — the
  // callback route lives under the portal's own base path, not the site
  // root, now that the portal is served from /portal instead of owning
  // its own origin.
  return `${window.location.origin}${import.meta.env.BASE_URL}auth/google/callback`
}

/** URL that sends the user to the Google consent screen. `state` is a CSRF nonce. */
export function buildGoogleAuthUrl(state: string): string {
  const params = new URLSearchParams({
    client_id: GOOGLE_CLIENT_ID,
    redirect_uri: googleRedirectUri(),
    response_type: 'code',
    scope: 'openid email profile',
    state,
    prompt: 'select_account',
  })
  return `${GOOGLE_AUTH_ENDPOINT}?${params.toString()}`
}

/**
 * Exchange the Google `code` for our session token via the backend (the client_secret stays in the
 * backend). The response is the same {access_token, token_type} as the password login, so authSession
 * is unchanged.
 */
export async function exchangeGoogleCode(code: string, redirectUri: string): Promise<LoginResponse> {
  const response = await apiFetch(`${API_BASE_URL}/auth/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, redirect_uri: redirectUri }),
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(extractErrorMessage(data, 'Google sign-in failed'))
  }

  return {
    access_token: data.access_token as string,
    token_type: data.token_type as string,
  }
}
