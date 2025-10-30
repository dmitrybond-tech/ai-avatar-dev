import { useEffect, useState } from "react";
import { getTasks } from "../api/client";
import type { TaskItem } from "../types";

export function TasksList() {
  const [items, setItems] = useState<TaskItem[] | null>(null);

  useEffect(() => {
    let alive = true;
    getTasks().then((r) => alive && setItems(r.items)).catch(() => setItems([]));
    return () => { alive = false };
  }, []);

  if (!items) {
    return <div className="grid gap-2">{Array.from({ length: 3 }).map((_,i) => (
      <div key={i} className="h-10 rounded bg-gray-100 animate-pulse" />
    ))}</div>;
  }

  return (
    <div className="grid gap-2">
      {items.map((t) => (
        <div key={t.id} className="p-3 rounded border border-gray-200 flex items-center justify-between">
          <div>
            <div className="font-medium">{t.title}</div>
            <div className="text-xs text-gray-500">{new Date(t.updatedAt).toLocaleString()}</div>
          </div>
          <span className="text-xs uppercase text-gray-700">{t.status}</span>
        </div>
      ))}
    </div>
  );
}


