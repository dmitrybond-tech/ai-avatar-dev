import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { getSkillDetail, getSkills } from '../api/client'
import { SkillDetailView } from '../components/SkillDetail'
import type { SkillCard, SkillDetail } from '../types'

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

export function SkillsPage({ lang, selectedSlug, onBack, onSelect, onCloseDetail }: SkillsPageProps) {
  const [skills, setSkills] = useState<SkillCard[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [reloadToken, setReloadToken] = useState(0)
  const [detailsCache, setDetailsCache] = useState<Record<string, SkillDetail>>({})
  const [activeDetail, setActiveDetail] = useState<SkillDetail | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailReloadToken, setDetailReloadToken] = useState(0)
  const dialogRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    let active = true
    const controller = new AbortController()
    setSkills(null)
    setError(null)

    getSkills(lang, controller.signal)
      .then((list) => {
        if (!active) return
        setSkills(list)
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

  useEffect(() => {
    setDrawerOpen(Boolean(selectedSlug))
  }, [selectedSlug])

  useEffect(() => {
    if (!selectedSlug || !skills) return
    if (!skills.some((item) => item.slug === selectedSlug)) {
      onCloseDetail()
    }
  }, [selectedSlug, skills, onCloseDetail])

  useEffect(() => {
    setDetailsCache({})
    setActiveDetail(null)
    setDetailError(null)
    setDetailReloadToken(0)
  }, [lang])

  const cachedDetail = useMemo(() => {
    if (!selectedSlug) return undefined
    return detailsCache[selectedSlug]
  }, [selectedSlug, detailsCache])

  useEffect(() => {
    if (!selectedSlug) {
      setActiveDetail(null)
      setDetailError(null)
      setDetailLoading(false)
      return
    }

    if (cachedDetail) {
      setActiveDetail(cachedDetail)
      setDetailError(null)
      setDetailLoading(false)
      return
    }

    let active = true
    const controller = new AbortController()
    setDetailLoading(true)
    setDetailError(null)
    setActiveDetail(null)

    getSkillDetail(selectedSlug, lang, controller.signal)
      .then((detail) => {
        if (!active) return
        setDetailsCache((prev) => ({ ...prev, [detail.slug]: detail }))
        setActiveDetail(detail)
        setDetailLoading(false)
      })
      .catch((err) => {
        if (!active) return
        setDetailError(err instanceof Error ? err.message : String(err))
        setDetailLoading(false)
      })

    return () => {
      active = false
      controller.abort()
    }
  }, [selectedSlug, lang, detailReloadToken, cachedDetail])

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

  const handleRetryDetail = useCallback(() => {
    if (!selectedSlug) return
    setDetailsCache((prev) => {
      if (selectedSlug in prev) {
        const next = { ...prev }
        delete next[selectedSlug]
        return next
      }
      return prev
    })
    setDetailReloadToken((token) => token + 1)
  }, [selectedSlug])

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
        {skills.map((item) => {
          const isActive = selectedSlug === item.slug && drawerOpen
          const uniqueTags = item.tags ? Array.from(new Set(item.tags)) : []
          return (
            <button
              key={item.slug}
              type="button"
              onClick={() => handleSelect(item.slug)}
              className="rounded-2xl border border-gray-200 bg-white p-4 text-left shadow-sm transition active:scale-[0.99] hover:-translate-y-0.5 hover:shadow"
              aria-haspopup="dialog"
              aria-expanded={isActive}
            >
              <div className="flex flex-col gap-2">
                <div className="text-base font-medium text-black">{item.title}</div>
                {item.short ? <div className="text-sm text-gray-600 clamp-2">{item.short}</div> : null}
                {uniqueTags.length ? (
                  <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                    {uniqueTags.map((tag) => (
                      <span key={tag} className="rounded-full bg-gray-100 px-2 py-0.5">
                        {tag}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            </button>
          )
        })}
      </section>
    )
  }, [skills, error, lang, handleSelect, selectedSlug, drawerOpen, handleRetry])

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

      {drawerOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto modal-offset-pt bg-black/40 px-4 pb-10 backdrop-blur-sm"
          role="presentation"
          onClick={handleClose}
        >
          <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-label={activeDetail?.title ?? selectedSlug ?? titles[lang]}
            tabIndex={-1}
            className="relative modal-offset-mt modal-maxh w-full overflow-auto max-w-lg rounded-3xl bg-white p-5 shadow-xl focus-visible:outline-none"
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
            {detailLoading ? (
              <div className="space-y-4">
                <div className="h-6 w-2/3 animate-pulse rounded bg-gray-100" />
                <div className="space-y-2">
                  <div className="h-4 animate-pulse rounded bg-gray-100" />
                  <div className="h-4 animate-pulse rounded bg-gray-100" />
                  <div className="h-4 animate-pulse rounded bg-gray-100" />
                </div>
              </div>
            ) : detailError ? (
              <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                <p>{lang === 'ru' ? 'Не удалось загрузить навык.' : 'Failed to load the skill.'}</p>
                <p className="mt-1 text-xs text-red-600">{detailError}</p>
                <button
                  type="button"
                  onClick={handleRetryDetail}
                  className="mt-3 inline-flex items-center justify-center rounded-md border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-700 transition hover:border-red-300 hover:text-red-800"
                >
                  {lang === 'ru' ? 'Попробовать ещё раз' : 'Try again'}
                </button>
              </div>
            ) : activeDetail ? (
              <SkillDetailView skill={activeDetail} lang={lang} />
            ) : (
              <div className="text-sm text-gray-500">
                {lang === 'ru' ? 'Навык не найден.' : 'Skill not found.'}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </main>
  )
}


