# Unified Diff - Chat UI Implementation

This document contains all changes made to implement the minimal chat UI feature.

## Modified Files

### 1. apps/website/astro.config.mjs

```diff
--- a/apps/website/astro.config.mjs
+++ b/apps/website/astro.config.mjs
@@ -1,4 +1,5 @@
 import { defineConfig } from 'astro/config';
+import react from '@astrojs/react';
 import path from 'path';
 import { fileURLToPath } from 'url';
 
@@ -7,6 +8,7 @@ const __dirname = path.dirname(fileURLToPath(import.meta.url));
 export default defineConfig({
   base: '/miniapp/',
   output: 'static',
+  integrations: [react()],
   server: {
     host: '127.0.0.1',
     port: 5173,
```

### 2. apps/website/package.json

```diff
--- a/apps/website/package.json
+++ b/apps/website/package.json
@@ -15,11 +15,16 @@
   "dependencies": {
     "@ai-avatar/clients": "workspace:*",
     "@ai-avatar/shared": "workspace:*",
-    "astro": "5.0.5"
+    "@astrojs/react": "3.6.2",
+    "astro": "5.0.5",
+    "react": "18.3.1",
+    "react-dom": "18.3.1"
   },
   "devDependencies": {
     "@astrojs/check": "0.9.4",
+    "@types/react": "18.3.3",
+    "@types/react-dom": "18.3.0",
     "typescript": "5.6.3"
   }
 }
```

### 3. apps/api/src/app/main.py

```diff
--- a/apps/api/src/app/main.py
+++ b/apps/api/src/app/main.py
@@ -7,7 +7,7 @@ from fastapi.staticfiles import StaticFiles
 from app.core.settings import settings
 from app.core.logging import setup_logging, get_logger
 from app.db.connection import init_db, close_db
-from app.adapters.web import health, chat, chat_ws, voice, telegram
+from app.adapters.web import health, chat, chat_ws, voice, telegram, chat_stub
 
 setup_logging()
 logger = get_logger(__name__)
@@ -38,7 +38,14 @@ app = FastAPI(
 )
 
 # CORS middleware
+cors_origins = [settings.website_origin, "https://web.telegram.org"]
+
+# Optional: Allow dev CORS (set ALLOW_DEV_CORS=1 for local development)
+import os
+if os.getenv("ALLOW_DEV_CORS") == "1":
+    cors_origins.append("*")
+    logger.warning("Dev CORS enabled - allowing all origins")
+
 app.add_middleware(
     CORSMiddleware,
-    allow_origins=[settings.website_origin, "https://web.telegram.org"],
+    allow_origins=cors_origins,
     allow_credentials=True,
@@ -56,6 +63,7 @@ app.include_router(chat.router, tags=["chat"])
 app.include_router(chat_ws.router, tags=["chat"])
 app.include_router(voice.router, tags=["voice"])
 app.include_router(telegram.router, tags=["telegram"])
+app.include_router(chat_stub.router, tags=["chat-stub"])
 
 
 if __name__ == "__main__":
```

## New Files Created

### 4. apps/website/src/components/ChatWidget.tsx

```typescript
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
          text:
            "Local fallback: I couldn't reach the API. Here's an echo of your message: "" +
            text +
            "".",
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
```

### 5. apps/website/src/pages/miniapp/chat.astro

```astro
---
import ChatWidget from "../../components/ChatWidget";
---

<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <meta name="theme-color" content="#ffffff" />
    <title>MiniApp Chat</title>
    <style is:global>
      * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
      }

      html,
      body {
        height: 100%;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu,
          Cantarell, 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
      }

      body {
        background: #ffffff;
        color: #1f2937;
        overflow: hidden;
      }
    </style>
  </head>
  <body>
    <ChatWidget client:load />
  </body>
</html>
```

### 6. apps/api/src/app/adapters/web/chat_stub.py

```python
"""Chat stub router - simple rule-based responses without DB."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Literal, Optional
import random

router = APIRouter()

Role = Literal["user", "assistant"]


class HistoryItem(BaseModel):
    role: Role
    text: str


class ChatStubRequest(BaseModel):
    message: str
    history: Optional[List[HistoryItem]] = None


class ChatStubResponse(BaseModel):
    reply: str


GREETINGS = ["hi", "hello", "hey", "привет", "здрав", "yo", "sup", "hola"]
HELP = ["help", "how", "помоги", "как", "что умеешь", "what can you do"]


def rule_based_reply(message: str, history: List[HistoryItem] | None) -> str:
    """Generate a rule-based reply without using any external services."""
    m = message.strip().lower()
    
    if any(g in m for g in GREETINGS):
        return random.choice(
            [
                "Hello! I'm a stub assistant. Ask me something.",
                "Hi there! I can echo and give simple hints.",
                "Привет! Я заглушка-бот — расскажи, что нужно.",
                "Hey! This is a simple demo. How can I help?",
            ]
        )
    
    if any(h in m for h in HELP):
        return (
            "I'm a simple demo assistant. I can greet you and echo your messages. "
            "Try asking a short question — I'll reflect it back with a friendly note."
        )
    
    return f"You said: "{message}". If this were wired to a model, I'd answer helpfully."


@router.post("/api/chat/stub", response_model=ChatStubResponse)
def chat_stub(req: ChatStubRequest) -> ChatStubResponse:
    """Handle chat stub requests with rule-based responses."""
    reply = rule_based_reply(req.message, req.history)
    return ChatStubResponse(reply=reply)
```

---

## Summary

**Total files modified**: 3  
**Total files created**: 3  
**Lines added**: ~330  
**Lines removed**: ~5  

**Key changes**:
- Added React support to Astro frontend
- Created mobile-responsive chat UI component
- Added stub chat endpoint to FastAPI backend
- Implemented safe-area handling for mobile devices
- Added optional dev CORS configuration
- No database dependencies
- No breaking changes to existing code

