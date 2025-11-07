import { useEffect, useMemo, useState } from 'react'
import { PrimaryActions } from './components/Buttons'
import { TasksModal } from './components/TasksModal'
import { ChatBox } from './components/Chat'
import { BriefFormPage } from './pages/BriefFormPage'
import { createI18n, detectLocale } from './lib/i18n'
import { safeInitTelegram } from './lib/telegram'
import { clientLog } from './lib/clientLog'
import { SkillsPage } from './pages/SkillsPage'

function useQuery() {
  return useMemo(() => new URLSearchParams(window.location.search), [])
}

const FALLBACK_LANGS = ['ru', 'en'] as const
type Lang = (typeof FALLBACK_LANGS)[number]

function normalizeLangCandidate(raw: unknown): Lang | null {
  if (typeof raw !== 'string') return null
  const val = raw.trim().toLowerCase()
  return val === 'en' || val === 'ru' ? (val as Lang) : null
}

const envSupported = (import.meta.env.VITE_SUPPORTED_LANGS as string | undefined) ?? ''
const parsedSupported = Array.from(
  new Set(
    envSupported
      .split(',')
      .map((entry) => normalizeLangCandidate(entry))
      .filter((entry): entry is Lang => Boolean(entry)),
  ),
)

const SUPPORTED_LANGS: Lang[] = parsedSupported.length ? parsedSupported : [...FALLBACK_LANGS]
const SUPPORTED_LANG_SET = new Set<Lang>(SUPPORTED_LANGS)

const envDefault = normalizeLangCandidate(import.meta.env.VITE_DEFAULT_LANG)
const DEFAULT_LANG: Lang = envDefault && SUPPORTED_LANG_SET.has(envDefault) ? envDefault : SUPPORTED_LANGS[0]

type Route =
  | { name: 'home' }
  | { name: 'skills', lang: Lang, slug?: string | null }
  | { name: 'brief' }
  | { name: 'redirect'; to: string }

function parseRoute(pathname: string): Route {
  if (pathname === '/brief') return { name: 'brief' }
  if (pathname === '/skills') return { name: 'redirect', to: `/${DEFAULT_LANG}/skills` }
  const skillsMatch = pathname.match(/^\/([a-z]{2})\/skills(?:\/([a-z0-9\-]+))?$/)
  if (skillsMatch) {
    const lang = normalizeLangCandidate(skillsMatch[1])
    if (!lang || !SUPPORTED_LANG_SET.has(lang)) {
      return { name: 'redirect', to: `/${DEFAULT_LANG}/skills` }
    }
    const slug = skillsMatch[2] ?? null
    return { name: 'skills', lang, slug }
  }
  return { name: 'home' }
}

export function App() {
  const _q = useQuery() // reserved for future
  const initialPath = window.location.pathname
  const initialRoute = parseRoute(initialPath)
  const initialLocale = initialRoute.name === 'skills' ? initialRoute.lang : detectLocale()

  const [route, setRoute] = useState<Route>(initialRoute)
  const [isTasksOpen, setIsTasksOpen] = useState(false)
  const [i18n] = useState(() => createI18n(initialLocale))

  const ensureLang = (candidate: string | null | undefined): Lang => {
    const normalized = normalizeLangCandidate(candidate)
    if (normalized && SUPPORTED_LANG_SET.has(normalized)) {
      return normalized
    }
    return DEFAULT_LANG
  }

  const goTo = (path: string, replace = false) => {
    if (replace) {
      window.history.replaceState({}, '', path)
    } else {
      window.history.pushState({}, '', path)
    }
    setRoute(parseRoute(path))
  }

  const goHome = () => {
    goTo('/')
  }

  const goSkills = (lang: Lang, slug?: string | null) => {
    const safeLang = SUPPORTED_LANG_SET.has(lang) ? lang : DEFAULT_LANG
    const base = `/${safeLang}/skills`
    const target = slug ? `${base}/${slug}` : base
    goTo(target)
  }

  useEffect(() => {
    // Initialize Telegram WebApp safely without blocking UI
    const { inTg } = safeInitTelegram()
    clientLog('info', 'miniapp_init', { inTg })
  }, [])

  useEffect(() => {
    const onPop = () => setRoute(parseRoute(window.location.pathname))
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  useEffect(() => {
    if (route.name === 'redirect') {
      goTo(route.to, true)
    }
  }, [route])

  useEffect(() => {
    if (route.name === 'skills') {
      i18n.set(route.lang)
    }
  }, [route, i18n])

  // Standalone brief page - render without wrapper
  if (route.name === 'brief') {
    return <BriefFormPage />
  }

  const currentLang = (i18n.get() === 'en' ? 'en' : 'ru') as Lang

  return (
    <div className="min-h-dvh w-full bg-white text-black">
      <div className="max-w-md mx-auto p-4 grid gap-4">
        <header className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <img
              src="/icons/android-chrome-192x192.png"
              alt="Dmitry"
              className="h-10 w-10 rounded-full object-cover"
              loading="eager"
              decoding="async"
            />
            <div className="font-semibold">{i18n.t('header.title')}</div>
          </div>
          <a
            href="https://dmitrybond.tech"
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1 text-sm rounded-md border border-gray-300 hover:bg-gray-50"
          >
            {i18n.t('header.personalSite')}
          </a>
        </header>
        {route.name === 'home' && (
          <>
            <PrimaryActions
              lang={currentLang}
              onSkills={(lang) => goSkills(ensureLang(lang))}
              onTasks={() => setIsTasksOpen(true)}
            />
            <ChatBox />
          </>
        )}
        {route.name === 'skills' && (
          <SkillsPage
            lang={route.lang}
            selectedSlug={route.slug ?? undefined}
            onBack={goHome}
            onSelect={(slug) => goSkills(route.lang, slug)}
            onCloseDetail={() => goSkills(route.lang)}
          />
        )}
      </div>
      <TasksModal isOpen={isTasksOpen} onClose={() => setIsTasksOpen(false)} />
    </div>
  )
}
