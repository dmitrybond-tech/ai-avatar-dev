import React, { useRef, useState, useMemo } from "react";
import { useI18n } from "../lib/i18n";
import { submitBriefUpload } from "../features/upload/upload";

const ACCEPT = "image/*,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,application/zip,application/x-zip-compressed";
const emailRx = /^[^\s@]+@[^\s@]+\.[^\s@]+$/i;
class ModalErrorBoundary extends React.Component<{ children: React.ReactNode }, { error: Error | null }> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  componentDidCatch(error: Error) {
    // Keep it minimal; show inline error instead of blank overlay
    // eslint-disable-next-line no-console
    console.error("BriefUploadModal render error:", error);
  }
  render() {
    if (this.state.error) {
      return (
        <div className="p-4 text-sm text-red-700 bg-red-50 rounded-md border border-red-200">
          {String(this.state.error.message || this.state.error)}
        </div>
      );
    }
    return this.props.children as any;
  }
}

export function BriefUploadModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ name: "", company: "", phone: "", email: "", message: "" });
  const [file, setFile] = useState<File | null>(null);
  const [submitStatus, setSubmitStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const { locale, t } = useI18n();

  if (!open) return null;
  // Dev-safe visibility probe to help diagnose blank overlays
  // eslint-disable-next-line no-console
  console.debug("BriefUploadModal open=true reached render path");

  const phoneSanitized = useMemo(() => form.phone.replace(/[^\d+]/g, ""), [form.phone]);
  const emailValid = emailRx.test(form.email);
  const phoneValid = phoneSanitized.length >= 7;
  const isReady = Boolean(form.name && form.company && emailValid && phoneValid && file && !busy);

  const onPickFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] || null;
    setFile(f);
    setSubmitStatus(null);
  };

  const submit = async () => {
    if (!isReady || !file) return;
    setBusy(true);
    setSubmitStatus(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("locale", locale);
      fd.append("name", form.name.trim());
      fd.append("company", form.company.trim());
      fd.append("phone", phoneSanitized);
      fd.append("email", form.email.trim());
      if (form.message?.trim()) {
        fd.append("message", form.message.trim());
      }

      const result = await submitBriefUpload(fd);
      const parts = [t("brief.success")];
      if (result.filename) parts.push(result.filename);
      if (result.telegram_sent === false) {
        parts.push(locale === "ru" ? "Telegram не настроен — файл сохранён." : "Telegram delivery skipped; file stored.");
      }
      setSubmitStatus({ type: "success", message: parts.join(" • ") });
      setForm({ name: "", company: "", phone: "", email: "", message: "" });
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : t("brief.error");
      setSubmitStatus({ type: "error", message: errorMsg });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[60] flex items-start justify-center overflow-y-auto modal-offset-pt bg-black/40 px-4 pb-6"
      onClick={onClose}
    >
      <div
        className="form-dark relative modal-offset-mt modal-maxh w-full overflow-auto rounded-2xl bg-white p-4 dark:bg-zinc-900"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={t("brief.title")}
      >
        <button aria-label="Close" className="absolute right-3 top-3 text-white/80" onClick={onClose}>✕</button>
        <ModalErrorBoundary>
          <h2 className="text-lg font-semibold mb-3 dark:text-white">{t("brief.title")}</h2>

          {submitStatus && (
            <div
              role="alert"
              aria-live="polite"
              className={`mb-4 p-3 rounded-md ${
                submitStatus.type === "success"
                  ? "bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-200 border border-green-200 dark:border-green-800"
                  : "bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200 border border-red-200 dark:border-red-800"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span>{submitStatus.message}</span>
              </div>
            </div>
          )}

          <div className="space-y-3">
          <label className="block">
            <span className="form-label block mb-1">{locale === "ru" ? "Имя" : "Name"}</span>
            <input
              className="w-full rounded-md border px-3 py-2 bg-white dark:bg-zinc-800 dark:border-zinc-700 dark:text-white placeholder-white/70"
              value={form.name}
              onChange={(e) => {
                setForm({ ...form, name: e.target.value });
                setSubmitStatus(null);
              }}
              placeholder={locale === "ru" ? "Ваше имя" : "Your name"}
            />
          </label>

          <label className="block">
            <span className="form-label block mb-1">{locale === "ru" ? "Компания" : "Company"}</span>
            <input
              className="w-full rounded-md border px-3 py-2 bg-white dark:bg-zinc-800 dark:border-zinc-700 dark:text-white placeholder-white/70"
              value={form.company}
              onChange={(e) => {
                setForm({ ...form, company: e.target.value });
                setSubmitStatus(null);
              }}
              placeholder={locale === "ru" ? "Название компании" : "Company name"}
            />
          </label>

          <label className="block">
            <span className="form-label block mb-1">{locale === "ru" ? "Телефон" : "Phone"}</span>
            <input
              className="w-full rounded-md border px-3 py-2 bg-white dark:bg-zinc-800 dark:border-zinc-700 dark:text-white placeholder-white/70"
              value={form.phone}
              onChange={(e) => {
                setForm({ ...form, phone: e.target.value });
                setSubmitStatus(null);
              }}
              placeholder={locale === "ru" ? "+7 999 123-45-67" : "+1 555 000 1234"}
              inputMode="tel"
            />
            {!phoneValid && form.phone && <p className="hint error mt-1 text-sm">{locale === "ru" ? "Проверьте номер" : "Check phone format"}</p>}
          </label>

          <label className="block">
            <span className="form-label block mb-1">Email</span>
            <input
              type="email"
              className="w-full rounded-md border px-3 py-2 bg-white dark:bg-zinc-800 dark:border-zinc-700 dark:text-white placeholder-white/70"
              value={form.email}
              onChange={(e) => {
                setForm({ ...form, email: e.target.value });
                setSubmitStatus(null);
              }}
              placeholder="you@example.com"
              inputMode="email"
            />
            {!emailValid && form.email && <p className="hint error mt-1 text-sm">{locale === "ru" ? "Проверьте email" : "Check email"}</p>}
          </label>

          <label className="block">
            <span className="form-label block mb-1">{locale === "ru" ? "Комментарий (необязательно)" : "Comment (optional)"}</span>
            <textarea
              className="w-full rounded-md border px-3 py-2 bg-white dark:bg-zinc-800 dark:border-zinc-700 dark:text-white placeholder-white/70"
              rows={3}
              value={form.message}
              onChange={(e) => {
                setForm({ ...form, message: e.target.value });
                setSubmitStatus(null);
              }}
              placeholder={locale === "ru" ? "Коротко о задаче..." : "Short description..."}
            />
          </label>

          <label className="block">
            <span className="form-label block mb-1">{locale === "ru" ? "Файл" : "File"}</span>
            <input
              ref={fileRef}
              type="file"
              accept={ACCEPT}
              capture="environment"
              onChange={onPickFile}
              className="w-full text-sm"
            />
            <p className="hint mt-1 text-xs">
              {locale === "ru"
                ? "Поддерживаются: изображения, PDF, DOC/DOCX, TXT, ZIP"
                : "Supported: images, PDF, DOC/DOCX, TXT, ZIP"}
            </p>
          </label>
          </div>

          <div className="flex gap-2 justify-end mt-4">
            <button className="px-3 py-1 rounded-md border dark:text-white" onClick={onClose} disabled={busy}>
              {t("brief.cancel")}
            </button>
            <button
              disabled={!isReady}
              className="px-3 py-1 rounded-md border bg-black text-white disabled:opacity-50"
              onClick={submit}
            >
              {busy ? (locale === "ru" ? "Отправка..." : "Sending...") : t("brief.send")}
            </button>
          </div>
        </ModalErrorBoundary>
      </div>
    </div>
  );
}

