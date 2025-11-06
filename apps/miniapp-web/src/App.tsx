import { useEffect, useMemo, useState } from 'react'
import { PrimaryActions } from './components/Buttons'
import { SkillsList } from './components/Skills'
import { TasksModal } from './components/TasksModal'
import { ChatBox } from './components/Chat'
import { SkillDetailView } from './components/SkillDetail'
import { createI18n, detectLocale } from './lib/i18n'
import { safeInitTelegram } from './lib/telegram'
import { clientLog } from './lib/clientLog'

function useQuery() {
  return useMemo(() => new URLSearchParams(window.location.search), [])
}

type Route = { name: 'home' } | { name: 'skills-list' } | { name: 'skill-detail', slug: string }

function parseRoute(pathname: string): Route {
  if (pathname === '/skills') return { name: 'skills-list' }
  const m = pathname.match(/^\/skills\/([a-z0-9\-]+)$/)
  if (m) return { name: 'skill-detail', slug: m[1] }
  return { name: 'home' }
}

export function App() {
  const _q = useQuery() // reserved for future
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.pathname))
  const [isTasksOpen, setIsTasksOpen] = useState(false)
  const [i18n] = useState(() => createI18n(detectLocale()))

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
            <PrimaryActions onSkills={()=>{ window.history.pushState({}, '', '/skills'); window.dispatchEvent(new PopStateEvent('popstate')) }} onTasks={()=>setIsTasksOpen(true)} />
            <ChatBox />
          </>
        )}
        {route.name === 'skills-list' && (
          <>
            <button className="text-sm" onClick={()=>{ window.history.pushState({}, '', '/'); window.dispatchEvent(new PopStateEvent('popstate')) }}>← Back</button>
            <SkillsList />
          </>
        )}
        {route.name === 'skill-detail' && (
          <>
            <button className="text-sm" onClick={()=>{ window.history.pushState({}, '', '/skills'); window.dispatchEvent(new PopStateEvent('popstate')) }}>← Back</button>
            <SkillDetailView slug={route.slug} />
          </>
        )}
      </div>
      <TasksModal isOpen={isTasksOpen} onClose={() => setIsTasksOpen(false)} />
    </div>
  )
}
