# Unified Diffs - Miniapp Init & Logging + Brief Modal Fix

## 1. apps/miniapp-web/src/lib/telegram.ts (NEW)

```diff
+export function safeInitTelegram() {
+  const tg = (window as any).Telegram?.WebApp;
+  const inTg = !!tg;
+  try {
+    if (inTg && tg.ready) {
+      tg.ready();
+    }
+  } catch {
+    // Silently ignore initialization errors
+  }
+  return { tg, inTg };
+}
```

## 2. apps/miniapp-web/src/lib/clientLog.ts (NEW)

```diff
+import { apiUrl } from "./apiBase";
+
+export async function clientLog(
+  level: "info" | "warn" | "error",
+  message: string,
+  extra: any = {}
+) {
+  try {
+    await fetch(apiUrl("/client-log"), {
+      method: "POST",
+      headers: { "content-type": "application/json" },
+      body: JSON.stringify({
+        level,
+        message,
+        extra,
+        ua: navigator.userAgent,
+      }),
+    });
+  } catch {
+    // Best-effort logging, fail silently
+  }
+}
```

## 3. apps/miniapp-web/src/main.tsx

```diff
 import React from 'react'
 import ReactDOM from 'react-dom/client'
 import './styles.css'
 import { App } from './App'
-import { getTelegramWebApp, isTelegramWebView } from './lib/tg'
-import { postClientLog } from './api/client'
+import { safeInitTelegram } from './lib/telegram'
+import { clientLog } from './lib/clientLog'
 
 const rootEl = document.getElementById('root')!
 
-function showSafeMode(message: string) {
-  try {
-    rootEl.innerHTML = ''
-    const container = document.createElement('div')
-    container.textContent = 'Miniapp failed to initialize inside Telegram. Retrying…'
-    rootEl.appendChild(container)
-  } catch {/* ignore */}
-  try {
-    if (isTelegramWebView()) {
-      postClientLog({
-        ua: typeof navigator !== 'undefined' ? navigator.userAgent : '',
-        location: typeof window !== 'undefined' ? String(window.location) : '',
-        message,
-        stack: undefined,
-      }).catch(()=>{})
-    }
-  } catch {/* ignore */}
-}
+// Initialize Telegram gracefully
+const { tg, inTg } = safeInitTelegram()
+clientLog("info", "miniapp_init", { inTg })
 
 window.addEventListener('error', (e) => {
   console.error('Global error:', e.error || e.message)
-  showSafeMode(e?.error?.message || e.message || 'error')
+  clientLog("error", e?.error?.message || e.message || 'error', {
+    stack: e?.error?.stack,
+  })
 })
 
 window.addEventListener('unhandledrejection', (e: PromiseRejectionEvent) => {
   const msg = (e.reason && (e.reason.message || String(e.reason))) || 'unhandledrejection'
   const stack = e.reason && e.reason.stack ? String(e.reason.stack) : undefined
   console.error('Unhandled rejection:', e.reason)
-  try {
-    if (isTelegramWebView()) {
-      postClientLog({
-        ua: typeof navigator !== 'undefined' ? navigator.userAgent : '',
-        location: typeof window !== 'undefined' ? String(window.location) : '',
-        message: msg,
-        stack,
-      }).catch(()=>{})
-    }
-  } catch {/* ignore */}
-  showSafeMode(msg)
+  clientLog("error", msg, { stack })
 })
 
-try {
-  // Guarded Telegram initialization
-  getTelegramWebApp()
-} catch (e) {
-  console.warn('TG init failed', e)
-}
-
 ReactDOM.createRoot(rootEl).render(
   <React.StrictMode>
     <App />
   </React.StrictMode>,
 )
```

## 4. apps/miniapp-web/src/components/BriefUploadModal.tsx

