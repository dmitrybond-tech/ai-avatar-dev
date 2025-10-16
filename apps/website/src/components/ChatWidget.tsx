import React, { useEffect, useRef, useState } from "react";

type Role = "user" | "assistant";
type Msg = { id: string; role: Role; text: string; ts: number };

const API_PATH =
  (import.meta as any).env?.PUBLIC_API_BASE_URL
    ? `${(import.meta as any).env.PUBLIC_API_BASE_URL}/api/chat/stub`
    : "/api/chat/stub";

export default function ChatWidget() {
  const [messages, setMessages] = useState<Msg[]>(() => [
    {
      id: crypto.randomUUID(),
      role: "assistant",
      text: "Hi! This is a simple demo chat. Ask me anything 👋",
      ts: Date.now(),
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const listRef = useRef<HTMLDivElement | null>(null);
  const taRef = useRef<HTMLTextAreaElement | null>(null);

  const scrollToBottom = () => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages.length]);

  const adjustTA = () => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(140, ta.scrollHeight) + "px";
  };
  
  useEffect(adjustTA, [input]);

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  };

  const send = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setSending(true);
    setInput("");
    const userMsg: Msg = { id: crypto.randomUUID(), role: "user", text, ts: Date.now() };
    setMessages((m) => [...m, userMsg]);
    try {
      const body = {
        message: text,
        history: messages.slice(-10).map((m) => ({ role: m.role, text: m.text })),
      };
      const res = await fetch(API_PATH, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const replyText: string = data?.reply ?? "I have nothing to add yet.";
      setMessages((m) => [
        ...m,
        { id: crypto.randomUUID(), role: "assistant", text: replyText, ts: Date.now() },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: `Local fallback: I couldn't reach the API. Here's an echo of your message: "${text}".`,
          ts: Date.now(),
        },
      ]);
    } finally {
      setSending(false);
      setTimeout(scrollToBottom, 50);
      taRef.current?.focus();
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100dvh",
        maxHeight: "100dvh",
        width: "100%",
        paddingBottom: "env(safe-area-inset-bottom)",
        WebkitTapHighlightColor: "transparent",
      }}
    >
      <div
        ref={listRef}
        role="log"
        aria-live="polite"
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "1rem",
          display: "flex",
          flexDirection: "column",
          gap: "0.75rem",
          background: "#f5f5f5",
          WebkitOverflowScrolling: "touch",
        }}
      >
        {messages.map((m) => (
          <div
            key={m.id}
            style={{
              maxWidth: "85%",
              borderRadius: "1rem",
              padding: "0.75rem 1rem",
              wordWrap: "break-word",
              ...(m.role === "user"
                ? {
                    marginLeft: "auto",
                    background: "#3b82f6",
                    color: "white",
                  }
                : {
                    marginRight: "auto",
                    background: "white",
                    color: "#333",
                    boxShadow: "0 2px 8px rgba(0, 0, 0, 0.08)",
                  }),
            }}
          >
            {m.text}
          </div>
        ))}
        {sending && (
          <div style={{ marginRight: "auto", fontSize: "0.875rem", opacity: 0.7 }}>
            Thinking…
          </div>
        )}
      </div>
      <div
        style={{
          position: "sticky",
          bottom: 0,
          width: "100%",
          borderTop: "1px solid #e5e7eb",
          background: "rgba(255, 255, 255, 0.95)",
          backdropFilter: "blur(8px)",
          paddingBottom: "env(safe-area-inset-bottom)",
        }}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
          style={{
            maxWidth: "640px",
            width: "100%",
            margin: "0 auto",
            display: "flex",
            alignItems: "flex-end",
            gap: "0.5rem",
            padding: "1rem",
          }}
        >
          <textarea
            ref={taRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Type a message"
            rows={1}
            aria-label="Message"
            disabled={sending}
            style={{
              flex: 1,
              resize: "none",
              borderRadius: "1rem",
              border: "2px solid #e5e7eb",
              padding: "0.75rem 1rem",
              outline: "none",
              fontSize: "1rem",
              fontFamily: "inherit",
              maxHeight: "140px",
              transition: "border-color 0.2s",
              touchAction: "manipulation",
            }}
            onFocus={(e) => {
              e.target.style.borderColor = "#3b82f6";
            }}
            onBlur={(e) => {
              e.target.style.borderColor = "#e5e7eb";
            }}
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            style={{
              padding: "0.75rem 1.5rem",
              background: sending || !input.trim() ? "#9ca3af" : "#3b82f6",
              color: "white",
              border: "none",
              borderRadius: "1rem",
              fontSize: "1rem",
              fontWeight: "500",
              cursor: sending || !input.trim() ? "not-allowed" : "pointer",
              transition: "transform 0.2s, background 0.2s",
              touchAction: "manipulation",
              userSelect: "none",
            }}
            onMouseDown={(e) => {
              if (!sending && input.trim()) {
                (e.target as HTMLElement).style.transform = "scale(0.98)";
              }
            }}
            onMouseUp={(e) => {
              (e.target as HTMLElement).style.transform = "scale(1)";
            }}
            onMouseLeave={(e) => {
              (e.target as HTMLElement).style.transform = "scale(1)";
            }}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

