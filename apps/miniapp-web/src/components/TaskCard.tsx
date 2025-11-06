import type { PublicTask } from "../shared/api/tasks";

export default function TaskCard({ t }: { t: PublicTask }) {
  const pct = Math.max(0, Math.min(100, t.progressPct ?? 0));
  return (
    <a href={t.url} target="_blank" rel="noreferrer"
       className="block rounded-xl border p-4 hover:shadow-sm transition">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-base font-semibold leading-snug">{t.title}</h3>
        <span className="text-xs rounded-full px-2 py-0.5 border">{t.status}</span>
      </div>
      {t.description && (
        <p className="mt-2 text-sm text-gray-600 line-clamp-3">{t.description}</p>
      )}
      <div className="mt-3 text-xs text-gray-500">
        {(t.scope ?? null) != null && (t.done ?? null) != null ? (
          <span>Scope {t.done}/{t.scope}</span>
        ) : null}
        <span className="ml-2">Updated {new Date(t.lastUpdated).toLocaleString()}</span>
      </div>
      <div className="mt-3 h-2 w-full rounded bg-gray-200 overflow-hidden">
        <div style={{ width: `${pct}%` }} className="h-full rounded bg-black" />
      </div>
      {t.tags?.length ? (
        <div className="mt-3 flex flex-wrap gap-1">
          {t.tags.map((x) => (
            <span key={x} className="text-[10px] px-2 py-0.5 rounded-full border">{x}</span>
          ))}
        </div>
      ) : null}
    </a>
  );
}

