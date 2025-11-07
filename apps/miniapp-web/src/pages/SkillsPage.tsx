import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { getSkills } from '../api/client'
import { SkillDetailView } from '../components/SkillDetail'
import type { Skill } from '../types'

type Lang = 'ru' | 'en'

type SkillsPageProps = {
  lang: Lang
  selectedSlug?: string | null
  onBack: () => void
  onSelect: (slug: string) => void
  onCloseDetail: () => void
}

const titles: Record<Lang, string> = {
  ru: 'Навыки',
  en: 'Skills',
}

function sortSkills(list: Skill[]): Skill[] {
  return [...list].sort((a, b) => {
    const orderA = typeof a.order === 'number' ? a.order : Number.POSITIVE_INFINITY
    const orderB = typeof b.order === 'number' ? b.order : Number.POSITIVE_INFINITY
    if (orderA !== orderB) {
      return orderA - orderB
    }
    return a.title.localeCompare(b.title)
  })
}

export function SkillsPage({ lang, selectedSlug, onBack, onSelect, onCloseDetail }: SkillsPageProps) {
  const [skills, setSkills] = useState<Skill[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [reloadToken, setReloadToken] = useState(0)
  const dialogRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    let active = true
    const controller = new AbortController()
    setSkills(null)
    setError(null)

    getSkills(lang, controller.signal)
      .then((list) => {
        if (!active) return
        setSkills(sortSkills(list))
      })
      .catch((err) => {
        if (!active) return
        setError(err instanceof Error ? err.message : String(err))
        setSkills([])
      })

    return () => {
      active = false
      controller.abort()
    }
  }, [lang, reloadToken])

  const activeSkill = useMemo(() => {
    if (!selectedSlug || !skills?.length) return null
    return skills.find((item) => item.slug === selectedSlug) ?? null
  }, [selectedSlug, skills])

  useEffect(() => {
    setDrawerOpen(Boolean(activeSkill))
  }, [activeSkill])

  useEffect(() => {
    if (selectedSlug && skills && !activeSkill) {
      onCloseDetail()
    }
  }, [selectedSlug, skills, activeSkill, onCloseDetail])

  useEffect(() => {
    if (!drawerOpen) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onCloseDetail()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [drawerOpen, onCloseDetail])

  useEffect(() => {
    if (!drawerOpen) return
    const node = dialogRef.current
    node?.focus({ preventScroll: true })
  }, [drawerOpen])

  const handleSelect = useCallback(
    (slug: string) => {
      onSelect(slug)
    },
    [onSelect],
  )

  const handleClose = useCallback(() => {
    setDrawerOpen(false)
    onCloseDetail()
  }, [onCloseDetail])

  const handleRetry = useCallback(() => {
    setReloadToken((token) => token + 1)
  }, [])

  const listContent = useMemo(() => {
    if (error) {
      return (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <p>{lang === 'ru' ? 'Не удалось загрузить навыки.' : 'Failed to load skills.'}</p>
          <p className="mt-1 text-xs text-red-600">{error}</p>
          <button
            type="button"
            onClick={handleRetry}
            className="mt-3 inline-flex items-center justify-center rounded-md border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-700 transition hover:border-red-300 hover:text-red-800"
          >
            {lang === 'ru' ? 'Попробовать ещё раз' : 'Try again'}
          </button>
        </div>
      )
    }

    if (!skills) {
      return (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-24 rounded-2xl bg-gray-100 animate-pulse" />
          ))}
        </div>
      )
    }

    if (!skills.length) {
      return (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-500">
          {lang === 'ru' ? 'Пока нет навыков для отображения.' : 'No skills are published yet.'}
        </div>
      )
    }

    return (
      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {skills.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => handleSelect(item.slug)}
            className="rounded-2xl border border-gray-200 bg-white p-4 text-left shadow-sm transition active:scale-[0.99] hover:-translate-y-0.5 hover:shadow"
            aria-haspopup="dialog"
            aria-expanded={activeSkill?.slug === item.slug && drawerOpen}
          >
            <div className="flex gap-3">
              <div className="flex flex-col gap-2">
                <div className="text-base font-medium text-black">{item.title}</div>
                <div className="text-sm text-gray-600">{item.short}</div>
                {item.tags?.length ? (
                  <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                    {Array.from(new Set(item.tags)).map((tag) => (
                      <span key={tag} className="rounded-full bg-gray-100 px-2 py-0.5">
                        {tag}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          </button>
        ))}
      </section>
    )
  }, [skills, error, lang, handleSelect, activeSkill, drawerOpen, handleRetry])

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col gap-4 p-4">
      <header className="flex items-center gap-3">
        <button
          type="button"
          onClick={onBack}
          className="text-sm text-gray-600 transition hover:text-black"
        >
          {lang === 'ru' ? '← Назад' : '← Back'}
        </button>
        <h1 className="text-lg font-semibold text-black">{titles[lang]}</h1>
      </header>

      {listContent}

      {drawerOpen && activeSkill ? (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 px-4 pb-10 pt-[var(--modal-top-offset)] backdrop-blur-sm"
          role="presentation"
          onClick={handleClose}
        >
          <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-label={activeSkill.title}
            tabIndex={-1}
            className="relative w-full max-h-[calc(100dvh_-_var(--modal-top-offset)_-_24px)] overflow-y-auto max-w-lg rounded-3xl bg-white p-5 shadow-xl focus-visible:outline-none"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              onClick={handleClose}
              className="absolute right-4 top-4 text-gray-500 transition hover:text-black"
              aria-label={lang === 'ru' ? 'Закрыть' : 'Close'}
            >
              ×
            </button>
            <SkillDetailView skill={activeSkill} lang={lang} />
          </div>
        </div>
      ) : null}
    </main>
  )
}


