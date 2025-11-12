# Unified Diffs: Telegram Export Flow Fixes

## 1. Frontend: Chat Component (`apps/miniapp-web/src/components/Chat.tsx`)

```diff
--- a/apps/miniapp-web/src/components/Chat.tsx
+++ b/apps/miniapp-web/src/components/Chat.tsx
@@ -316,6 +316,10 @@ export function ChatBox({ lang }: ChatBoxProps) {
         );
         return;
       }
+      // Generate conv_id: miniapp-<ISO_DATETIME>-<6rand>
+      const now = new Date().toISOString().replace(/[:.]/g, "");
+      const rand = Math.random().toString(36).slice(2, 8);
+      const convId = `miniapp-${now}-${rand}`;
       const exportPayload: ChatExportPayload = {
+        conv_id: convId,
+        lang,
         messages: conversation,
         meta: {
           session_id: sessionId,
```

## 2. Frontend: Types (`apps/miniapp-web/src/types.ts`)

```diff
--- a/apps/miniapp-web/src/types.ts
+++ b/apps/miniapp-web/src/types.ts
@@ -56,6 +56,8 @@ export type ChatAskResponse = {
 
 export type ChatExportPayload = {
+  conv_id?: string;
+  lang?: "ru" | "en";
   messages: ChatMessageDto[];
   meta?: {
     title?: string | null;
```

## 3. Backend: Chat Model (`apps/miniapp-api/app/models/chat.py`)

```diff
--- a/apps/miniapp-api/app/models/chat.py
+++ b/apps/miniapp-api/app/models/chat.py
@@ -37,6 +37,8 @@ class AskResponse(BaseModel):
 
 
 class ExportRequest(BaseModel):
+    conv_id: Optional[str] = None
+    lang: Optional[Literal["en", "ru"]] = None
     messages: List[ChatMessage] = Field(default_factory=list)
     items: Optional[List[ChatMessage]] = Field(default=None)
     title: Optional[str] = None
```

## 4. Backend: Chat Router (`apps/miniapp-api/routers/chat_v2.py`)

```diff
--- a/apps/miniapp-api/routers/chat_v2.py
+++ b/apps/miniapp-api/routers/chat_v2.py
@@ -166,6 +166,20 @@ async def export_telegram(
     if not body.messages and body.items:
         body.messages = body.items  # type: ignore[assignment]
     payload_messages = body.messages or []
 
+    # Extract lang from top-level or meta, default to "ru"
+    lang = body.lang
+    if not lang and body.meta:
+        lang = body.meta.get("lang", "ru")
+    if not lang:
+        lang = "ru"
+
+    # Use conv_id as title if provided, otherwise use title or generate from session_id
+    title = body.title or body.conv_id
+    if not title and body.meta and body.meta.get("session_id"):
+        title = f"chat-{body.meta['session_id']}"
+
     meta = body.meta or {}
     meta.update(
         {
             "ip": request.client.host if request.client else None,
             "user_agent": request.headers.get("user-agent"),
+            "conv_id": body.conv_id,
+            "lang": lang,
         }
     )
     try:
         result = await exporter.send(
             [ChatMessage(role=msg.role, content=msg.content) for msg in payload_messages],
             meta=meta,
-            title=body.title,
+            title=title,
             dry_run=dry_run,
         )
```

## 5. Compose Environment (No Changes Needed)

The compose file (`infra/compose/miniapp.compose.yaml`) already has the correct environment variables:

```yaml
environment:
  TELEGRAM_TOKEN: ${TELEGRAM_TOKEN:-}
  TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:-${TELEGRAM_TOKEN:-}}
  ADMIN_CHAT_ID: ${ADMIN_CHAT_ID:-}
  TELEGRAM_ADMIN_CHAT_ID: ${TELEGRAM_ADMIN_CHAT_ID:-${ADMIN_CHAT_ID:-}}
```

No changes required - fallbacks are already configured correctly.

