/// <reference types="astro/client" />

interface Window {
  Telegram?: {
    WebApp: {
      ready(): void;
      initData: string;
      themeParams: Record<string, string>;
      colorScheme: 'light' | 'dark';
      expand(): void;
      close(): void;
    };
  };
}

