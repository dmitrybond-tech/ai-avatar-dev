import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react"

import { getLocaleStorageKey, resolveLocale, type Locale, type LocaleSource } from "./resolveLocale"

type LocaleContextValue = {
  locale: Locale
  source: LocaleSource
  setLocale: (locale: Locale) => void
}

const LocaleContext = createContext<LocaleContextValue | undefined>(undefined)

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState(() => resolveLocale())
  const initialStateRef = useRef(state)
  const storageKey = getLocaleStorageKey()

  useEffect(() => {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.info(`[i18n] resolved=${initialStateRef.current.locale} via=${initialStateRef.current.source}`)
    }
  }, [])

  useEffect(() => {
    if (typeof window === "undefined" || !("localStorage" in window)) {
      return
    }
    try {
      window.localStorage.setItem(storageKey, state.locale)
    } catch {
      // ignore storage failures (Safari private mode, etc.)
    }
  }, [state.locale, storageKey])

  const setLocale = useCallback((locale: Locale) => {
    setState((prev) => {
      if (prev.locale === locale) {
        return prev
      }
      if (typeof window !== "undefined" && "localStorage" in window) {
        try {
          window.localStorage.setItem(storageKey, locale)
        } catch {
          // ignore storage errors
        }
      }
      return { locale, source: "storage" as LocaleSource }
    })
  }, [storageKey])

  const value = useMemo<LocaleContextValue>(() => ({
    locale: state.locale,
    source: state.source,
    setLocale,
  }), [setLocale, state.locale, state.source])

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
}

export function useLocale(): [Locale, (locale: Locale) => void] {
  const ctx = useContext(LocaleContext)
  if (!ctx) {
    throw new Error("useLocale must be used within LocaleProvider")
  }
  return [ctx.locale, ctx.setLocale]
}

export function useLocaleDetails(): LocaleContextValue {
  const ctx = useContext(LocaleContext)
  if (!ctx) {
    throw new Error("useLocaleDetails must be used within LocaleProvider")
  }
  return ctx
}


