import { useEffect, useState } from "react";
import { getSkills } from "../api/client";
import type { ProjectedSkill } from "../types";

function getLang(): 'ru' | 'en' {
  return (navigator.language || '').toLowerCase().startsWith('ru') ? 'ru' : 'en';
}

export function SkillsList() {
  const [items, setItems] = useState<ProjectedSkill[] | null>(null);

  useEffect(() => {
    let alive = true;
    getSkills(getLang()).then((list) => alive && setItems(list)).catch(() => setItems([]));
    return () => { alive = false };
  }, []);

  if (!items) {
    return <div className="grid gap-2">{Array.from({ length: 4 }).map((_,i) => (
      <div key={i} className="h-12 rounded bg-gray-100 animate-pulse" />
    ))}</div>;
  }

  function open(slug: string) {
    const url = `/skills/${slug}`;
    window.history.pushState({}, '', url);
    window.dispatchEvent(new PopStateEvent('popstate'));
  }

  return (
    <div className="grid gap-2">
      {items.map((s) => (
        <button
          key={s.slug}
          className="p-3 rounded border border-gray-200 text-left active:scale-[0.99]"
          onClick={() => open(s.slug)}
        >
          <div className="flex items-start gap-2">
            {s.icon && <span className="text-xl leading-none">{s.icon}</span>}
            <div className="flex-1">
              <div className="font-medium">{s.title}</div>
              {s.short && <div className="text-sm text-gray-600">{s.short}</div>}
              {s.tags?.length ? (
                <div className="mt-1 text-xs text-gray-500 truncate">{s.tags.join(', ')}</div>
              ) : null}
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}


