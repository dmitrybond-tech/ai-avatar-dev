# Fix: Unterminated String Literal in ChatWidget.tsx

## Issue
"Unterminated string literal" error in `apps/website/src/components/ChatWidget.tsx` caused by curly quotes in concatenated string.

## Solution
Replaced string concatenation with template literal using backticks.

## Unified Diff

```diff
--- a/apps/website/src/components/ChatWidget.tsx
+++ b/apps/website/src/components/ChatWidget.tsx
@@ -74,12 +74,7 @@ export default function ChatWidget() {
     } catch (e) {
       setMessages((m) => [
         ...m,
         {
           id: crypto.randomUUID(),
           role: "assistant",
-          text:
-            "Local fallback: I couldn't reach the API. Here's an echo of your message: "" +
-            text +
-            "".",
+          text: `Local fallback: I couldn't reach the API. Here's an echo of your message: "${text}".`,
           ts: Date.now(),
         },
       ]);
```

## Change Summary

**File**: `apps/website/src/components/ChatWidget.tsx`  
**Lines Modified**: 1 (multi-line string concatenation → single template literal)  
**Type**: Bug fix  

**Before** (with curly quotes and concatenation):
```typescript
text:
  "Local fallback: I couldn't reach the API. Here's an echo of your message: "" +
  text +
  "".",
```

**After** (with template literal):
```typescript
text: `Local fallback: I couldn't reach the API. Here's an echo of your message: "${text}".`,
```

## Verification

✅ No linter errors  
✅ String properly terminated  
✅ Template literal correctly interpolates `text` variable  
✅ Maintains same functionality and message content  

## Testing

```powershell
# Run dev server
cd apps\website
pnpm dev

# Server should start without "Unterminated string literal" error
# Navigate to /miniapp/chat and test API failure scenario
```

**Status**: ✅ Fixed

