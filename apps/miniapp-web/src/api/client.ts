import { apiUrl, CHAT_ASK_URL, CHAT_CONFIG_URL, CHAT_EXPORT_URL } from "../lib/apiBase.ts";
import type { Locale } from "../shared/i18n/resolveLocale";
import type {
  TasksStatusResponse,
  CalLinkResponse,
  ChatOut,
  ChatConfig,
  ChatAskPayload,
  ChatExportPayload,
  SkillCard,
  SkillDetail,
} from "../types";

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

export async function getChatConfig(signal?: AbortSignal): Promise<ChatConfig> {
  const r = await fetch(CHAT_CONFIG_URL, { signal });
  if (!r.ok) {
    throw new Error(`Failed to load chat config (status ${r.status})`);
  }
  const payload = await r.json();
  return {
    persona: typeof payload?.persona === "string" ? payload.persona : "dima",
    smart_chat: Boolean(payload?.smart_chat),
    rag_mode: payload?.rag_mode === "llm" ? "llm" : "extractive",
    provider: typeof payload?.provider === "string" ? payload.provider : "openai",
    model: typeof payload?.model === "string" ? payload.model : "",
  };
}

export class ChatRequestError extends Error {
  readonly status: number;
  readonly url: string;
  readonly responseSnippet: string;

  constructor(status: number, url: string, responseSnippet: string) {
    super("Chat request failed");
    this.name = "ChatRequestError";
    this.status = status;
    this.url = url;
    this.responseSnippet = responseSnippet;
  }
}

export async function postChat(payload: ChatAskPayload, signal?: AbortSignal): Promise<ChatOut> {
  let r: Response;
  try {
    r = await fetch(CHAT_ASK_URL, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
      signal,
    });
  } catch (networkErr) {
    throw new ChatRequestError(
      0,
      CHAT_ASK_URL,
      networkErr instanceof Error ? networkErr.message : String(networkErr),
    );
  }
  if (!r.ok) {
    let text = "";
    try {
      text = await r.text();
    } catch {
      text = "";
    }
    const snippet = text.length > 200 ? `${text.slice(0, 200)}…` : text;
    throw new ChatRequestError(r.status, r.url || CHAT_ASK_URL, snippet.trim());
  }
  const data = await r.json();
  return {
    reply: typeof data?.reply === "string" && data.reply.trim().length > 0 ? data.reply : "",
    mode: data?.mode === "llm" ? "llm" : "stub",
    session_id: typeof data?.session_id === "string" ? data.session_id : "",
    persona: typeof data?.persona === "string" ? data.persona : "dima",
  };
}

export async function postChatExport(payload: ChatExportPayload): Promise<void> {
  const r = await fetch(CHAT_EXPORT_URL, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    const snippet = await r.text().catch(() => "");
    throw new ChatRequestError(r.status, r.url || CHAT_EXPORT_URL, snippet.slice(0, 200));
  }
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


