// Message types
export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: number;
  meta?: Record<string, unknown>;
}

// Persona configuration
export interface PersonaPreset {
  id: string;
  name: string;
  description?: string;
  systemPrompt: string;
  voice?: string;
  temperature?: number;
  maxTokens?: number;
}

// WebSocket message envelopes
export type WsEnvelope =
  | WsUserMessage
  | WsPartialMessage
  | WsFinalMessage
  | WsErrorMessage
  | WsConnectedMessage;

export interface WsUserMessage {
  type: 'user_message';
  text: string;
  session_id?: string;
  persona?: string;
}

export interface WsPartialMessage {
  type: 'partial';
  delta: string;
}

export interface WsFinalMessage {
  type: 'final';
  text: string;
  session_id: string;
  meta?: Record<string, unknown>;
}

export interface WsErrorMessage {
  type: 'error';
  message: string;
  code?: string;
}

export interface WsConnectedMessage {
  type: 'connected';
  session_id?: string;
}

// HTTP request/response types
export interface ChatRequest {
  session_id?: string | null;
  message: string;
  persona?: string;
  params?: Record<string, unknown>;
}

export interface ChatResponse {
  session_id: string;
  answer: string;
  meta?: Record<string, unknown>;
}

export interface TTSRequest {
  text: string;
  voice_preset?: string;
}

export interface TTSResponse {
  audio_url: string;
  duration_sec: number;
}

export interface TelegramVerifyRequest {
  init_data: string;
}

export interface TelegramVerifyResponse {
  session_token: string;
  session_id: string;
}

// Default persona presets
export const DEFAULT_PERSONAS: PersonaPreset[] = [
  {
    id: 'default',
    name: 'Default Assistant',
    systemPrompt: 'You are a helpful AI assistant. Be concise and friendly.',
    voice: 'male_russian_1',
    temperature: 0.7,
    maxTokens: 500,
  },
  {
    id: 'technical',
    name: 'Technical Expert',
    systemPrompt: 'You are a technical expert. Provide detailed, accurate information.',
    voice: 'male_russian_1',
    temperature: 0.5,
    maxTokens: 800,
  },
];

// Constants
export const API_ROUTES = {
  HEALTH: '/healthz',
  CHAT: '/chat',
  CHAT_STREAM: '/chat/stream',
  TTS: '/voice/tts',
  TG_VERIFY: '/tg/verify',
} as const;

export const SESSION_EXPIRY_SECONDS = 3600;
export const MAX_MESSAGE_LENGTH = 4000;
export const RATE_LIMIT_WINDOW_SECONDS = 60;
export const RATE_LIMIT_MAX_REQUESTS = 20;

