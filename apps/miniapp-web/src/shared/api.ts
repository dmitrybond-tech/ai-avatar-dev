export function getApiBaseUrl(): string {
  try {
    const raw = (window as any).__API_BASE__ || import.meta.env.VITE_API_BASE_URL || "/api";
    return String(raw).replace(/\/+$/, ""); // без хвостового '/'
  } catch {
    return "/api";
  }
}

export function apiUrl(p: string): string {
  const base = getApiBaseUrl();                          // напр. '/api'
  const path = ("/" + String(p || "").trim()).replace(/\/+/, "/");
  return base + path;                                    // всегда абсолютный: '/api/skills'
}

