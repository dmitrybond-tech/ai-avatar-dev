export const tg = (window as any)?.Telegram?.WebApp;
try {
  tg?.ready?.();
  tg?.expand?.();
} catch {}


