import { useEffect, useMemo, useState } from "react";
import { getChatConfig, postChat, ChatRequestError } from "../api/client";
import type { ChatOut, ChatSource, ChatConfig } from "../types";
import type { Locale } from "../shared/i18n/resolveLocale";

type Msg = {
  id: string;
  role: "user" | "assistant";
  text: string;
  mode?: ChatOut["mode"];
  sources?: ChatSource[];
};

type ChatBoxProps = { lang: Locale };

export function ChatBox({ lang }: ChatBoxProps) {
  const initialAssistant = useMemo(
    () => (lang === "en" ? "Hi! I'm your assistant. How can I help?" : "Привет! Я ассистент. Чем помочь?"),
    [lang],
  );

  const [msgs, setMsgs] = useState<Msg[]>([
    { id: "m1", role: "assistant", text: initialAssistant },
  ]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [smartEnabled, setSmartEnabled] = useState(false);
  const [config, setConfig] = useState<ChatConfig | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    getChatConfig(controller.signal)
      .then((cfg) => {
        if (!active) return;
        setConfig(cfg);
        const allowed = cfg.rag_mode === "llm";
        setSmartEnabled(allowed && cfg.smart_default);
      })
      .catch(() => {
        if (!active) return;
        setConfig({ smart_default: false, rag_mode: "extractive", topk: 3 });
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  useEffect(() => {
    setMsgs((existing) => {
      if (existing.length === 0) return [{ id: "m1", role: "assistant", text: initialAssistant }];
      const [first, ...rest] = existing;
      if (first.role === "assistant" && first.sources === undefined && rest.length === 0) {
        return [{ ...first, text: initialAssistant }];
      }
      return existing;
    });
  }, [initialAssistant]);

  const send = async () => {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    setError(null);
    const userMsg: Msg = { id: String(Date.now()), role: "user", text: trimmed };
    setMsgs((m) => [...m, userMsg]);
    setText("");
    setSending(true);
    const wantsLLM = smartEnabled && config?.rag_mode === "llm";
    try {
      const reply = await postChat({ text: trimmed, lang, llm: wantsLLM });
      const assistantMsg: Msg = {
        id: `${userMsg.id}-r`,
        role: "assistant",
        text: reply.reply || (lang === "en" ? "No answer yet." : "Ответ пока недоступен."),
        mode: reply.mode,
        sources: reply.sources,
      };
      setMsgs((m) => [...m, assistantMsg]);
    } catch (err) {
      const fallback =
        lang === "en"
          ? "Sorry, something went wrong. Try again later."
          : "Извините, не получилось. Попробуйте ещё раз.";
      let message = fallback;
      if (err instanceof ChatRequestError && import.meta.env.DEV) {
        const statusPart = err.status ? `status ${err.status}` : "network error";
        const urlPart = err.url ? `url ${err.url}` : "";
        const bodyPart = err.responseSnippet ? `body ${err.responseSnippet}` : "";
        const detail = [statusPart, urlPart, bodyPart].filter(Boolean).join(" | ");
        message = `${fallback} — dev: ${detail}`.trim();
      }
      setError(message);
      setMsgs((m) => [...m, { id: `${userMsg.id}-err`, role: "assistant", text: fallback }]);
    } finally {
      setSending(false);
    }
  };

  const smartToggleDisabled = !config || config.rag_mode !== "llm";

  useEffect(() => {
    if (smartToggleDisabled && smartEnabled) {
      setSmartEnabled(false);
    }
  }, [smartToggleDisabled, smartEnabled]);

  return (
    <div className="grid gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{lang === "en" ? "Smart answer (LLM)" : "Умный ответ (LLM)"}</span>
        <label className="inline-flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={smartEnabled && !smartToggleDisabled}
            onChange={(e) => setSmartEnabled(e.target.checked)}
            disabled={smartToggleDisabled}
          />
          <span>{smartToggleDisabled ? (lang === "en" ? "Unavailable" : "Недоступно") : (smartEnabled ? (lang === "en" ? "On" : "Вкл") : (lang === "en" ? "Off" : "Выкл"))}</span>
        </label>
      </div>

      <div className="grid gap-2 max-h-64 overflow-auto pr-1">
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
              {m.role === "assistant" && m.sources && m.sources.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {m.sources.map((source) => {
                    const pct = Math.round(Math.max(0, Math.min(1, source.score ?? 0)) * 100);
                    return (
                      <span
                        key={source.id}
                        className="rounded-full border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600"
                      >
                        {source.title} · {pct}%
                      </span>
                    );
                  })}
                </div>
              )}
              {m.role === "assistant" && m.mode && (
                <span className="text-xs uppercase tracking-wide text-gray-400">
                  {m.mode === "llm"
                    ? lang === "en"
                      ? "Mode: LLM"
                      : "Режим: LLM"
                    : lang === "en"
                      ? "Mode: Extractive"
                      : "Режим: Выборка"}
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
        <button className="h-10 rounded bg-black px-4 text-white disabled:opacity-60" onClick={send} disabled={sending}>
          {lang === "en" ? "Send" : "Отправить"}
        </button>
      </div>
      {error && <div className="text-xs text-red-500">{error}</div>}
    </div>
  );
}

