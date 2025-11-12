import { useEffect, useMemo, useRef, useState } from "react";
import { ChatRequestError, getChatConfig, postChat, postChatExport, EXPORT_TELEGRAM_ENDPOINT, askGrok, askSkills } from "../api/client";
import type { ChatAskPayload, ChatConfig, ChatExportPayload, ChatMessageDto } from "../types";
import type { Locale } from "../shared/i18n/resolveLocale";
import { useChatSessionId } from "../hooks/useChatSessionId";
import { useSmartLLM } from "../hooks/useSmartLLM";
import { useI18n } from "../lib/i18n";
import { getTelegramWebApp, isTelegramWebView } from "../lib/tg";
import { apiUrl } from "../shared/api";
import { streamReply } from "../lib/sse";

type Msg = {
  id: string;
  role: "user" | "assistant";
  text: string;
  usedLLM?: boolean;
  sources?: string[];
  isError?: boolean;
};

type ErrorState = { message: string; detail?: string; status?: number };

type ChatBoxProps = { lang: Locale };

const INTRO_RU = "Привет! Я ассистент Димы. Подскажу по его компетенциям и текущим проектам.";
const INTRO_EN = "Hi! I'm Dima's assistant. I can share what he is working on and how he can help.";
const HISTORY_PREFIX = "chat_history:";

const normalizeStringArray = (value: unknown): string[] => {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter((item) => item.length > 0);
};

const fallbackConfig: ChatConfig = {
  persona: "dima",
  llmAvailable: false,
  notion: false,
  csvFallback: true,
  telegramExport: false,
  model: undefined,
};

const initialHistory = (text: string): Msg[] => [{ id: "intro", role: "assistant", text }];

const loadHistory = (key: string, intro: string): Msg[] => {
  if (typeof window === "undefined") return initialHistory(intro);
  try {
    const raw = window.sessionStorage.getItem(key);
    if (!raw) return initialHistory(intro);
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return initialHistory(intro);
    const cleaned: Msg[] = [];
    for (const item of parsed) {
      if (!item || typeof item !== "object") continue;
      const role = item.role === "assistant" ? "assistant" : item.role === "user" ? "user" : null;
      const id = typeof item.id === "string" ? item.id : `${Date.now()}-${cleaned.length}`;
      const text = typeof item.text === "string" ? item.text : "";
      const usedLLM = item.usedLLM === true || item.mode === "llm";
      const sources = normalizeStringArray(item.sources);
      const isError = item.isError === true;
      if (!role || !text) continue;
      cleaned.push({ id, role, text, usedLLM, sources, isError });
    }
    return cleaned.length > 0 ? cleaned : initialHistory(intro);
  } catch {
    return initialHistory(intro);
  }
};

const serializeHistory = (key: string, msgs: Msg[]): void => {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(key, JSON.stringify(msgs));
  } catch {
    // ignore storage failures
  }
};

