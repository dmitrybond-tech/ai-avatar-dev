import { useEffect, useState } from "react";
import { fetchOpenTasks, type PublicTask } from "../shared/api/tasks";

type Props = {
  onClose?: () => void;
};

export function TasksList({ onClose }: Props) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<PublicTask[]>([]);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const tasks = await fetchOpenTasks();
        if (alive) setItems(tasks);
      } catch (e: any) {
        if (alive) setError(e?.message ?? "Failed to load tasks");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false };
  }, []);

  const isOverdue = (reviewAt?: string) => {
    if (!reviewAt) return false;
    return new Date(reviewAt) < new Date();
  };

  const formatRelativeTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="grid gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-24 rounded-lg animate-pulse bg-gray-200" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-600 text-sm">
        Error: {error}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        Nothing in progress yet.
      </div>
    );
  }

  return (
    <div className="grid gap-3">
      {items.map((t) => {
        const overdue = isOverdue(t.reviewAt);
        return (
          <a
            key={t.id}
            href={t.url}
            target="_blank"
            rel="noreferrer"
            className={`block rounded-lg p-4 border hover:shadow-md transition ${
              overdue ? "border-red-300 bg-red-50" : "border-gray-200 bg-white"
            }`}
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="text-sm font-medium line-clamp-2 flex-1">
                {t.title}
              </div>
              <span className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-700 whitespace-nowrap">
                {t.status}
              </span>
            </div>
            <div className="h-2 rounded bg-gray-100 mt-2 mb-2">
              <div
                className="h-2 rounded bg-gray-400"
                style={{ width: `${t.progressPct}%` }}
              />
            </div>
            {t.tags.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {t.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 border text-gray-700"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
            <div
              className={`mt-2 text-[11px] ${
                overdue ? "text-red-600 font-semibold" : "text-gray-500"
              }`}
            >
              {t.reviewAt ? (
                <>
                  Review: {new Date(t.reviewAt).toLocaleString()}
                  {overdue && " (overdue)"}
                </>
              ) : (
                <>Updated: {formatRelativeTime(t.lastUpdated)}</>
              )}
            </div>
          </a>
        );
      })}
    </div>
  );
}
