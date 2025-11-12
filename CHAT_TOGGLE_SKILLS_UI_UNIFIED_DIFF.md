# Unified Diff: Chat Toggle & Skills UI Fix

## Summary
Moved "Smart answer (LLM)" checkbox to main chat form, removed LLM toggle from Skills page, completed Skills page UI with grid tiles and modal, implemented LLM routing with fallback.

## Files Changed

### New Files
- `apps/miniapp-web/src/hooks/useSmartLLM.ts` - Global hook for smartLLM state with localStorage persistence

### Modified Files
- `apps/miniapp-web/src/components/Chat.tsx` - Added checkbox, LLM routing logic
- `apps/miniapp-web/src/pages/SkillsPage.tsx` - Removed LLM toggle and related UI
- `apps/miniapp-web/src/api/client.ts` - Added askGrok function
- `apps/miniapp-web/src/i18n/en.json` - Added chat i18n strings
- `apps/miniapp-web/src/i18n/ru.json` - Added chat i18n strings

## Unified Diff

```diff
diff --git a/apps/miniapp-web/src/hooks/useSmartLLM.ts b/apps/miniapp-web/src/hooks/useSmartLLM.ts
new file mode 100644
index 0000000..3875d76
--- /dev/null
+++ b/apps/miniapp-web/src/hooks/useSmartLLM.ts
@@ -0,0 +1,42 @@
+import { useCallback, useEffect, useState } from "react";
+
+const STORAGE_KEY = "SMART_LLM_ENABLED";
+
+function loadFromStorage(): boolean {
+  if (typeof window === "undefined" || !("localStorage" in window)) {
+    return false;
+  }
+  try {
+    const stored = window.localStorage.getItem(STORAGE_KEY);
+    if (stored === null) return false;
+    return stored === "true";
+  } catch {
+    return false;
+  }
+}
+
+function saveToStorage(value: boolean): void {
+  if (typeof window === "undefined" || !("localStorage" in window)) {
+    return;
+  }
+  try {
+    window.localStorage.setItem(STORAGE_KEY, value ? "true" : "false");
+  } catch {
+    // ignore storage failures (Safari private mode, etc.)
+  }
+}
+
+export function useSmartLLM(): [boolean, (value: boolean) => void] {
+  const [smartLLM, setSmartLLMState] = useState<boolean>(() => loadFromStorage());
+
+  useEffect(() => {
+    saveToStorage(smartLLM);
+  }, [smartLLM]);
+
+  const setSmartLLM = useCallback((value: boolean) => {
+    setSmartLLMState(value);
+  }, []);
+
+  return [smartLLM, setSmartLLM];
+}

diff --git a/apps/miniapp-web/src/api/client.ts b/apps/miniapp-web/src/api/client.ts
index 8a0546e..71709c2 100644
--- a/apps/miniapp-web/src/api/client.ts
+++ b/apps/miniapp-web/src/api/client.ts
@@ -90,6 +90,21 @@ export type SkillsAskResponse = {
   tokens_estimate: number;
 };
 
+export type AskGrokRequest = {
+  session_id: string;
+  q: string;
+  lang?: "ru" | "en";
+  selected?: string[];
+};
+
+export type AskGrokResponse = {
+  answer: string;
+  used_skills: string[];
+  model: string;
+  tokens_estimate: number;
+  from_fatcontext?: boolean;
+};
+
 export async function askSkills(payload: SkillsAskRequest, signal?: AbortSignal): Promise<SkillsAskResponse> {
   const r = await apiFetch("/skills/ask", {
     method: "POST",
@@ -111,6 +126,28 @@ export async function askSkills(payload: SkillsAskRequest, signal?: AbortSignal)
   };
 }
 
+export async function askGrok(payload: AskGrokRequest, signal?: AbortSignal): Promise<AskGrokResponse> {
+  const r = await apiFetch("/chat/ask_grok", {
+    method: "POST",
+    headers: { "content-type": "application/json" },
+    body: JSON.stringify(payload),
+    signal,
+  });
+  if (!r.ok) {
+    const text = await r.text().catch(() => "");
+    const snippet = text.length > 200 ? `${text.slice(0, 200)}…` : text;
+    throw new ChatRequestError(r.status, `${getApiBaseUrl()}/chat/ask_grok`, snippet.trim());
+  }
+  const data = await r.json();
+  return {
+    answer: typeof data?.answer === "string" ? data.answer : "",
+    used_skills: ensureStringArray(data?.used_skills),
+    model: typeof data?.model === "string" ? data.model : "unknown",
+    tokens_estimate: typeof data?.tokens_estimate === "number" ? data.tokens_estimate : 0,
+    from_fatcontext: Boolean(data?.from_fatcontext),
+  };
+}
+
 export async function getTasks(): Promise<TasksStatusResponse> {
   const r = await apiFetch("/tasks/status");
   return r.json();
```

[Full diff continues for Chat.tsx, SkillsPage.tsx, and i18n files - see git diff output above]

