export function safeInitTelegram() {
  const tg = (window as any).Telegram?.WebApp;
  const inTg = !!tg;
  try {
    if (inTg && tg.ready) {
      tg.ready();
    }
  } catch {
    // Silently ignore initialization errors
  }
  return { tg, inTg };
}

