import { useCallback, useEffect, useMemo, useState } from 'react'
import type { SkillTile } from '../content/skills/types'
import { skills as skillsEn } from '../content/skills/en'
import { skills as skillsRu } from '../content/skills/ru'

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

const lists: Record<Lang, SkillTile[]> = {
  en: skillsEn,
  ru: skillsRu,
}

export function SkillsPage({ lang, selectedSlug, onBack, onSelect, onCloseDetail }: SkillsPageProps) {
  const items = lists[lang] ?? lists.ru

  const active = useMemo(() => {
    if (!selectedSlug) return null
    return items.find((item) => item.key === selectedSlug) ?? null
  }, [items, selectedSlug])

  const [drawerOpen, setDrawerOpen] = useState(() => Boolean(active))

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

  useEffect(() => {
    setDrawerOpen(Boolean(active))
  }, [active])

  useEffect(() => {
    if (selectedSlug && !active) {
      onCloseDetail()
    }
  }, [selectedSlug, active, onCloseDetail])

  useEffect(() => {
    if (!drawerOpen) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        handleClose()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [drawerOpen, handleClose])

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

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {items.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => handleSelect(item.key)}
            className="rounded-2xl border border-gray-200 bg-white p-4 text-left shadow-sm transition active:scale-[0.99] hover:-translate-y-0.5 hover:shadow"
            aria-haspopup="dialog"
            aria-expanded={active?.key === item.key && drawerOpen}
          >
            <div className="flex flex-col gap-2">
              <div className="text-base font-medium text-black">{item.title}</div>
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
          </button>
        ))}
      </section>

      {drawerOpen && active ? (
        <div
          className="fixed inset-0 z-50 flex flex-col justify-end bg-black/40 backdrop-blur-sm"
          role="presentation"
          onClick={handleClose}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label={active.title}
            className="relative mx-auto w-full max-w-lg translate-y-0 rounded-t-3xl bg-white p-5 shadow-lg transition sm:bottom-auto sm:mt-24 sm:rounded-3xl"
            style={{ maxHeight: '80vh' }}
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
            <div className="flex flex-col gap-3 overflow-y-auto pr-1" style={{ maxHeight: 'calc(80vh - 3rem)' }}>
              <div>
                <div className="text-lg font-semibold text-black">{active.title}</div>
                <div className="text-sm text-gray-600">{active.short}</div>
                {active.tags?.length ? (
                  <div className="mt-2 flex flex-wrap gap-2 text-xs text-gray-500">
                    {active.tags.map((tag) => (
                      <span key={tag} className="rounded-full bg-gray-100 px-2 py-0.5">
                        {tag}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
              <p className="whitespace-pre-line text-sm leading-relaxed text-gray-800">{active.details}</p>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  )
}


