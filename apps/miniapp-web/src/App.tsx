import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { PrimaryActions } from './components/Buttons'
import { TasksModal } from './components/TasksModal'
import { ChatBox } from './components/Chat'
import { BriefFormPage } from './pages/BriefFormPage'
import { useI18n } from './lib/i18n'
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

function ensureSupportedLang(candidate: string | null | undefined): Lang {
  const normalized = normalizeLangCandidate(candidate)
  if (normalized && SUPPORTED_LANG_SET.has(normalized)) {
    return normalized
  }
  return DEFAULT_LANG
}

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
  const { locale, setLocale, t } = useI18n()
  const initialPath = typeof window !== 'undefined' ? window.location.pathname : '/'

  const [route, setRoute] = useState<Route>(() => parseRoute(initialPath))
  const [isTasksOpen, setIsTasksOpen] = useState(false)
  const headerRef = useRef<HTMLElement | null>(null)

  const buildTarget = useCallback((path: string, lang: Lang): string => {
    if (typeof window === 'undefined') {
      return path
    }
    const url = new URL(window.location.href)
    url.pathname = path
    url.searchParams.set('lang', lang)
    return `${url.pathname}${url.search}${url.hash}`
  }, [])

  const goTo = useCallback((path: string, options?: { replace?: boolean; lang?: Lang }) => {
    const requestedLang = options?.lang
    const safeLang = ensureSupportedLang(requestedLang ?? locale)
    if (safeLang !== locale) {
      setLocale(safeLang)
    }

    const target = buildTarget(path, safeLang)
    if (options?.replace) {
      window.history.replaceState({}, '', target)
    } else {
      window.history.pushState({}, '', target)
    }
    setRoute(parseRoute(path))
  }, [buildTarget, locale, setLocale])

  const goHome = useCallback((lang?: Lang, options?: { replace?: boolean }) => {
    goTo('/', { lang, replace: options?.replace })
  }, [goTo])

  const goSkills = useCallback((lang: Lang, slug?: string | null, options?: { replace?: boolean }) => {
    const safeLang = ensureSupportedLang(lang)
    const base = `/${safeLang}/skills`
    const target = slug ? `${base}/${slug}` : base
    goTo(target, { lang: safeLang, replace: options?.replace })
  }, [goTo])
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
      goTo(route.to, { replace: true })
    }
  }, [route, goTo])

  useEffect(() => {
    if (route.name === 'skills' && route.lang !== locale) {
      goSkills(route.lang, route.slug ?? null, { replace: true })
    }
  }, [locale, route, goSkills])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }
    const currentPath = window.location.pathname || '/'
    const searchParams = new URLSearchParams(window.location.search)
    const queryValue = searchParams.get('lang')
    const normalizedQuery = queryValue ? normalizeLangCandidate(queryValue) : null
    if (normalizedQuery && normalizedQuery !== locale) {
      setLocale(normalizedQuery)
      goTo(currentPath, { lang: normalizedQuery, replace: true })
      return
    }
    if (!normalizedQuery) {
      goTo(currentPath, { lang: locale, replace: true })
    }
  }, [goTo, locale, setLocale])

  useLayoutEffect(() => {
    const target = headerRef.current
    if (!target) return

    const update = () => {
      const height = target.getBoundingClientRect().height
      if (Number.isFinite(height) && height > 0) {
        document.documentElement.style.setProperty('--app-header-height', `${Math.round(height)}px`)
      }
    }

    update()

    let ro: ResizeObserver | null = null
    if (typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(() => update())
      ro.observe(target)
    }

    window.addEventListener('resize', update)
    return () => {
      window.removeEventListener('resize', update)
      if (ro) {
        ro.disconnect()
      }
    }
  }, [])

  const currentLang = ensureSupportedLang(locale)

  const handleLocaleChange = useCallback(
    (target: Lang) => {
      const safeTarget = ensureSupportedLang(target)
      if (safeTarget === currentLang) {
        if (typeof window === 'undefined') {
          return
        }
        const params = new URLSearchParams(window.location.search)
        if (params.get('lang') === safeTarget) {
          return
        }
      }
      if (route.name === 'skills') {
        goSkills(safeTarget, route.slug ?? null, { replace: true })
      } else {
        goHome(safeTarget, { replace: true })
      }
    },
    [currentLang, goHome, goSkills, route],
  )

  // Standalone brief page - render without wrapper
  if (route.name === 'brief') {
    return <BriefFormPage />
  }

  return (
    <div className="min-h-dvh w-full bg-white text-black">
      <div className="max-w-md mx-auto p-4 grid gap-4">
        <header ref={headerRef} className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <img
              src="/icons/android-chrome-192x192.png"
              alt="Dmitry"
              className="h-10 w-10 rounded-full object-cover"
              loading="eager"
              decoding="async"
            />
            <div className="font-semibold">{t('header.title')}</div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center rounded-full border border-gray-200 bg-white p-0.5 text-xs shadow-sm">
              {(['ru', 'en'] as const).map((code) => {
                const isActive = code === currentLang
                return (
                  <button
                    key={code}
                    type="button"
                    onClick={() => handleLocaleChange(code)}
                    className={[
                      'px-2 py-1 rounded-full transition',
                      isActive
                        ? 'bg-black text-white shadow-sm'
                        : 'text-gray-600 hover:bg-gray-100',
                    ].join(' ')}
                    aria-pressed={isActive}
                    aria-label={code === 'ru' ? 'Русский' : 'English'}
                  >
                    {code.toUpperCase()}
                  </button>
                )
              })}
            </div>
            <a
              href="https://dmitrybond.tech"
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1 text-sm rounded-md border border-gray-300 hover:bg-gray-50"
            >
              {t('header.personalSite')}
            </a>
          </div>
        </header>
        {route.name === 'home' && (
          <>
            <PrimaryActions
              lang={currentLang}
              onSkills={(lang) => goSkills(ensureSupportedLang(lang))}
              onTasks={() => setIsTasksOpen(true)}
            />
            <ChatBox lang={currentLang} />
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
