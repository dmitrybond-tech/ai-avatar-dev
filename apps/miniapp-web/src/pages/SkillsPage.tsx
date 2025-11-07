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

const overlayPadding = 'calc(var(--app-header-height) + var(--modal-offset) + env(safe-area-inset-top, 0px))'
const modalMaxHeight = 'calc(100vh - var(--app-header-height) - var(--modal-offset) - env(safe-area-inset-top, 0px) - 24px)'

function sortSkills(list: Skill[]): Skill[] {
  return [...list].sort((a, b) => {
    const orderA = typeof a.order === 'number' ? a.order : Number.POSITIVE_INFINITY
    const orderB = typeof b.order === 'number' ? b.order : Number.POSITIVE_INFINITY
    if (orderA !== orderB) {
      return orderA - orderB
    }
    return a.name.localeCompare(b.name)
  })
}

export function SkillsPage({ lang, selectedSlug, onBack, onSelect, onCloseDetail }: SkillsPageProps) {
  const [skills, setSkills] = useState<Skill[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
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
  }, [lang])

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

  const listContent = useMemo(() => {
    if (error) {
      return (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
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
              {item.icon ? (
                <span className="text-2xl leading-none" aria-hidden="true">{item.icon}</span>
              ) : null}
              <div className="flex flex-col gap-2">
                <div className="text-base font-medium text-black">{item.name}</div>
                <div className="text-sm text-gray-600">{item.short}</div>
                {item.tags?.length ? (
                  <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                    {item.tags.map((tag) => (
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
  }, [skills, error, lang, handleSelect, activeSkill, drawerOpen])

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
          className="fixed inset-0 z-50 flex justify-center bg-black/40 px-4 pb-10 backdrop-blur-sm"
          style={{ paddingTop: overlayPadding, overflowY: 'auto', alignItems: 'flex-start' }}
          role="presentation"
          onClick={handleClose}
        >
          <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-label={activeSkill.name}
            tabIndex={-1}
            className="relative w-full max-w-lg rounded-3xl bg-white p-5 shadow-xl focus-visible:outline-none"
            style={{ maxHeight: modalMaxHeight, overflowY: 'auto' }}
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
            <SkillDetailView skill={activeSkill} />
          </div>
        </div>
      ) : null}
    </main>
  )
}


