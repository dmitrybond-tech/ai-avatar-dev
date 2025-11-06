import { useEffect, useMemo, useState } from "react";
import { fetchPublicTasks, type PublicTask } from "../shared/api/tasks";

export default function TasksBoard() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [tasks, setTasks] = useState<PublicTask[]>([]);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const items = await fetchPublicTasks();
        if (alive) setTasks(items);
      } catch (e: any) {
        if (alive) setErr(e?.message ?? "Failed to load");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false };
  }, []);

  const byStatus = useMemo(() => {
    const groups: Record<string, PublicTask[]> = {
      Backlog: [], "In Progress": [], Review: [], Blocked: [], Done: [], Other: []
    };
    for (const t of tasks) {
      (groups[t.status] ?? groups.Other).push(t);
    }
    return groups;
  }, [tasks]);

  if (loading) {
    return (
      <div className="grid gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-20 rounded-lg animate-pulse bg-gray-200" />
        ))}
      </div>
    );
  }
  if (err) return <div className="text-red-600 text-sm">Error: {err}</div>;

  const Column = ({ title, items }: { title: string; items: PublicTask[] }) => {
    const isOverdue = (reviewAt?: string) => {
      if (!reviewAt) return false;
      return new Date(reviewAt) < new Date();
    };

    return (
      <div>
        <div className="font-semibold mb-2">{title} ({items.length})</div>
        <div className="grid gap-2">
          {items.map(t => {
            const overdue = isOverdue(t.reviewAt);
            return (
              <a key={t.id} href={t.url} target="_blank" rel="noreferrer"
                 className={`block rounded-lg p-3 border hover:shadow-sm transition ${overdue ? 'border-red-300 bg-red-50' : ''}`}>
                <div className="text-sm font-medium line-clamp-2">{t.title}</div>
                <div className="h-2 rounded bg-gray-100 mt-2">
                  <div className="h-2 rounded bg-gray-400" style={{ width: `${t.progressPct}%` }} />
                </div>
                <div className="flex flex-wrap gap-1 mt-2">
                  {t.tags.map(tag => (
                    <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 border text-gray-700">{tag}</span>
                  ))}
                </div>
                <div className={`mt-2 text-[11px] ${overdue ? 'text-red-600 font-semibold' : 'text-gray-500'}`}>
                  {t.reviewAt ? `Review: ${new Date(t.reviewAt).toLocaleString()}` : `Updated: ${new Date(t.lastUpdated).toLocaleString()}`}
                </div>
              </a>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <Column title="Backlog" items={byStatus["Backlog"]} />
      <Column title="In Progress" items={byStatus["In Progress"]} />
      <Column title="Review" items={byStatus["Review"]} />
      <Column title="Blocked" items={byStatus["Blocked"]} />
      <Column title="Done" items={byStatus["Done"]} />
      {!!byStatus.Other.length && <Column title="Other" items={byStatus.Other} />}
    </div>
  );
}


