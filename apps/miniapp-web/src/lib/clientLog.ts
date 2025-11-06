export async function clientLog(
  level: "info" | "warn" | "error",
  message: string,
  extra: any = {}
) {
  try {
    await fetch("/client-log", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        level,
        message,
        extra,
        ua: navigator.userAgent,
      }),
    });
  } catch {
    // Best-effort logging, fail silently
  }
}

