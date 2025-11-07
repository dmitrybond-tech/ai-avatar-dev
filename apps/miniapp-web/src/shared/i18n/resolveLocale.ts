export type Locale = "ru" | "en"
export type LocaleSource = "query" | "storage" | "tg" | "navigator" | "env"

const LOCALE_STORAGE_KEY = "app.locale"

function normalizeLocale(value: unknown): Locale | null {
  if (typeof value !== "string") return null
  const trimmed = value.trim().toLowerCase()
  if (!trimmed) return null
  if (trimmed.startsWith("ru")) return "ru"
  if (trimmed.startsWith("en")) return "en"
  return null
}

function readQueryParam(): Locale | null {
  if (typeof window === "undefined" || typeof window.location === "undefined") {
    return null
  }
  try {
    const params = new URLSearchParams(window.location.search)
    return normalizeLocale(params.get("lang"))
  } catch {
    return null
  }
}

function readStorage(): Locale | null {
  if (typeof window === "undefined" || !("localStorage" in window)) {
    return null
  }
  try {
    const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY)
    return normalizeLocale(stored)
  } catch {
    return null
  }
}

function readTelegram(): Locale | null {
  if (typeof window === "undefined") return null
  try {
    const tgLang = (window as any)?.Telegram?.WebApp?.initDataUnsafe?.user?.language_code
    return normalizeLocale(tgLang)
  } catch {
    return null
  }
}

function readNavigator(): Locale | null {
  if (typeof navigator === "undefined") return null
  const candidates = Array.isArray(navigator.languages) ? navigator.languages : [navigator.language]
  for (const candidate of candidates) {
    const normalized = normalizeLocale(candidate)
    if (normalized) {
      return normalized
    }
  }
  return null
}

function readEnvDefault(): Locale {
  const envValue = normalizeLocale((import.meta.env?.VITE_DEFAULT_LANG as string | undefined) ?? null)
  if (envValue) {
    return envValue
  }
  return "en"
}

export function getLocaleStorageKey(): string {
  return LOCALE_STORAGE_KEY
}

export function resolveLocale(): { locale: Locale; source: LocaleSource } {
  const queryLocale = readQueryParam()
  if (queryLocale) {
    return { locale: queryLocale, source: "query" }
  }

  const storedLocale = readStorage()
  if (storedLocale) {
    return { locale: storedLocale, source: "storage" }
  }

  const tgLocale = readTelegram()
  if (tgLocale) {
    return { locale: tgLocale, source: "tg" }
  }

  const navigatorLocale = readNavigator()
  if (navigatorLocale) {
    return { locale: navigatorLocale, source: "navigator" }
  }

  return { locale: readEnvDefault(), source: "env" }
}

export { normalizeLocale }


