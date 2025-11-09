import { useEffect, useState } from "react";
import { getSkills } from "../api/client";
import type { SkillCard } from "../types";

function getLang(): 'ru' | 'en' {
  return (navigator.language || '').toLowerCase().startsWith('ru') ? 'ru' : 'en';
}

export function SkillsList() {
  const [items, setItems] = useState<SkillCard[] | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let alive = true;
    getSkills(getLang(), controller.signal)
      .then((list) => alive && setItems(list))
      .catch(() => alive && setItems([]));
    return () => {
      alive = false;
      controller.abort();
    };
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
          <div className="flex flex-col gap-2">
            <div className="font-medium">{s.title}</div>
            {s.short ? <div className="text-sm text-gray-600 clamp-2">{s.short}</div> : null}
            {s.tags?.length ? (
              <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                {Array.from(new Set(s.tags)).map((tag) => (
                  <span key={tag} className="rounded-full bg-gray-100 px-2 py-0.5">
                    {tag}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        </button>
      ))}
    </div>
  );
}


