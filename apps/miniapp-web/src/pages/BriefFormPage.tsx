import React, { useRef, useState, useMemo, useEffect } from "react";
import { createI18n, detectLocale } from "../lib/i18n";

const ACCEPT = "image/*,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,application/zip,application/x-zip-compressed";
const emailRx = /^[^\s@]+@[^\s@]+\.[^\s@]+$/i;

// Throttle function for resize messages
function throttle<T extends (...args: any[]) => void>(func: T, wait: number): T {
  let timeout: NodeJS.Timeout | null = null;
  let previous = 0;
  return ((...args: any[]) => {
    const now = Date.now();
    const remaining = wait - (now - previous);
    if (remaining <= 0 || remaining > wait) {
      if (timeout) {
        clearTimeout(timeout);
        timeout = null;
      }
      previous = now;
      func(...args);
    } else if (!timeout) {
      timeout = setTimeout(() => {
        previous = Date.now();
        timeout = null;
        func(...args);
      }, remaining);
    }
  }) as T;
}

// Auto-resize for iframe embedding
function useIframeResize() {
  useEffect(() => {
    const sendHeight = () => {
      if (window.parent !== window) {
        const height = document.body.scrollHeight;
        window.parent.postMessage({ type: "brief:height", h: height }, "*");
      }
    };

    const throttledSendHeight = throttle(sendHeight, 100);

    // Initial send
    sendHeight();

    // Watch for content changes
    const observer = new ResizeObserver(throttledSendHeight);
    observer.observe(document.body);

    // Also listen to window resize
    window.addEventListener("resize", throttledSendHeight);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", throttledSendHeight);
    };
  }, []);
}

