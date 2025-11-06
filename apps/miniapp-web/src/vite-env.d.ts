/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CAL_LINK?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        ready: () => void
        expand: () => void
        openTgLink?: (url: string) => void
      }
    }
  }
}

export {}
