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
        {((t.scope ?? null) != null || (t.done ?? null) != null) && (
          <span>
            {(t.scope ?? null) != null && (t.done ?? null) != null ? (
              <>Scope {t.scope} • Done {t.done}</>
            ) : (t.scope ?? null) != null ? (
              <>Scope {t.scope}</>
            ) : (
              <>Done {t.done}</>
            )}
          </span>
        )}
        {t.lastUpdated && (
          <span className={((t.scope ?? null) != null || (t.done ?? null) != null) ? "ml-2" : ""}>
            Updated {new Date(t.lastUpdated).toLocaleDateString(undefined, { 
              month: 'short', 
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            })}
          </span>
        )}
      </div>
      <div className="mt-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-gray-600">Progress</span>
          <span className="text-xs font-medium text-gray-700">{pct}%</span>
        </div>
        <div className="h-2 w-full rounded bg-gray-200 overflow-hidden">
          <div style={{ width: `${pct}%` }} className="h-full rounded bg-black" />
        </div>
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

