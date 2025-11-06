import { apiUrl } from "../lib/apiBase.ts";
import type { TasksStatusResponse, CalLinkResponse, ChatOut, ProjectedSkill, ProjectedSkillDetail } from "../types";

// New skills endpoints
export async function getSkills(lang?: 'ru' | 'en'): Promise<ProjectedSkill[]> {
  const qs = lang ? `?lang=${lang}` : '';
  const r = await fetch(apiUrl(`/skills${qs}`));
  return r.json();
}

export async function getSkillDetail(slug: string, lang?: 'ru' | 'en'): Promise<ProjectedSkillDetail> {
  const qs = lang ? `?lang=${lang}` : '';
  const r = await fetch(apiUrl(`/skills/${encodeURIComponent(slug)}${qs}`));
  if (!r.ok) throw new Error(`Skill ${slug} not found`);
  return r.json();
}

// Legacy alias preserved during rollout
export async function getRules(lang?: 'ru' | 'en'): Promise<{ items: ProjectedSkill[] }> {
  const qs = lang ? `?lang=${lang}` : '';
  const r = await fetch(apiUrl(`/rules${qs}`));
  const items: ProjectedSkill[] = await r.json();
  // Server returns array for /rules; adapt to old shape
  return { items };
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


