import { useEffect, useState } from "react";
import { getRules } from "../api/client";
import type { SkillItem } from "../types";

export function SkillsList() {
  const [items, setItems] = useState<SkillItem[] | null>(null);

  useEffect(() => {
    let alive = true;
    getRules().then((r) => alive && setItems(r.items)).catch(() => setItems([]));
    return () => { alive = false };
  }, []);

  if (!items) {
    return <div className="grid gap-2">{Array.from({ length: 4 }).map((_,i) => (
      <div key={i} className="h-12 rounded bg-gray-100 animate-pulse" />
    ))}</div>;
  }

  return (
    <div className="grid gap-2">
      {items.map((s) => (
        <div key={s.id} className="p-3 rounded border border-gray-200">
          <div className="font-medium">{s.title}</div>
          {s.desc && <div className="text-sm text-gray-600">{s.desc}</div>}
          {s.tags && <div className="mt-1 text-xs text-gray-500">{s.tags.join(', ')}</div>}
        </div>
      ))}
    </div>
  );
}