```diff
 export function BriefUploadModal({ open, onClose }: { open: boolean; onClose: () => void }) {
   const fileRef = useRef<HTMLInputElement>(null);
   const [busy, setBusy] = useState(false);
-  const [form, setForm] = useState({ name: "", company: "", phone: "", email: "" });
+  const [form, setForm] = useState({ name: "", company: "", phone: "", email: "", message: "" });
   const [file, setFile] = useState<File | null>(null);
 
   // ... existing code ...
 
   const submit = async () => {
     if (!isReady || !file) return;
     setBusy(true);
     try {
       const fd = new FormData();
       fd.append("file", file);
       fd.append("locale", i18n.get());
       fd.append("name", form.name.trim());
       fd.append("company", form.company.trim());
       fd.append("phone", phoneSanitized);
       fd.append("email", form.email.trim());
+      if (form.message?.trim()) {
+        fd.append("message", form.message.trim());
+      }
       const res = await fetch(apiUrl("/briefs/upload"), {
         // ... existing code ...
       });
     } catch (e) {
       // ... existing code ...
     }
   };
 
   return (
     // ... existing JSX ...
           <label className="block">
             <span className="form-label block mb-1">{i18n.get()==="ru" ? "Комментарий (необязательно)" : "Comment (optional)"}</span>
+            <textarea
+              className="w-full rounded-md border px-3 py-2 bg-white dark:bg-zinc-800 dark:border-zinc-700 dark:text-white placeholder-white/70"
+              rows={3}
+              value={form.message}
+              onChange={(e) => setForm({ ...form, message: e.target.value })}
+              placeholder={i18n.get()==="ru" ? "Коротко о задаче..." : "Short description..."}
+            />
+          </label>
+
+          <label className="block">
             <span className="form-label block mb-1">{i18n.get()==="ru" ? "Файл" : "File"}</span>
             // ... existing file input ...
           </label>
     // ... existing JSX ...
   );
 }
```

## 5. apps/api/src/app/adapters/web/client_log.py

```diff
 """Client log/telemetry endpoint (minimal, optional)."""
-from fastapi import APIRouter, Request, Response
-from pydantic import BaseModel
-from typing import Optional
+from fastapi import APIRouter, Request, Response, Body
+from fastapi.responses import JSONResponse
+from typing import Optional, Dict, Any
 from app.core.logging import get_logger
 
 logger = get_logger(__name__)
 router = APIRouter()
 
 
-class ClientLog(BaseModel):
-    ua: str
-    location: str
-    message: str
-    stack: Optional[str] = None
-
-
-@router.post("/api/client-log", status_code=204)
-async def client_log(payload: ClientLog, request: Request) -> Response:
-    """Accept minimal client-side error logs and write to server logs.
-
-    Always returns 204 to avoid leaking details to the client.
-    """
+@router.post("/client-log")
+async def client_log(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
+    """Accept minimal client-side logs and write to server logs.
+    
+    Accepts JSON with: level (info/warn/error), message, extra (dict), ua (string).
+    Returns {ok: true} on success.
+    """
     try:
-        logger.warning(
-            "client-log: %s | %s | %s | %s",
-            payload.ua,
-            payload.location,
-            payload.message,
-            (payload.stack or ""),
-        )
+        level = payload.get("level", "info").lower()
+        msg = payload.get("message", "")
+        extra = {k: v for k, v in payload.items() if k not in ("level", "message")}
+        
+        # Use appropriate log level
+        log_level = level if level in ("info", "warning", "error") else "info"
+        getattr(logger, log_level)(f"client-log: {msg} | {extra}")
     except Exception as e:  # pragma: no cover - best effort logging
         logger.error("client-log failed: %s", e)
-    return Response(status_code=204)
+    return JSONResponse({"ok": True})
+
+
+@router.post("/api/client-log")
+async def client_log_alias(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
+    """Backward-compat alias for /client-log."""
+    return await client_log(payload)
```

## 6. apps/api/src/app/adapters/web/briefs.py

```diff
 """Brief upload router."""
 import os
 import time
 import pathlib
 import re
+import html
 from fastapi import APIRouter, UploadFile, File, Form, HTTPException
 from fastapi.responses import JSONResponse
 import httpx
 from app.core.logging import get_logger
 
 // ... existing code ...
 
 @router.post("/upload")
 async def upload_brief(
     file: UploadFile = File(...),
     locale: str = Form(None),
     name: str = Form(...),
     company: str = Form(...),
     phone: str = Form(...),
     email: str = Form(...),
+    message: str | None = Form(None),
 ):
     """Upload a brief file, save it, and forward digest + file to Telegram admin."""
     // ... existing validation code ...
 
     # Forward digest and document to Telegram admin
     telegram_sent = False
     if BOT_TOKEN and ADMIN_CHAT:
         try:
             async with httpx.AsyncClient(timeout=60.0) as client:
                 # 1) Send digest message
+                message_text = ""
+                if message and message.strip():
+                    # HTML escape the message for safety
+                    message_escaped = html.escape(message.strip())
+                    message_text = f"<b>Comment:</b> {message_escaped}\n"
                 text = (
                     f"<b>New brief</b> ({(locale or 'en').upper()})\n"
                     f"<b>Name:</b> {name}\n"
                     f"<b>Company:</b> {company}\n"
                     f"<b>Phone:</b> {phone}\n"
                     f"<b>Email:</b> {email}\n"
+                    + message_text
                     + f"<b>File:</b> {safe} ({round(size/1024/1024, 2)} MB)"
                 )
                 // ... existing Telegram send code ...
```

