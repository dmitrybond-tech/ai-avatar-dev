import { useEffect, useState } from "react";
import { fetchOpenTasks, type PublicTask } from "../shared/api/tasks";
import TaskCard from "./TaskCard";

type Props = {
  isOpen: boolean;
  onClose: () => void;
};

export function TasksModal({ isOpen, onClose }: Props) {
  const [items, setItems] = useState<PublicTask[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    
    let ok = true;
    setItems(null);
    setErr(null);
    fetchOpenTasks()
      .then((d) => ok && setItems(d))
      .catch((e) => ok && setErr(String(e)));
    return () => { ok = false; };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-end sm:items-center justify-center p-4 z-50">
      <div className="w-full sm:max-w-2xl bg-white rounded-2xl p-4 shadow-xl">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Task Status</h2>
          <button onClick={onClose} className="text-sm px-2 py-1">×</button>
        </div>

        {!items && !err && (
          <div className="mt-6 space-y-2">
            <div className="h-4 bg-gray-200 rounded animate-pulse" />
            <div className="h-4 bg-gray-200 rounded animate-pulse w-3/4" />
            <div className="h-4 bg-gray-200 rounded animate-pulse w-1/2" />
          </div>
        )}
        {err && (
          <div className="mt-6 p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="text-sm font-medium text-red-800">Can't reach Notion right now</div>
            <div className="text-xs text-red-600 mt-1">Please try again later.</div>
          </div>
        )}

        {items?.length ? (
          <div className="mt-4 space-y-3">
            {items.map((t) => <TaskCard key={t.id} t={t} />)}
          </div>
        ) : items && !items.length ? (
          <div className="mt-6 text-sm text-gray-500">Nothing in progress yet.</div>
        ) : null}
      </div>
    </div>
  );
}
