export const API_BASE =
  (import.meta.env.VITE_API_BASE_URL && import.meta.env.VITE_API_BASE_URL.trim())
    ? import.meta.env.VITE_API_BASE_URL.trim().replace(/\/+$/, '')
    : (typeof window !== 'undefined' && window.location && window.location.origin
        ? window.location.origin
        : '');

export const apiUrl = (p: string) => `${API_BASE}${p.startsWith('/') ? p : '/' + p}`;


