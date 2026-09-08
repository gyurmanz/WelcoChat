import { createI18n } from 'vue-i18n'

import en from './locales/en.json'
import de from './locales/de.json'
import fr from './locales/fr.json'
import hu from './locales/hu.json'
import pl from './locales/pl.json'
import sk from './locales/sk.json'
import hr from './locales/hr.json'
import el from './locales/el.json'
import es from './locales/es.json'

// Adding a language later: create locales/<code>.json (copy en.json as a
// starting point, translate the values), add it to SUPPORTED_LOCALES and the
// messages map below. Any key missing from a non-English locale silently
// falls back to the English string (see `fallbackLocale`), so a partial
// translation is always safe to ship.
export const SUPPORTED_LOCALES = [
  { code: 'en', name: 'English' },
  { code: 'de', name: 'Deutsch' },
  { code: 'fr', name: 'Français' },
  { code: 'hu', name: 'Magyar' },
  { code: 'pl', name: 'Polski' },
  { code: 'sk', name: 'Slovenčina' },
  { code: 'hr', name: 'Hrvatski' },
  { code: 'el', name: 'Ελληνικά' },
  { code: 'es', name: 'Español' },
] as const

export type LocaleCode = (typeof SUPPORTED_LOCALES)[number]['code']

const SUPPORTED_CODES: readonly string[] = SUPPORTED_LOCALES.map((l) => l.code)
const DEFAULT_LOCALE: LocaleCode = 'en'
const STORAGE_KEY = 'welcochat_locale'

function isSupported(code: string | null | undefined): code is LocaleCode {
  return !!code && SUPPORTED_CODES.includes(code)
}

/** Best-matching supported locale from the browser's language list, or null. */
function detectBrowserLocale(): LocaleCode | null {
  const candidates = navigator.languages && navigator.languages.length
    ? navigator.languages
    : [navigator.language]
  for (const raw of candidates) {
    if (!raw) continue
    const primary = (raw.split('-')[0] ?? '').toLowerCase()
    if (isSupported(primary)) return primary
  }
  return null
}

/** ?lang= query param set by the public site's CTAs, e.g. /portal/signup?lang=hu
 * — read once so a visitor who already picked a language on the marketing
 * site doesn't have to pick it again in the portal. */
function detectFromQueryParam(): LocaleCode | null {
  try {
    const param = new URLSearchParams(window.location.search).get('lang')
    return isSupported(param) ? param : null
  } catch {
    return null
  }
}

function initialLocale(): LocaleCode {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (isSupported(stored)) return stored

  const fromQuery = detectFromQueryParam()
  if (fromQuery) {
    localStorage.setItem(STORAGE_KEY, fromQuery)
    return fromQuery
  }

  const detected = detectBrowserLocale() ?? DEFAULT_LOCALE
  localStorage.setItem(STORAGE_KEY, detected)
  return detected
}

export const i18n = createI18n({
  legacy: false, // Composition API mode — use useI18n() / $t() in <script setup> and templates
  locale: initialLocale(),
  fallbackLocale: DEFAULT_LOCALE,
  messages: { en, de, fr, hu, pl, sk, hr, el, es },
})

export function setLocale(code: LocaleCode): void {
  ;(i18n.global.locale as unknown as { value: LocaleCode }).value = code
  localStorage.setItem(STORAGE_KEY, code)
}

export function getLocale(): LocaleCode {
  return (i18n.global.locale as unknown as { value: LocaleCode }).value
}
