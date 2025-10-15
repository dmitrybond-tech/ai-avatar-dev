/**
 * Client-side configuration.
 * In production, these should be set via environment variables at build time.
 */

const API_BASE_URL = import.meta.env.PUBLIC_API_BASE_URL || 'http://localhost:8080';
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

export const config = {
  apiBaseUrl: API_BASE_URL,
  wsUrl: `${WS_BASE_URL}/chat/stream`,
} as const;
