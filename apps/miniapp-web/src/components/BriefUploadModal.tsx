import React, { useRef, useState } from "react";
import { createI18n } from "../lib/i18n";
import { apiUrl } from "../lib/apiBase";

const i18n = createI18n();

export function BriefUploadModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  if (!open) return null;

  const submit = async () => {
    const f = fileRef.current?.files?.[0];
    if (!f) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", f);
      fd.append("locale", i18n.get());
      const res = await fetch(apiUrl("/briefs/upload"), {
        method: "POST",
        body: fd,
      });
      if (!res.ok) {
        const errorText = await res.text().catch(() => String(res.status));
        throw new Error(errorText);
      }
      // Success - show popup
      try {
        const tg = (window as any).Telegram?.WebApp;
        if (tg?.showPopup) {
          tg.showPopup({
            title: i18n.t("brief.title"),
            message: i18n.t("brief.success"),
            buttons: [{ type: "ok" }],
          });
        } else {
          alert(i18n.t("brief.success"));
        }
      } catch (e) {
        alert(i18n.t("brief.success"));
      }
      onClose();
    } catch (e) {
      // Error - show popup
      try {
        const tg = (window as any).Telegram?.WebApp;
        if (tg?.showPopup) {
          tg.showPopup({
            title: i18n.t("brief.title"),
            message: i18n.t("brief.error"),
            buttons: [{ type: "ok" }],
          });
        } else {
          alert(i18n.t("brief.error"));
        }
      } catch {
        alert(i18n.t("brief.error"));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white dark:bg-zinc-900 rounded-2xl p-4 w-[92%] max-w-md" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold mb-3">{i18n.t("brief.title")}</h2>
        <input
          ref={fileRef}
          type="file"
          className="mb-3 w-full p-2 border rounded"
          accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.zip"
        />
        <div className="flex gap-2 justify-end">
          <button
            className="px-3 py-1 rounded-md border border-gray-300 hover:bg-gray-50"
            onClick={onClose}
            disabled={busy}
          >
            {i18n.t("brief.cancel")}
          </button>
          <button
            disabled={busy}
            className="px-3 py-1 rounded-md border bg-black text-white disabled:opacity-50"
            onClick={submit}
          >
            {i18n.t("brief.send")}
          </button>
        </div>
      </div>
    </div>
  );
}

