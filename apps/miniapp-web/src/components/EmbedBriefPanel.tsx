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
    <div className="fixed inset-0 z-[70] flex items-start justify-center overflow-y-auto modal-offset-pt bg-black/50 px-4 pb-6">
      <div className="relative modal-offset-mt modal-maxh h-full w-full overflow-hidden bg-white dark:bg-zinc-900">
        <button
          aria-label="Close"
          className="absolute right-3 top-3 z-[71] rounded-md px-2 py-1 bg-black text-white dark:bg-white dark:text-black hover:opacity-80"
          onClick={onClose}
        >
          ✕
        </button>
        <iframe
          title="Brief form"
          src={src}
          className="w-full h-full border-0"
          allow="camera; clipboard-write"
        />
      </div>
    </div>
  );
}

