const rawEnv =
  typeof import.meta.env?.VITE_API_BASE_URL === "string"
    ? import.meta.env.VITE_API_BASE_URL.trim()
    : "";

const DEFAULT_BASE = "/api";

const isAbsoluteUrl = (value: string): boolean => /^https?:\/\//i.test(value);

const normalizeBase = (value: string): string => {
  if (!value) return DEFAULT_BASE;
  const withoutTrailing = value.replace(/\/+$/, "");
  if (isAbsoluteUrl(withoutTrailing)) {
    return withoutTrailing;
  }
  const withLeading = withoutTrailing.startsWith("/") ? withoutTrailing : `/${withoutTrailing}`;
  return withLeading || DEFAULT_BASE;
};

const normalizePath = (value: string): string => {
  if (!value) return "";
  if (isAbsoluteUrl(value)) return value;
  const withLeading = value.startsWith("/") ? value : `/${value}`;
  return withLeading.replace(/\/{2,}/g, "/");
};

const API_BASE_URL = normalizeBase(rawEnv);

export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const normalizedPath = normalizePath(path);
  if (!normalizedPath) {
    return fetch(API_BASE_URL, init);
  }
  if (isAbsoluteUrl(normalizedPath)) {
    return fetch(normalizedPath, init);
  }
  return fetch(`${API_BASE_URL}${normalizedPath}`, init);
}

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

export function apiUrl(path: string): string {
  const normalizedPath = normalizePath(path);
  if (!normalizedPath) {
    return API_BASE_URL;
  }
  if (isAbsoluteUrl(normalizedPath)) {
    return normalizedPath;
  }
  return `${API_BASE_URL}${normalizedPath}`;
}

