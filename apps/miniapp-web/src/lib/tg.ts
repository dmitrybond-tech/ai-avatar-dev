export function isTelegramWebView(): boolean {
  try {
    // UA hint or presence of Telegram SDK object
    const ua = typeof navigator !== 'undefined' ? navigator.userAgent : '';
    const isUA = /Telegram/i.test(ua);
    const hasSDK = typeof (window as any)?.Telegram?.WebApp !== 'undefined';
    return Boolean(isUA || hasSDK);
  } catch {
    return false;
  }
}

export function getTelegramWebApp(): any | undefined {
  try {
    const tg = (window as any)?.Telegram?.WebApp;
    if (!tg) return undefined;
    try { tg.expand?.(); } catch (e) { /* ignore */ }
    try { tg.ready?.(); } catch (e) { /* ignore */ }
    return tg;
  } catch {
    return undefined;
  }
}

