import React, { useRef, useState, useMemo } from "react";
import { createI18n } from "../lib/i18n";
import { apiUrl } from "../lib/apiBase";

const i18n = createI18n();

const ACCEPT = "image/*,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,application/zip,application/x-zip-compressed";
const emailRx = /^[^\s@]+@[^\s@]+\.[^\s@]+$/i;

export function BriefUploadModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ name: "", company: "", phone: "", email: "" });
  const [file, setFile] = useState<File | null>(null);

  if (!open) return null;

  const phoneSanitized = useMemo(() => form.phone.replace(/[^\d+]/g, ""), [form.phone]);
  const emailValid = emailRx.test(form.email);
  const phoneValid = phoneSanitized.length >= 7;
  const isReady = Boolean(form.name && form.company && emailValid && phoneValid && file && !busy);

  const onPickFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] || null;
    setFile(f);
  };

  const submit = async () => {
    if (!isReady || !file) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("locale", i18n.get());
      fd.append("name", form.name.trim());
      fd.append("company", form.company.trim());
      fd.append("phone", phoneSanitized);
      fd.append("email", form.email.trim());
      const res = await fetch(apiUrl("/briefs/upload"), {
        method: "POST",
        body: fd,
      });
      if (!res.ok) throw new Error(String(res.status));
      const tg = (window as any).Telegram?.WebApp;
      if (tg?.showPopup) {
        tg.showPopup({ title: i18n.t("brief.title"), message: i18n.t("brief.success"), buttons: [{ type: "ok" }] });
      } else {
        alert(i18n.t("brief.success"));
      }
      onClose();
    } catch (e) {
      const tg = (window as any).Telegram?.WebApp;
      if (tg?.showPopup) {
        tg.showPopup({ title: i18n.t("brief.title"), message: i18n.t("brief.error"), buttons: [{ type: "ok" }] });
      } else {
        alert(i18n.t("brief.error"));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="form-dark bg-white dark:bg-zinc-900 rounded-2xl p-4 w-[92%] max-w-md" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold mb-3 dark:text-white">{i18n.t("brief.title")}</h2>

        <div className="space-y-3">
          <label className="block">
            <span className="form-label block mb-1">{i18n.get()==="ru" ? "Имя" : "Name"}</span>
            <input
              className="w-full rounded-md border px-3 py-2 bg-white dark:bg-zinc-800 dark:border-zinc-700 dark:text-white placeholder-white/70"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder={i18n.get()==="ru" ? "Ваше имя" : "Your name"}
            />
          </label>

          <label className="block">
            <span className="form-label block mb-1">{i18n.get()==="ru" ? "Компания" : "Company"}</span>
            <input
              className="w-full rounded-md border px-3 py-2 bg-white dark:bg-zinc-800 dark:border-zinc-700 dark:text-white placeholder-white/70"
              value={form.company}
              onChange={(e) => setForm({ ...form, company: e.target.value })}
              placeholder={i18n.get()==="ru" ? "Название компании" : "Company name"}
            />
          </label>

          <label className="block">
            <span className="form-label block mb-1">{i18n.get()==="ru" ? "Телефон" : "Phone"}</span>
            <input
              className="w-full rounded-md border px-3 py-2 bg-white dark:bg-zinc-800 dark:border-zinc-700 dark:text-white placeholder-white/70"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              placeholder={i18n.get()==="ru" ? "+7 999 123-45-67" : "+1 555 000 1234"}
              inputMode="tel"
            />
            {!phoneValid && form.phone && <p className="hint error mt-1 text-sm">{i18n.get()==="ru" ? "Проверьте номер" : "Check phone format"}</p>}
          </label>

          <label className="block">
            <span className="form-label block mb-1">Email</span>
            <input
              type="email"
              className="w-full rounded-md border px-3 py-2 bg-white dark:bg-zinc-800 dark:border-zinc-700 dark:text-white placeholder-white/70"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="you@example.com"
              inputMode="email"
            />
            {!emailValid && form.email && <p className="hint error mt-1 text-sm">{i18n.get()==="ru" ? "Проверьте email" : "Check email"}</p>}
          </label>

          <label className="block">
            <span className="form-label block mb-1">{i18n.get()==="ru" ? "Файл" : "File"}</span>
            <input
              ref={fileRef}
              type="file"
              accept={ACCEPT}
              capture="environment"
              onChange={onPickFile}
              className="w-full text-sm"
            />
            <p className="hint mt-1 text-xs">
              {i18n.get()==="ru"
                ? "Поддерживаются: изображения, PDF, DOC/DOCX, TXT, ZIP"
                : "Supported: images, PDF, DOC/DOCX, TXT, ZIP"}
            </p>
          </label>
        </div>

        <div className="flex gap-2 justify-end mt-4">
          <button className="px-3 py-1 rounded-md border dark:text-white" onClick={onClose} disabled={busy}>
            {i18n.t("brief.cancel")}
          </button>
          <button
            disabled={!isReady}
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

