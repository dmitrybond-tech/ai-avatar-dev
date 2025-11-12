import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "SMART_LLM_ENABLED";

function loadFromStorage(): boolean {
  if (typeof window === "undefined" || !("localStorage" in window)) {
    return false;
  }
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === null) return false;
    return stored === "true";
  } catch {
    return false;
  }
}

function saveToStorage(value: boolean): void {
  if (typeof window === "undefined" || !("localStorage" in window)) {
    return;
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, value ? "true" : "false");
  } catch {
    // ignore storage failures (Safari private mode, etc.)
  }
}

export function useSmartLLM(): [boolean, (value: boolean) => void] {
  const [smartLLM, setSmartLLMState] = useState<boolean>(() => loadFromStorage());

  useEffect(() => {
    saveToStorage(smartLLM);
  }, [smartLLM]);

  const setSmartLLM = useCallback((value: boolean) => {
    setSmartLLMState(value);
  }, []);

  return [smartLLM, setSmartLLM];
}

