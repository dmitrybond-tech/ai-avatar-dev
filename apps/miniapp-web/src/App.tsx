import { useMemo, useState } from 'react'
import { PrimaryActions } from './components/Buttons'
import { SkillsList } from './components/Skills'
import { TasksList } from './components/Tasks'
import TasksBoard from './components/TasksBoard'
import { ChatBox } from './components/Chat'

function useQuery() {
  return useMemo(() => new URLSearchParams(window.location.search), [])
}

export function App() {
  const _q = useQuery() // reserved for future
  const [view, setView] = useState<'home'|'skills'|'tasks'>('home')

  return (
    <div className="min-h-dvh w-full bg-white text-black">
      <div className="max-w-md mx-auto p-4 grid gap-4">
        <header className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gray-200" />
          <div className="font-semibold">Дима’s Assistant</div>
        </header>
        {view === 'home' && (
          <>
            <PrimaryActions onSkills={()=>setView('skills')} onTasks={()=>setView('tasks')} />
            <ChatBox />
            <TasksBoard />
          </>
        )}
        {view === 'skills' && (
          <>
            <button className="text-sm" onClick={()=>setView('home')}>← Back</button>
            <SkillsList />
          </>
        )}
        {view === 'tasks' && (
          <>
            <button className="text-sm" onClick={()=>setView('home')}>← Back</button>
            <TasksList />
          </>
        )}
      </div>
    </div>
  )
}
