import { useEffect } from "react";

type Props = { open: boolean; lang: "en" | "ru"; onClose: () => void };

export function EmbedBriefPanel({ open, lang, onClose }: Props) {
  useEffect(() => {
    const tg = (window as any).Telegram?.WebApp;
    
    if (!open) {
      try {
        if (tg?.BackButton) {
          tg.BackButton.hide();
        }
      } catch {}
      return;
    }

    try {
      if (tg?.BackButton) {
        tg.BackButton.show();
        const handler = () => onClose();
        tg.BackButton.onClick(handler);
        return () => {
          try {
            tg.BackButton.offClick(handler);
            tg.BackButton.hide();
          } catch {}
        };
      }
    } catch {}
  }, [open, onClose]);

  if (!open) return null;

  const src = `/brief?embed=1&lang=${lang}`;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto modal-offset-pt bg-black/50 px-4 pb-6"
      onClick={onClose}
    >
      <div
        className="relative modal-offset-mt modal-maxh w-full overflow-auto bg-white dark:bg-zinc-900"
        onClick={(event) => event.stopPropagation()}
        style={{ minHeight: 'min(100svh, 100dvh, 100vh)' }}
      >
        <button
          aria-label="Close"
          className="absolute right-3 top-3 z-[71] rounded-md bg-black px-2 py-1 text-white hover:opacity-80 dark:bg-white dark:text-black"
          onClick={onClose}
        >
          ✕
        </button>
        <iframe
          title="Brief form"
          src={src}
          className="block h-full w-full border-0"
          allow="camera; clipboard-write"
          style={{ minHeight: 'min(100svh, 100dvh, 100vh)' }}
        />
      </div>
    </div>
  );
}

