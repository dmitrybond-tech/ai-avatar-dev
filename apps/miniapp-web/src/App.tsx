import { useMemo, useState } from 'react'
import { PrimaryActions } from './components/Buttons'
import { SkillsList } from './components/Skills'
import { TasksModal } from './components/TasksModal'
import { ChatBox } from './components/Chat'

function useQuery() {
  return useMemo(() => new URLSearchParams(window.location.search), [])
}

export function App() {
  const _q = useQuery() // reserved for future
  const [view, setView] = useState<'home'|'skills'>('home')
  const [isTasksOpen, setIsTasksOpen] = useState(false)

  return (
    <div className="min-h-dvh w-full bg-white text-black">
      <div className="max-w-md mx-auto p-4 grid gap-4">
        <header className="flex items-center gap-3">
          <img
            src="/icons/android-chrome-192x192.png"
            alt="Dmitry"
            className="h-10 w-10 rounded-full object-cover"
            loading="eager"
            decoding="async"
          />
          <div className="font-semibold">Dmitry's Assistant</div>
        </header>
        {view === 'home' && (
          <>
            <PrimaryActions onSkills={()=>setView('skills')} onTasks={()=>setIsTasksOpen(true)} />
            <ChatBox />
          </>
        )}
        {view === 'skills' && (
          <>
            <button className="text-sm" onClick={()=>setView('home')}>← Back</button>
            <SkillsList />
          </>
        )}
      </div>
      <TasksModal isOpen={isTasksOpen} onClose={() => setIsTasksOpen(false)} />
    </div>
  )
}
