import { useState } from "react";

const STORAGE_KEY = "chat_session_id";

const makeId = (): string => {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2, 10);
};

const readSessionId = (): string => {
  if (typeof window === "undefined") {
    return makeId();
  }
  try {
    const existing = window.sessionStorage.getItem(STORAGE_KEY);
    if (existing && existing.trim().length > 0) {
      return existing;
    }
    const generated = makeId();
    window.sessionStorage.setItem(STORAGE_KEY, generated);
    return generated;
  } catch {
    return makeId();
  }
};

export function useChatSessionId(): string {
  const [sessionId] = useState<string>(() => readSessionId());
  return sessionId;
}

