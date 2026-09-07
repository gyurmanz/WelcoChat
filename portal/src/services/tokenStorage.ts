export type TokenStorageType = 'local' | 'session'

export function setAuthToken(
  token: string,
  tokenType: string,
  remember: boolean,
) {
  const storage = remember ? localStorage : sessionStorage

  storage.setItem('auth_token', token)
  storage.setItem('auth_token_type', tokenType)

  // biztos ami biztos: a másikból töröljük
  const other = remember ? sessionStorage : localStorage
  other.removeItem('auth_token')
  other.removeItem('auth_token_type')
}

export function getAuthToken(): string | null {
  return (
    localStorage.getItem('auth_token') ||
    sessionStorage.getItem('auth_token')
  )
}

export function getAuthTokenType(): string | null {
  return (
    localStorage.getItem('auth_token_type') ||
    sessionStorage.getItem('auth_token_type')
  )
}

export function clearAuthToken() {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('auth_token_type')
  sessionStorage.removeItem('auth_token')
  sessionStorage.removeItem('auth_token_type')
}

export function isRemembered(): boolean {
  // A 'remember me' valasztas megorzese token-rotaciokor: localStorage = tartos.
  return localStorage.getItem('auth_token') !== null
}
