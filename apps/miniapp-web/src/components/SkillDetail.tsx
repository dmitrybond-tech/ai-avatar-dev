import type { SkillDetail } from '../types'

type SkillDetailProps = {
  skill: SkillDetail
  lang: 'ru' | 'en'
}

const sectionLabels = {
  bullets: {
    en: 'What this skill covers',
    ru: 'Что входит в навык',
  },
  examples: {
    en: 'Examples',
    ru: 'Примеры',
  },
}

export function SkillDetailView({ skill, lang }: SkillDetailProps) {
  const pills = skill.tags?.length ? Array.from(new Set(skill.tags)) : []
  return (
    <div className="grid gap-3">
      <div className="space-y-1">
        <div className="text-lg font-semibold text-black">{skill.title}</div>
        {skill.short ? <div className="text-sm text-gray-600">{skill.short}</div> : null}
        {pills.length ? (
          <div className="mt-1 flex flex-wrap gap-2 text-xs text-gray-500">
            {pills.map((tag) => (
              <span key={tag} className="rounded-full bg-gray-100 px-2 py-0.5">{tag}</span>
            ))}
          </div>
        ) : null}
      </div>

      {skill.bullets?.length ? (
        <section className="space-y-2">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">
            {lang === 'ru' ? 'Что делаю' : 'What I do'}
          </h2>
          <ul className="space-y-2 text-sm leading-relaxed text-gray-800">
            {skill.bullets.map((line, index) => (
              <li key={index} className="flex items-start gap-2">
                <span className="mt-1 flex-shrink-0 text-gray-400">✓</span>
                <span>{line}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {skill.examples?.length ? (
        <section className="space-y-2">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">
            {lang === 'ru' ? 'Примеры' : 'Examples'}
          </h2>
          <div className="space-y-2 text-sm leading-relaxed text-gray-700">
            {skill.examples.map((example, index) => (
              <p key={index} className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2">
                {example}
              </p>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}

