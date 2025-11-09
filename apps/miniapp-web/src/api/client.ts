import { apiUrl } from "../lib/apiBase.ts";
import type { Locale } from "../shared/i18n/resolveLocale";
import type { TasksStatusResponse, CalLinkResponse, ChatOut, SkillCard, SkillDetail } from "../types";

// New skills endpoints
function ensureStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter((item) => item.length > 0);
}

export async function getSkills(lang: Locale, signal?: AbortSignal): Promise<SkillCard[]> {
  const qs = `?lang=${lang}`;
  const r = await fetch(apiUrl(`/api/skills${qs}`), {
    signal,
    headers: {
      "X-Locale": lang,
      "Accept-Language": lang,
    },
  });
  if (!r.ok) {
    throw new Error(`Failed to load skills (status ${r.status})`);
  }
  const data = await r.json();
  if (!Array.isArray(data)) {
    return [];
  }
  return data
    .map((item) => ({
      slug: typeof item?.slug === "string" ? item.slug : "",
      title: typeof item?.title === "string" ? item.title : "",
      short: typeof item?.short === "string" ? item.short : "",
      tags: ensureStringArray(item?.tags),
    }))
    .filter((item) => item.slug && item.title);
}

export async function getSkillDetail(slug: string, lang: Locale, signal?: AbortSignal): Promise<SkillDetail> {
  const qs = `?lang=${lang}`;
  const r = await fetch(apiUrl(`/api/skills/${encodeURIComponent(slug)}${qs}`), {
    signal,
    headers: {
      "X-Locale": lang,
      "Accept-Language": lang,
    },
  });
  if (!r.ok) {
    throw new Error(`Skill ${slug} not found (status ${r.status})`);
  }
  const payload = await r.json();
  return {
    slug: typeof payload?.slug === "string" ? payload.slug : slug,
    title: typeof payload?.title === "string" ? payload.title : slug,
    short: typeof payload?.short === "string" ? payload.short : undefined,
    tags: ensureStringArray(payload?.tags),
    bullets: ensureStringArray(payload?.bullets),
    examples: ensureStringArray(payload?.examples),
  };
}

export async function getTasks(): Promise<TasksStatusResponse> {
  const r = await fetch(apiUrl("/tasks/status"));
  return r.json();
}

export async function getCal(): Promise<CalLinkResponse> {
  const r = await fetch(apiUrl("/cal/link"));
  return r.json();
}

export async function postChat(text: string): Promise<ChatOut> {
  const r = await fetch(apiUrl("/api/chat/stub"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: text }),
  });
  return r.json();
}


type ClientLogPayload = {
  ua: string;
  location: string;
  message: string;
  stack?: string;
}

export async function postClientLog(payload: ClientLogPayload): Promise<void> {
  try {
    // Only attempt when inside Telegram WebView (UA or SDK present)
    const isTG = /Telegram/i.test(navigator.userAgent) || !!(window as any)?.Telegram?.WebApp;
    if (!isTG) return;
    await fetch(apiUrl('/api/client-log'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      // Do not send credentials to avoid CORS complications
    });
  } catch {
    // best-effort only
  }
}


