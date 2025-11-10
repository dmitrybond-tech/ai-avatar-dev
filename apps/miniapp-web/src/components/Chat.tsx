import { useEffect, useMemo, useRef, useState } from "react";
import { ChatRequestError, getChatConfig, postChat, postChatExport } from "../api/client";
import type { ChatConfig, ChatOut } from "../types";
import type { Locale } from "../shared/i18n/resolveLocale";
import { useChatSessionId } from "../hooks/useChatSessionId";
import { getTelegramWebApp, isTelegramWebView } from "../lib/tg";
import { CHAT_EXPORT_URL } from "../lib/apiBase";

type Msg = {
  id: string;
  role: "user" | "assistant";
  text: string;
  mode?: ChatOut["mode"];
};

type ChatBoxProps = { lang: Locale };

const INTRO_RU = "Привет! Я ассистент Димы. Подскажу по его компетенциям и текущим проектам.";
const INTRO_EN = "Hi! I’m Dima’s assistant. I can share what he is working on and how he can help.";
const HISTORY_PREFIX = "chat_history:";

const fallbackConfig: ChatConfig = {
  persona: "dima",
  smart_chat: false,
  rag_mode: "extractive",
  provider: "openai",
  model: "",
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
      const mode = item.mode === "llm" ? "llm" : item.mode === "stub" ? "stub" : undefined;
      if (!role || !text) continue;
      cleaned.push({ id, role, text, mode });
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
  const [persona, setPersona] = useState<string>(fallbackConfig.persona);
  const introText = useMemo(() => {
    if (lang === "en") {
      return persona === "dima"
        ? INTRO_EN
        : `Hi! I’m ${persona}'s assistant. I can share what they are working on.`;
    }
    return persona === "dima"
      ? INTRO_RU
      : `Привет! Я ассистент ${persona}. Расскажу о его проектах и компетенциях.`;
  }, [lang, persona]);

  const [msgs, setMsgs] = useState<Msg[]>(() => loadHistory(sessionKey, introText));
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [smartEnabled, setSmartEnabled] = useState(false);
  const [config, setConfig] = useState<ChatConfig>(fallbackConfig);
  const [error, setError] = useState<string | null>(null);
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
        const enableSmart = cfg.smart_chat && cfg.rag_mode === "llm";
        setSmartEnabled(enableSmart);
      })
      .catch(() => {
        if (!active) return;
        setConfig(fallbackConfig);
        setSmartEnabled(false);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, []);

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
    const smartAvailable = config.smart_chat && config.rag_mode === "llm";
    if (!smartAvailable && smartEnabled) {
      setSmartEnabled(false);
    }
  }, [config, smartEnabled]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const handler = () => {
      if (exportedRef.current || !hasUserMessages) return;
      if (typeof navigator.sendBeacon !== "function") return;
      const payload: { session_id: string; tg_init_data?: string | null } = { session_id };
      if (tgInitData) payload.tg_init_data = tgInitData;
      try {
        const blob = new Blob([JSON.stringify(payload)], { type: "application/json" });
        navigator.sendBeacon(CHAT_EXPORT_URL, blob);
        exportedRef.current = true;
      } catch {
        // ignore sendBeacon failures
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [sessionId, tgInitData, hasUserMessages]);

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

    const providerReady = config.smart_chat && config.rag_mode === "llm";
    const payload = {
      text: trimmed,
      lang,
      llm: smartEnabled && providerReady,
      session_id: sessionId,
      tg_init_data: tgInitData ?? undefined,
    } as const;

    try {
      const reply = await postChat(payload);
      if (reply.session_id && reply.session_id !== sessionId && typeof window !== "undefined") {
        try {
          window.sessionStorage.setItem("chat_session_id", reply.session_id);
        } catch {
          // ignore storage errors
        }
      }
      if (reply.persona) {
        setPersona(reply.persona);
      }
      const assistantMsg: Msg = {
        id: `${messageId}-assistant`,
        role: "assistant",
        text: reply.reply || (lang === "en" ? "No answer yet." : "Ответ пока недоступен."),
        mode: reply.mode,
      };
      setMsgs((previous) => [...previous, assistantMsg]);
    } catch (err) {
      const fallback = lang === "en"
        ? "Sorry, something went wrong. Try again later."
        : "Извините, отправка не удалась. Попробуйте ещё раз.";
      let message = fallback;
      if (err instanceof ChatRequestError && import.meta.env.DEV) {
        const statusPart = err.status ? `status ${err.status}` : "network error";
        const urlPart = err.url ? `url ${err.url}` : "";
        const bodyPart = err.responseSnippet ? `body ${err.responseSnippet}` : "";
        const detail = [statusPart, urlPart, bodyPart].filter(Boolean).join(" | ");
        message = `${fallback} — dev: ${detail}`.trim();
      }
      setError(message);
      setMsgs((previous) => [...previous, { id: `${messageId}-error`, role: "assistant", text: fallback }]);
    } finally {
      setSending(false);
    }
  };

  const finishAndSend = async () => {
    if (exporting || exportedRef.current) return;
    setExportMessage(null);
    setExporting(true);
    try {
      await postChatExport({ session_id: sessionId, tg_init_data: tgInitData ?? undefined });
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

  const smartAvailable = config.smart_chat && config.rag_mode === "llm";
  const smartToggleDisabled = !smartAvailable;

  return (
    <div className="grid gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">
          {lang === "en" ? "Smart answer (LLM)" : "Умный ответ (LLM)"}
        </span>
        <label className="inline-flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={smartEnabled && !smartToggleDisabled}
            onChange={(e) => setSmartEnabled(e.target.checked)}
            disabled={smartToggleDisabled}
          />
          <span>
            {smartToggleDisabled
              ? lang === "en"
                ? "Unavailable"
                : "Недоступно"
              : smartEnabled
                ? lang === "en"
                  ? "On"
                  : "Вкл"
                : lang === "en"
                  ? "Off"
                  : "Выкл"}
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
                  m.role === "user" ? "bg-black text-white" : "bg-gray-100 text-gray-900",
                ].join(" ")}
              >
                {m.text}
              </span>
              {m.role === "assistant" && m.mode && (
                <span className="text-xs uppercase tracking-wide text-gray-400">
                  {m.mode === "llm"
                    ? lang === "en"
                      ? "Mode: LLM"
                      : "Режим: LLM"
                    : lang === "en"
                      ? "Mode: Quick"
                      : "Режим: Быстрый"}
                </span>
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
            disabled={exporting || !hasUserMessages}
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
            {lang === "en"
              ? "I’ll send the whole chat to Dima in Telegram."
              : "Отправлю всю переписку Диме в Telegram."}
          </span>
        </div>
      )}

      {error && <div className="text-xs text-red-500">{error}</div>}
      {exportMessage && <div className="text-xs text-gray-600">{exportMessage}</div>}
    </div>
  );
}

