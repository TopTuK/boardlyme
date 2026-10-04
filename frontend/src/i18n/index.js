import { createI18n } from 'vue-i18n'
import en from './locales/en'
import ru from './locales/ru'

export const LOCALES = [
  { code: 'en', native: 'English' },
  { code: 'ru', native: 'Русский' },
]

const STORAGE_KEY = 'bm_locale'

export function readStoredLocale() {
  const value = localStorage.getItem(STORAGE_KEY)
  return value === 'ru' ? 'ru' : 'en'
}

export const i18n = createI18n({
  legacy: false,
  locale: readStoredLocale(),
  fallbackLocale: 'en',
  messages: { en, ru },
})

export function applyLocale(code) {
  const locale = code === 'ru' ? 'ru' : 'en'
  i18n.global.locale.value = locale
  localStorage.setItem(STORAGE_KEY, locale)
  document.documentElement.lang = locale
  return locale
}
