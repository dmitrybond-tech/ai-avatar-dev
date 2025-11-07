import { useMemo } from "react"

import en from "../i18n/en.json"
import ru from "../i18n/ru.json"

import { useLocale } from "../shared/i18n/localeContext"
import type { Locale } from "../shared/i18n/resolveLocale"

const dictionaries: Record<Locale, any> = { en, ru }

function translateInternal(locale: Locale, key: string): string {
  const parts = key.split(".")
  let node: any = dictionaries[locale]
  for (const part of parts) {
    node = node?.[part]
  }
  if (typeof node === "string" && node.length > 0) {
    return node
  }
  return key
}

export function translate(locale: Locale, key: string): string {
  return translateInternal(locale, key)
}

export function useI18n() {
  const [locale, setLocale] = useLocale()
  const t = useMemo(() => {
    return (key: string) => translateInternal(locale, key)
  }, [locale])

  return { locale, setLocale, t }
}

export type { Locale }


