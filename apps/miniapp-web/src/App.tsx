import { useEffect, useMemo, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8080'
const DEFAULT_LANG = (import.meta.env.VITE_DEFAULT_LANG ?? 'ru') as 'ru' | 'en'

type Rules = {
  language?: 'ru' | 'en'
  labels: Record<string, any>
  scenes: Record<string, any>
}

function useQuery() {
  return useMemo(() => new URLSearchParams(window.location.search), [])
}

export function App() {
  const query = useQuery()
  const [lang, setLang] = useState<'ru' | 'en'>(() => (query.get('lang') === 'en' ? 'en' : DEFAULT_LANG))
  const [rules, setRules] = useState<Rules | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    fetch(`${API_BASE}/rules?lang=${lang}`, { signal: controller.signal })
      .then(r => r.json())
      .then((data: Rules) => setRules(data))
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [lang])

  const labels = rules?.labels ?? {}
  const scene = rules?.scenes?.start ?? { text: '', buttons: [] as string[] }

  const onBook = async () => {
    const r = await fetch(`${API_BASE}/cal/suggest?event=intro-30m&lang=${lang}`)
    const data = await r.json()
    // open in external browser
    if (window.Telegram?.WebApp?.openTgLink) {
      window.Telegram.WebApp.openTgLink(data.url)
    } else {
      window.open(data.url, '_blank')
    }
  }

  return (
    <div className="min-h-dvh w-full bg-white text-black">
      <div className="max-w-md mx-auto p-4 grid gap-4">
        <header className="flex items-center justify-between">
          <h1 className="text-lg font-semibold">{lang === 'ru' ? 'Ассистент' : 'Assistant'}</h1>
          <button
            className="text-sm px-3 py-1 rounded border border-gray-300"
            onClick={() => setLang(prev => (prev === 'ru' ? 'en' : 'ru'))}
          >
            {labels?.language ?? (lang === 'ru' ? 'Язык' : 'Language')}
          </button>
        </header>
        <main className="grid gap-4">
          <div className="whitespace-pre-line text-base">
            {loading ? (lang === 'ru' ? 'Загрузка…' : 'Loading…') : scene.text}
          </div>
          <div className="grid grid-cols-1 gap-3">
            <button className="h-14 rounded bg-black text-white text-base" onClick={onBook}>
              {labels?.book ?? (lang === 'ru' ? 'Записаться' : 'Book a call')}
            </button>
            <a className="h-14 rounded bg-gray-100 text-black text-base grid place-items-center" href="#about">
              {labels?.about ?? (lang === 'ru' ? 'Обо мне' : 'About')}
            </a>
            <a className="h-14 rounded bg-gray-100 text-black text-base grid place-items-center" href="#services">
              {labels?.services ?? (lang === 'ru' ? 'Услуги' : 'Services')}
            </a>
            <a className="h-14 rounded bg-gray-100 text-black text-base grid place-items-center" href="#cases">
              {labels?.cases ?? (lang === 'ru' ? 'Кейсы' : 'Cases')}
            </a>
          </div>
          <section id="about" className="pt-2">
            <h2 className="font-semibold mb-1">{labels?.about ?? (lang === 'ru' ? 'Обо мне' : 'About')}</h2>
            <p className="whitespace-pre-line text-sm">{rules?.scenes?.about?.text ?? ''}</p>
          </section>
          <section id="services" className="pt-2">
            <h2 className="font-semibold mb-1">{labels?.services ?? (lang === 'ru' ? 'Услуги' : 'Services')}</h2>
            <p className="whitespace-pre-line text-sm">{rules?.scenes?.services?.text ?? ''}</p>
          </section>
          <section id="cases" className="pt-2 pb-6">
            <h2 className="font-semibold mb-1">{labels?.cases ?? (lang === 'ru' ? 'Кейсы' : 'Cases')}</h2>
            <p className="whitespace-pre-line text-sm">{rules?.scenes?.cases?.text ?? ''}</p>
          </section>
        </main>
      </div>
    </div>
  )
}
