import { useMemo } from 'react'
import type { Skill } from '../types'

type SkillDetailProps = {
  skill: Skill
}

export function SkillDetailView({ skill }: SkillDetailProps) {
  const richParagraphs = useMemo(() => {
    const chunks = skill.long.split(/\n{2,}/).map((segment) => segment.trim()).filter(Boolean)
    if (chunks.length) {
      return chunks
    }
    const fallback = (skill.long || skill.short || '').trim()
    return fallback ? [fallback] : []
  }, [skill.long, skill.short])

  return (
    <div className="grid gap-3">
      <div className="flex items-start gap-3">
        {skill.icon && (
          <span className="text-2xl leading-none" aria-hidden="true">
            {skill.icon}
          </span>
        )}
        <div className="space-y-1">
          <div className="text-lg font-semibold text-black">{skill.name}</div>
          {skill.category ? (
            <div className="text-xs uppercase tracking-wide text-gray-400">{skill.category}</div>
          ) : null}
          {skill.short && <div className="text-sm text-gray-600">{skill.short}</div>}
          {skill.tags?.length ? (
            <div className="mt-1 flex flex-wrap gap-2 text-xs text-gray-500">
              {skill.tags.map((tag) => (
                <span key={tag} className="rounded-full bg-gray-100 px-2 py-0.5">{tag}</span>
              ))}
            </div>
          ) : null}
        </div>
      </div>

      <div className="space-y-3 text-sm leading-relaxed text-gray-800">
        {richParagraphs.map((paragraph, index) => (
          <p key={index} className="whitespace-pre-line">
            {paragraph}
          </p>
        ))}
      </div>
    </div>
  )
}

