/// <reference types="vite/client" />

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
