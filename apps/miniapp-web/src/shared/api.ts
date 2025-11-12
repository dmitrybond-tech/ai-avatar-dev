export const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/+$/, "");

export const apiUrl = (path: string) =>
  `${API_BASE}${path.startsWith("/") ? path : "/" + path}`;