export function ChatBox({ lang }: ChatBoxProps) {
  const sessionId = useChatSessionId();
  const sessionKey = `${HISTORY_PREFIX}${sessionId}`;
  const { t } = useI18n();
  const [smartLLM, setSmartLLM] = useSmartLLM();
  const [persona, setPersona] = useState<string>(fallbackConfig.persona);
  const introText = useMemo(() => {
    if (lang === "en") {
      return persona === "dima"
        ? INTRO_EN
        : `Hi! I'm ${persona}'s assistant. I can share what they are working on.`;
    }
    return persona === "dima"
      ? INTRO_RU
      : `Привет! Я ассистент ${persona}. Расскажу о его проектах и компетенциях.`;
  }, [lang, persona]);

  const [msgs, setMsgs] = useState<Msg[]>(() => loadHistory(sessionKey, introText));
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [config, setConfig] = useState<ChatConfig>(fallbackConfig);
  const [error, setError] = useState<ErrorState | null>(null);
  const [exportMessage, setExportMessage] = useState<string | null>(null);
  const [tgInitData, setTgInitData] = useState<string | null>(null);
  const exportedRef = useRef(false);
  const [inTelegram] = useState<boolean>(() => isTelegramWebView());

  const hasUserMessages = useMemo(() => msgs.some((m) => m.role === "user"), [msgs]);

  useEffect(() => {
    setMsgs(loadHistory(sessionKey, introText));
  }, [sessionKey]);

  useEffect(() => {
    setMsgs((existing) => {
      if (existing.length === 0) return initialHistory(introText);
      const [first, ...rest] = existing;
      if (first.role === "assistant" && rest.length === 0) {
        return [{ ...first, text: introText }];
      }
      return existing;
    });
  }, [introText]);

  useEffect(() => {
    serializeHistory(sessionKey, msgs);
  }, [msgs, sessionKey]);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    getChatConfig(controller.signal)
      .then((cfg) => {
        if (!active) return;
        setConfig(cfg);
        setPersona(cfg.persona || "dima");
        // Don't override user's localStorage preference
        // Only disable if LLM is not available and user had it enabled
        if (!cfg.llmAvailable && smartLLM) {
          setSmartLLM(false);
        }
      })
      .catch(() => {
        if (!active) return;
        setConfig(fallbackConfig);
        if (smartLLM) {
          setSmartLLM(false);
        }
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [smartLLM, setSmartLLM]);

  useEffect(() => {
    const tg = getTelegramWebApp();
    if (!tg) return;
    const initData = typeof tg.initData === "string" ? tg.initData.trim() : "";
    if (initData) {
      setTgInitData(initData);
      return;
    }
    const unsafe = tg.initDataUnsafe;
    if (unsafe && typeof unsafe === "object") {
      try {
        const params = new URLSearchParams();
        for (const [key, value] of Object.entries(unsafe)) {
          if (value === undefined || value === null) continue;
          const serialized = typeof value === "string" ? value : JSON.stringify(value);
          params.append(key, serialized);
        }
        const fallbackInit = params.toString();
        if (fallbackInit) {
          setTgInitData(fallbackInit);
        }
      } catch {
        // ignore fallback serialization issues
      }
    }
  }, []);

  useEffect(() => {
    if (!config.llmAvailable && smartLLM) {
      setSmartLLM(false);
    }
  }, [config, smartLLM, setSmartLLM]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const handler = () => {
      if (exportedRef.current || !hasUserMessages) return;
      if (typeof navigator.sendBeacon !== "function") return;
      if (!config.telegramExport) return;
      const conversation: ChatMessageDto[] = msgs
        .filter((msg) => msg.role === "assistant" || msg.role === "user")
        .map((msg) => ({
          role: msg.role,
          content: msg.text,
        }));
      if (conversation.length === 0) return;
      const payload = {
        messages: conversation,
        meta: {
          session_id: sessionId,
          lang,
          persona,
          tg_init_data: tgInitData ?? undefined,
        },
      };
      try {
        const blob = new Blob([JSON.stringify(payload)], { type: "application/json" });
        navigator.sendBeacon(apiUrl(EXPORT_TELEGRAM_ENDPOINT), blob);
        exportedRef.current = true;
      } catch {
        // ignore sendBeacon failures
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [sessionId, tgInitData, hasUserMessages, msgs, lang, persona, config.telegramExport]);

  const send = async () => {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    setError(null);
    setExportMessage(null);
    exportedRef.current = false;

    const messageId = `${Date.now()}`;
    const userMsg: Msg = { id: messageId, role: "user", text: trimmed };
    setMsgs((previous) => [...previous, userMsg]);
    setText("");
    setSending(true);

    try {
      let assistantMsg: Msg;
      
      if (smartLLM && config.llmAvailable) {
        // Try /api/chat/ask_grok first, fallback to /api/skills/ask
        try {
          const grokReply = await askGrok({
            session_id: sessionId,
            q: trimmed,
            lang,
          });
          assistantMsg = {
            id: `${messageId}-assistant`,
            role: "assistant",
            text: grokReply.answer?.trim() || (lang === "en" ? "No answer yet." : "Ответ пока недоступен."),
            usedLLM: true,
            sources: grokReply.used_skills,
          };
        } catch (grokErr) {
          // Fallback to /api/skills/ask if ask_grok fails
          if (grokErr instanceof ChatRequestError && (grokErr.status === 401 || grokErr.status === 404 || grokErr.status === 502 || grokErr.status === 503)) {
            try {
              const skillsReply = await askSkills({
                q: trimmed,
                lang,
              });
              assistantMsg = {
                id: `${messageId}-assistant`,
                role: "assistant",
                text: skillsReply.answer?.trim() || (lang === "en" ? "No answer yet." : "Ответ пока недоступен."),
                usedLLM: true,
                sources: skillsReply.used_skills,
              };
            } catch (skillsErr) {
              throw skillsErr;
            }
          } else {
            throw grokErr;
          }
        }
      } else {
        // Use regular /api/ask flow
        const historyForRequest = [...msgs.filter((msg) => !msg.isError), userMsg];
        const requestMessages: ChatMessageDto[] = historyForRequest.map((msg) => ({
          role: msg.role,
          content: msg.text,
        }));

        const payload: ChatAskPayload = {
          messages: requestMessages,
          lang,
          top_k: 5,
          use_llm: false,
        };

        const reply = await postChat(payload);
        if (reply.persona) {
          setPersona(reply.persona);
        }
        assistantMsg = {
          id: `${messageId}-assistant`,
          role: "assistant",
          text: reply.answer?.trim().length
            ? reply.answer
            : lang === "en"
              ? "No answer yet."
              : "Ответ пока недоступен.",
          usedLLM: reply.used_llm,
          sources: reply.sources,
        };
      }
      
      setMsgs((previous) => [...previous, assistantMsg]);
    } catch (err) {
      const fallback = lang === "en"
        ? "Sorry, something went wrong. Try again later."
        : "Извините, отправка не удалась. Попробуйте ещё раз.";
      let message = fallback;
      let detail: string | undefined;
      let status: number | undefined;
      if (err instanceof ChatRequestError) {
        status = err.status || undefined;
        if (err.responseSnippet) {
          detail = err.responseSnippet;
        }
        
        // User-friendly error messages
        if (status === 401) {
          message = lang === "en" 
            ? "LLM service is not configured. Please contact support."
            : "Сервис LLM не настроен. Обратитесь в поддержку.";
        } else if (status === 502 || status === 503) {
          message = lang === "en"
            ? "LLM service is temporarily unavailable. Please try again later."
            : "Сервис LLM временно недоступен. Попробуйте позже.";
        } else if (status === 404) {
          message = lang === "en"
            ? "Session not found. Please refresh the page."
            : "Сессия не найдена. Обновите страницу.";
        }
        
        if (import.meta.env.DEV) {
          const parts = [
            status ? `status ${status}` : "network error",
            err.url ? `url ${err.url}` : "",
            detail ? `body ${detail}` : "",
          ].filter(Boolean);
          message = `${fallback} — dev: ${parts.join(" | ")}`.trim();
        } else if (status && status >= 400 && status < 600 && detail && !message.includes("LLM")) {
          message = `${fallback} (${status})`;
        }
      }
      setError({ message, detail, status });
      setMsgs((previous) => [
        ...previous,
        { id: `${messageId}-error`, role: "assistant", text: message, isError: true },
      ]);
    } finally {
      setSending(false);
    }
  };

  const finishAndSend = async () => {
    if (exporting || exportedRef.current) return;
    if (!config.telegramExport) {
      setExportMessage(
        lang === "en"
          ? "Telegram export is disabled."
          : "Отправка в Telegram отключена."
      );
      return;
    }
    setExportMessage(null);
    setExporting(true);
    try {
      const conversation = msgs
        .filter((msg) => (msg.role === "assistant" || msg.role === "user") && !msg.isError)
        .map((msg): ChatMessageDto => ({
          role: msg.role,
          content: msg.text,
        }));
      if (conversation.length === 0) {
        exportedRef.current = false;
        setExportMessage(
          lang === "en"
            ? "There is nothing to send yet."
            : "Отправлять пока нечего."
        );
        return;
      }
      // Generate conv_id: miniapp-<ISO_DATETIME>-<6rand>
      const now = new Date().toISOString().replace(/[:.]/g, "");
      const rand = Math.random().toString(36).slice(2, 8);
      const convId = `miniapp-${now}-${rand}`;
      const exportPayload: ChatExportPayload = {
        conv_id: convId,
        lang,
        messages: conversation,
        meta: {
          session_id: sessionId,
          lang,
          persona,
          tg_init_data: tgInitData ?? undefined,
        },
      };
      await postChatExport(exportPayload);
      exportedRef.current = true;
      setExportMessage(lang === "en" ? "Sent to Telegram." : "Отправила переписку в Telegram.");
    } catch (err) {
      exportedRef.current = false;
      const base = lang === "en" ? "Could not send transcript." : "Не получилось отправить переписку.";
      let message = base;
      if (err instanceof ChatRequestError && import.meta.env.DEV) {
        const detail = [err.status ? `status ${err.status}` : null, err.responseSnippet || null].filter(Boolean).join(" | ");
        message = `${base} — dev: ${detail}`.trim();
      }
      setExportMessage(message);
    } finally {
      setExporting(false);
    }
  };

  const smartToggleDisabled = !config.llmAvailable;

  return (
    <div className="grid gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">
          {t("chat.smartLLM")}
        </span>
        <label className="inline-flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={smartLLM && !smartToggleDisabled}
            onChange={(e) => setSmartLLM(e.target.checked)}
            disabled={smartToggleDisabled}
            aria-label={t("chat.smartLLM")}
          />
          <span>
            {smartToggleDisabled
              ? t("chat.smartLLMUnavailable")
              : smartLLM
                ? t("chat.smartLLMOn")
                : t("chat.smartLLMOff")}
          </span>
        </label>
      </div>

      <div className="grid max-h-64 gap-2 overflow-auto pr-1">
        {msgs.map((m) => (
          <div key={m.id} className={m.role === "user" ? "text-right" : "text-left"}>
            <div className="inline-flex max-w-full flex-col gap-1">
              <span
                className={[
                  "inline-block max-w-full whitespace-pre-line rounded px-3 py-2 text-left",
                  m.role === "user"
                    ? "bg-black text-white"
                    : m.isError
                      ? "border border-red-200 bg-red-50 text-red-700"
                      : "bg-gray-100 text-gray-900",
                ].join(" ")}
              >
                {m.text}
              </span>
              {m.role === "assistant" && (
                <div className="flex flex-col gap-1">
                  {m.usedLLM !== undefined && (
                    <span className="text-xs uppercase tracking-wide text-gray-400">
                      {m.usedLLM ? t("chat.modeLLM") : t("chat.modeSkills")}
                    </span>
                  )}
                  {m.sources && m.sources.length > 0 && (
                    <span className="text-xs text-gray-500">
                      {lang === "en" ? "Sources:" : "Источники:"} {m.sources.join(", ")}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <input
          className="flex-1 h-10 rounded border border-gray-300 px-3"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              send();
            }
          }}
          placeholder={lang === "en" ? "Type a message" : "Введите сообщение"}
        />
        <button
          className="h-10 rounded bg-black px-4 text-white disabled:opacity-60"
          onClick={send}
          disabled={sending}
        >
          {lang === "en" ? "Send" : "Отправить"}
        </button>
      </div>

      {(inTelegram || tgInitData) && (
        <div className="flex items-center gap-2">
          <button
            className="rounded border border-black px-3 py-2 text-sm font-medium disabled:opacity-60"
            onClick={finishAndSend}
            disabled={exporting || !hasUserMessages || !config.telegramExport}
          >
            {exporting
              ? lang === "en"
                ? "Sending…"
                : "Отправляю…"
              : lang === "en"
                ? "Finish & Send to Telegram"
                : "Завершить и отправить в Telegram"}
          </button>
          <span className="text-xs text-gray-500">
            {config.telegramExport
              ? lang === "en"
                ? "I'll send the whole chat to Dima in Telegram."
                : "Отправлю всю переписку Диме в Telegram."
              : lang === "en"
                ? "Telegram export is unavailable right now."
                : "Отправка в Telegram сейчас недоступна."}
          </span>
        </div>
      )}

      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          <div className="font-medium">
            {lang === "en" ? "The assistant could not reply" : "Ассистент не смог ответить"}
            {error.status ? ` (${error.status})` : ""}
          </div>
          <div>{error.message}</div>
          {error.detail && import.meta.env.DEV && (
            <div className="mt-1 whitespace-pre-wrap text-xs text-red-600 opacity-80">{error.detail}</div>
          )}
        </div>
      )}
      {exportMessage && <div className="text-xs text-gray-600">{exportMessage}</div>}
    </div>
  );
}

// --- NVP: Minimal chat component for /chat route ---
type Turn = { role: "user" | "assistant"; content: string };

export default function Chat() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [streaming, setStreaming] = useState(false);

  async function sendREST() {
    const message = text.trim();
    if (!message) return;
    setText("");
    setTurns((t) => [...t, { role: "user", content: message }]);
    const res = await fetch(apiUrl("/chat"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lang: "ru", history: turns, message }),
    });
    const data = await res.json();
    setTurns((t) => [...t, { role: "assistant", content: data.reply }]);
  }

  async function sendSSE() {
    const message = text.trim();
    if (!message || streaming) return;
    setText("");
    setStreaming(true);
    setTurns((t) => [...t, { role: "user", content: message }, { role: "assistant", content: "" }]);
    const idx = turns.length + 1;
    streamReply(message, (tok) => {
      setTurns((t) => {
        const copy = [...t];
        copy[idx] = { role: "assistant", content: (copy[idx]?.content ?? "") + tok };
        return copy;
      });
    }, () => setStreaming(false));
  }

  return (
    <div className="flex flex-col gap-3 max-w-[720px] mx-auto p-4">
      <div className="flex flex-col gap-2">
        {turns.map((m, i) => (
          <div key={i} className={m.role === "user" ? "self-end" : "self-start"}>
            <div className="rounded-2xl px-3 py-2 shadow" style={{ background: m.role === "user" ? "#eef" : "#eee" }}>
              {m.content}
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendREST()}
          className="flex-1 border rounded-xl px-3 py-2"
          placeholder="Напишите сообщение…"
        />
        <button onClick={sendREST} className="px-4 py-2 rounded-xl shadow">Send</button>
        <button onClick={sendSSE} disabled={streaming} className="px-4 py-2 rounded-xl shadow">{streaming ? "Streaming…" : "Stream"}</button>
      </div>
    </div>
  );
}
