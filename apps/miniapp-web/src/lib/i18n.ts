import en from "../i18n/en.json";
import ru from "../i18n/ru.json";

type Locale = "en" | "ru";
const dict: Record<Locale, any> = { en, ru };

export function detectLocale(): Locale {
  // 1. URLSearchParams (lang)
  const urlLang = new URLSearchParams(location.search).get("lang");
  if (urlLang === "ru" || urlLang === "en") return urlLang;

  // 2. Telegram WebApp language
  try {
    const tg = (window as any).Telegram?.WebApp?.initDataUnsafe?.user?.language_code;
    if (tg && /^ru/i.test(tg)) return "ru";
  } catch {}

  // 3. localStorage
  const saved = localStorage.getItem("locale");
  if (saved === "ru" || saved === "en") return saved as Locale;

  // 4. navigator.language
  return /^ru/i.test(navigator.language) ? "ru" : "en";
}

export function createI18n(initial?: Locale) {
  let current: Locale = initial || detectLocale();

  const t = (key: string): string => {
    const parts = key.split(".");
    let node: any = dict[current];
    for (const p of parts) {
      node = node?.[p];
    }
    return (typeof node === "string" && node) || key;
  };

  const get = () => current;
  const set = (l: Locale) => {
    current = l;
    localStorage.setItem("locale", l);
  };

  return { t, get, set };
}