export function BriefFormPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ name: "", company: "", phone: "", email: "", message: "" });
  const [file, setFile] = useState<File | null>(null);
  const [submitStatus, setSubmitStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Detect locale from URL or default
  const urlParams = useMemo(() => new URLSearchParams(window.location.search), []);
  const langParam = urlParams.get("lang");
  const embedMode = urlParams.get("embed") === "1";
  const themeParam = urlParams.get("theme");
  
  const initialLocale = langParam === "ru" || langParam === "en" ? langParam : detectLocale();
  const [i18n] = useState(() => createI18n(initialLocale));

  // Apply theme if specified
  useEffect(() => {
    if (themeParam === "dark" || themeParam === "light") {
      document.documentElement.classList.toggle("dark", themeParam === "dark");
    }
  }, [themeParam]);

  // Iframe resize
  useIframeResize();

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
      fd.append("locale", i18n.get());
      fd.append("name", form.name.trim());
      fd.append("company", form.company.trim());
      fd.append("phone", phoneSanitized);
      fd.append("email", form.email.trim());
      if (form.message?.trim()) {
        fd.append("message", form.message.trim());
      }

      async function postBrief(fd: FormData) {
        const tryPost = async (url: string) => {
          const res = await fetch(url, { method: "POST", body: fd });
          if (!res.ok) throw new Error(String(res.status));
          return res.json();
        };
        try {
          return await tryPost("/briefs/upload");
        } catch (e: any) {
          // fallback if nginx doesn't proxy /briefs/ yet
          return await tryPost("/api/briefs/upload");
        }
      }

      const result = await postBrief(fd);
      if (result.ok) {
        setSubmitStatus({ type: "success", message: i18n.t("brief.success") });
        // Reset form
        setForm({ name: "", company: "", phone: "", email: "", message: "" });
        setFile(null);
        if (fileRef.current) fileRef.current.value = "";
        // Auto-hide success message after 5s
        setTimeout(() => setSubmitStatus(null), 5000);
      } else {
        throw new Error(i18n.t("brief.error"));
      }
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : i18n.t("brief.error");
      setSubmitStatus({ type: "error", message: errorMsg });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`min-h-screen w-full ${embedMode ? "" : "bg-white dark:bg-zinc-900"} p-4`}>
      <div className="max-w-2xl mx-auto">
        {!embedMode && (
          <header className="mb-6">
            <h1 className="text-2xl font-semibold dark:text-white">{i18n.t("brief.title")}</h1>
          </header>
        )}

        <div className="bg-white dark:bg-zinc-900 rounded-2xl p-6 border border-gray-200 dark:border-zinc-700">
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
              {submitStatus.message}
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit();
            }}
            className="space-y-4"
          >
            <label className="block">
              <span className="block mb-1 text-sm font-medium dark:text-white">
                {i18n.get() === "ru" ? "Имя" : "Name"} <span className="text-red-500">*</span>
              </span>
              <input
                type="text"
                required
                aria-required="true"
                className="w-full rounded-md border border-gray-300 dark:border-zinc-700 px-3 py-2 bg-white dark:bg-zinc-800 dark:text-white placeholder-gray-400 dark:placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-white"
                value={form.name}
                onChange={(e) => {
                  setForm({ ...form, name: e.target.value });
                  setSubmitStatus(null);
                }}
                placeholder={i18n.get() === "ru" ? "Ваше имя" : "Your name"}
                aria-invalid={!form.name && form.name !== ""}
              />
            </label>

            <label className="block">
              <span className="block mb-1 text-sm font-medium dark:text-white">
                {i18n.get() === "ru" ? "Компания" : "Company"} <span className="text-red-500">*</span>
              </span>
              <input
                type="text"
                required
                aria-required="true"
                className="w-full rounded-md border border-gray-300 dark:border-zinc-700 px-3 py-2 bg-white dark:bg-zinc-800 dark:text-white placeholder-gray-400 dark:placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-white"
                value={form.company}
                onChange={(e) => {
                  setForm({ ...form, company: e.target.value });
                  setSubmitStatus(null);
                }}
                placeholder={i18n.get() === "ru" ? "Название компании" : "Company name"}
                aria-invalid={!form.company && form.company !== ""}
              />
            </label>

            <label className="block">
              <span className="block mb-1 text-sm font-medium dark:text-white">
                {i18n.get() === "ru" ? "Телефон" : "Phone"} <span className="text-red-500">*</span>
              </span>
              <input
                type="tel"
                required
                aria-required="true"
                inputMode="tel"
                className="w-full rounded-md border border-gray-300 dark:border-zinc-700 px-3 py-2 bg-white dark:bg-zinc-800 dark:text-white placeholder-gray-400 dark:placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-white"
                value={form.phone}
                onChange={(e) => {
                  setForm({ ...form, phone: e.target.value });
                  setSubmitStatus(null);
                }}
                placeholder={i18n.get() === "ru" ? "+7 999 123-45-67" : "+1 555 000 1234"}
                aria-invalid={!phoneValid && form.phone !== ""}
                aria-describedby={!phoneValid && form.phone ? "phone-error" : undefined}
              />
              {!phoneValid && form.phone && (
                <p id="phone-error" className="mt-1 text-sm text-red-600 dark:text-red-400" role="alert">
                  {i18n.get() === "ru" ? "Проверьте номер" : "Check phone format"}
                </p>
              )}
            </label>

            <label className="block">
              <span className="block mb-1 text-sm font-medium dark:text-white">
                Email <span className="text-red-500">*</span>
              </span>
              <input
                type="email"
                required
                aria-required="true"
                inputMode="email"
                className="w-full rounded-md border border-gray-300 dark:border-zinc-700 px-3 py-2 bg-white dark:bg-zinc-800 dark:text-white placeholder-gray-400 dark:placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-white"
                value={form.email}
                onChange={(e) => {
                  setForm({ ...form, email: e.target.value });
                  setSubmitStatus(null);
                }}
                placeholder="you@example.com"
                aria-invalid={!emailValid && form.email !== ""}
                aria-describedby={!emailValid && form.email ? "email-error" : undefined}
              />
              {!emailValid && form.email && (
                <p id="email-error" className="mt-1 text-sm text-red-600 dark:text-red-400" role="alert">
                  {i18n.get() === "ru" ? "Проверьте email" : "Check email"}
                </p>
              )}
            </label>

            <label className="block">
              <span className="block mb-1 text-sm font-medium dark:text-white">
                {i18n.get() === "ru" ? "Комментарий (необязательно)" : "Comment (optional)"}
              </span>
              <textarea
                className="w-full rounded-md border border-gray-300 dark:border-zinc-700 px-3 py-2 bg-white dark:bg-zinc-800 dark:text-white placeholder-gray-400 dark:placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-white resize-y"
                rows={3}
                value={form.message}
                onChange={(e) => {
                  setForm({ ...form, message: e.target.value });
                  setSubmitStatus(null);
                }}
                placeholder={i18n.get() === "ru" ? "Коротко о задаче..." : "Short description..."}
              />
            </label>

            <label className="block">
              <span className="block mb-1 text-sm font-medium dark:text-white">
                {i18n.get() === "ru" ? "Файл" : "File"} <span className="text-red-500">*</span>
              </span>
              <input
                ref={fileRef}
                type="file"
                required
                aria-required="true"
                accept={ACCEPT}
                capture="environment"
                onChange={onPickFile}
                className="w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-black file:text-white hover:file:bg-gray-800 dark:file:bg-white dark:file:text-black dark:hover:file:bg-gray-200"
              />
              <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                {i18n.get() === "ru"
                  ? "Поддерживаются: изображения, PDF, DOC/DOCX, TXT, ZIP"
                  : "Supported: images, PDF, DOC/DOCX, TXT, ZIP"}
              </p>
              {file && (
                <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">
                  {i18n.get() === "ru" ? "Выбран файл: " : "Selected: "}
                  <span className="font-medium">{file.name}</span>
                </p>
              )}
            </label>

            <div className="flex gap-3 justify-end pt-2">
              <button
                type="button"
                onClick={() => {
                  setForm({ name: "", company: "", phone: "", email: "", message: "" });
                  setFile(null);
                  setSubmitStatus(null);
                  if (fileRef.current) fileRef.current.value = "";
                }}
                disabled={busy}
                className="px-4 py-2 rounded-md border border-gray-300 dark:border-zinc-700 dark:text-white hover:bg-gray-50 dark:hover:bg-zinc-800 disabled:opacity-50"
              >
                {i18n.t("brief.cancel")}
              </button>
              <button
                type="submit"
                disabled={!isReady}
                className="px-4 py-2 rounded-md bg-black dark:bg-white text-white dark:text-black font-medium hover:bg-gray-800 dark:hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {busy ? (i18n.get() === "ru" ? "Отправка..." : "Sending...") : i18n.t("brief.send")}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

