const rawEnvBase =
  typeof import.meta.env?.VITE_API_BASE_URL === "string"
    ? import.meta.env.VITE_API_BASE_URL.trim()
    : "";

export const API_BASE = rawEnvBase ? rawEnvBase.replace(/\/+$/, "") : "";

export const API_ROOT = API_BASE ? `${API_BASE}/api` : "/api";

const isAbsoluteUrl = (value: string): boolean => /^https?:\/\//i.test(value);
const ensureLeadingSlash = (value: string): string =>
  value.startsWith("/") ? value : `/${value}`;

export const apiUrl = (path: string): string => {
  if (!path) return API_ROOT;
  if (isAbsoluteUrl(path)) return path;
  const normalized = ensureLeadingSlash(path);
  return API_BASE ? `${API_BASE}${normalized}` : normalized;
};

export const CHAT_ASK_URL = `${API_ROOT}/chat/ask`;
export const CHAT_CONFIG_URL = `${API_ROOT}/chat/config`;
export const CHAT_EXPORT_URL = `${API_ROOT}/chat/export`;
export const ASK_URL = CHAT_ASK_URL;

