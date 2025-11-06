import { useEffect, useState } from 'react'
import { getSkillDetail } from '../api/client'
import type { ProjectedSkillDetail } from '../types'

function getLang(): 'ru' | 'en' {
  return (navigator.language || '').toLowerCase().startsWith('ru') ? 'ru' : 'en';
}

export function SkillDetailView({ slug }: { slug: string }) {
  const [data, setData] = useState<ProjectedSkillDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    setError(null)
    setData(null)
    getSkillDetail(slug, getLang()).then(d => { if (alive) setData(d) }).catch(e => { if (alive) setError(String(e)) })
    return () => { alive = false }
  }, [slug])

  if (error) {
    return <div className="text-sm text-red-600">{error}</div>
  }
  if (!data) {
    return (
      <div className="grid gap-2">
        <div className="h-6 w-40 bg-gray-100 rounded animate-pulse" />
        <div className="h-4 w-64 bg-gray-100 rounded animate-pulse" />
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-4 w-full bg-gray-100 rounded animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <div className="grid gap-3">
      <div className="flex items-start gap-2">
        {data.icon && <span className="text-2xl leading-none">{data.icon}</span>}
        <div>
          <div className="font-semibold text-lg">{data.title}</div>
          {data.short && <div className="text-sm text-gray-600">{data.short}</div>}
          {data.tags?.length ? <div className="mt-1 text-xs text-gray-500">{data.tags.join(', ')}</div> : null}
        </div>
      </div>

      {data.bullets?.length ? (
        <ul className="list-disc pl-5 space-y-1 text-sm">
          {data.bullets.map((b, i) => <li key={i}>{b}</li>)}
        </ul>
      ) : null}

      {data.examples?.length ? (
        <div className="text-sm">
          <div className="font-medium mb-1">Examples</div>
          <ul className="list-disc pl-5 space-y-1">
            {data.examples.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      ) : null}
    </div>
  )
}


