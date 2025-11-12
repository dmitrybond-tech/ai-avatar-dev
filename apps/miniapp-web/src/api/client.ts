import { apiFetch, getApiBaseUrl } from "../lib/api.ts";
import { apiUrl } from "../shared/api.ts";
import type { Locale } from "../shared/i18n/resolveLocale";
import type {
  TasksStatusResponse,
  CalLinkResponse,
  ChatConfig,
  ChatAskPayload,
  ChatExportPayload,
  ChatAskResponse,
  SkillCard,
  SkillDetail,
  ChatMessageDto,
} from "../types";

export const CONFIG_ENDPOINT = "/config";
export const ASK_ENDPOINT = "/ask";
export const EXPORT_TELEGRAM_ENDPOINT = "/export/telegram";
export const CLIENT_LOG_ENDPOINT = "/client-log";

// New skills endpoints
function ensureStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter((item) => item.length > 0);
}

export async function getSkills(lang: Locale, signal?: AbortSignal): Promise<SkillCard[]> {
  const qs = `?lang=${lang}`;
  const r = await fetch(apiUrl(`/skills${qs}`), {
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
  // Guard: handle both array and {items,count} shapes
  const items = Array.isArray(data) ? data : (data?.items || []);
  if (!Array.isArray(items)) {
    return [];
  }
  return items
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
  const r = await fetch(apiUrl(`/skills/${encodeURIComponent(slug)}${qs}`), {
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

export type SkillsAskRequest = {
  q: string;
  lang?: "ru" | "en";
  selected?: string[];
};

export type SkillsAskResponse = {
  answer: string;
  used_skills: string[];
  model: string;
  tokens_estimate: number;
};

export type AskGrokRequest = {
  session_id: string;
  q: string;
  lang?: "ru" | "en";
  selected?: string[];
};

export type AskGrokResponse = {
  answer: string;
  used_skills: string[];
  model: string;
  tokens_estimate: number;
  from_fatcontext?: boolean;
};

export async function askSkills(payload: SkillsAskRequest, signal?: AbortSignal): Promise<SkillsAskResponse> {
  const r = await apiFetch("/skills/ask", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    const snippet = text.length > 200 ? `${text.slice(0, 200)}…` : text;
    throw new ChatRequestError(r.status, `${getApiBaseUrl()}/skills/ask`, snippet.trim());
  }
  const data = await r.json();
  return {
    answer: typeof data?.answer === "string" ? data.answer : "",
    used_skills: ensureStringArray(data?.used_skills),
    model: typeof data?.model === "string" ? data.model : "unknown",
    tokens_estimate: typeof data?.tokens_estimate === "number" ? data.tokens_estimate : 0,
  };
}

export async function askGrok(payload: AskGrokRequest, signal?: AbortSignal): Promise<AskGrokResponse> {
  const r = await apiFetch("/chat/ask_grok", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    const snippet = text.length > 200 ? `${text.slice(0, 200)}…` : text;
    throw new ChatRequestError(r.status, `${getApiBaseUrl()}/chat/ask_grok`, snippet.trim());
  }
  const data = await r.json();
  return {
    answer: typeof data?.answer === "string" ? data.answer : "",
    used_skills: ensureStringArray(data?.used_skills),
    model: typeof data?.model === "string" ? data.model : "unknown",
    tokens_estimate: typeof data?.tokens_estimate === "number" ? data.tokens_estimate : 0,
    from_fatcontext: Boolean(data?.from_fatcontext),
  };
}

export async function getTasks(): Promise<TasksStatusResponse> {
  const r = await apiFetch("/tasks/status");
  return r.json();
}

export async function getCal(): Promise<CalLinkResponse> {
  const r = await apiFetch("/cal/link");
  return r.json();
}

export async function getChatConfig(signal?: AbortSignal): Promise<ChatConfig> {
  const r = await apiFetch(CONFIG_ENDPOINT, { signal });
  if (!r.ok) {
    throw new Error(`Failed to load chat config (status ${r.status})`);
  }
  const payload = await r.json();
  return {
    persona: typeof payload?.persona === "string" && payload.persona.trim().length > 0 ? payload.persona : "dima",
    llmAvailable: Boolean(payload?.llmAvailable),
    notion: Boolean(payload?.notion),
    csvFallback: Boolean(payload?.csvFallback),
    telegramExport: Boolean(payload?.telegramExport),
    model: typeof payload?.model === "string" && payload.model.trim().length > 0 ? payload.model : undefined,
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

const allowedRoles = new Set<ChatMessageDto["role"]>(["user", "assistant", "system"]);

const sanitizeMessages = (messages: ChatMessageDto[]): ChatMessageDto[] => {
  if (!Array.isArray(messages)) return [];
  return messages
    .map((message) => {
      if (!message || typeof message !== "object") return null;
      const role = allowedRoles.has(message.role) ? message.role : "user";
      const content = typeof message.content === "string" ? message.content.trim() : "";
      if (!content) return null;
      return { role, content };
    })
    .filter((message): message is ChatMessageDto => message !== null);
};

export async function postChat(payload: ChatAskPayload, signal?: AbortSignal): Promise<ChatAskResponse> {
  let r: Response;
  const sanitizedMessages = sanitizeMessages(payload.messages);
  const body = JSON.stringify({
    ...payload,
    messages: sanitizedMessages,
  });
  try {
    r = await apiFetch(ASK_ENDPOINT, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
      signal,
    });
  } catch (networkErr) {
    throw new ChatRequestError(
      0,
      `${getApiBaseUrl()}${ASK_ENDPOINT}`,
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
    throw new ChatRequestError(r.status, r.url || `${getApiBaseUrl()}${ASK_ENDPOINT}`, snippet.trim());
  }
  const data = await r.json();
  return {
    answer: typeof data?.answer === "string" ? data.answer : "",
    sources: ensureStringArray(data?.sources),
    used_llm: Boolean(data?.used_llm),
    persona: typeof data?.persona === "string" && data.persona.trim().length > 0 ? data.persona : undefined,
  };
}

export async function postChatExport(payload: ChatExportPayload): Promise<void> {
  const sanitizedMessages = sanitizeMessages(payload.messages);
  const r = await apiFetch(EXPORT_TELEGRAM_ENDPOINT, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      ...payload,
      messages: sanitizedMessages,
    }),
  });
  if (!r.ok) {
    const snippet = await r.text().catch(() => "");
    throw new ChatRequestError(
      r.status,
      r.url || `${getApiBaseUrl()}${EXPORT_TELEGRAM_ENDPOINT}`,
      snippet.slice(0, 200),
    );
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
    await apiFetch(CLIENT_LOG_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      // Do not send credentials to avoid CORS complications
    });
  } catch {
    // best-effort only
  }
}


