import { useEffect, useState } from "react";
import { normalizeCalLink } from "../shared/cal";
import { useI18n } from "../lib/i18n";
import { EmbedBriefPanel } from "./EmbedBriefPanel";

type Props = {
  lang: "ru" | "en";
  onSkills: (lang: "ru" | "en") => void;
  onTasks: () => void;
};

export function PrimaryActions({ lang, onSkills, onTasks }: Props) {
  const { t } = useI18n();
  const calLink = normalizeCalLink(
    import.meta.env.VITE_CAL_LINK || "dmitrybond/intro-30m"
  );
  const [briefOpen, setBriefOpen] = useState(false);

  useEffect(() => {
    try {
      const brief = new URLSearchParams(window.location.search).get("brief");
      if (brief === "1") setBriefOpen(true);
    } catch {}
  }, []);

  return (
    <>
      <div className="grid grid-cols-1 gap-2">
        <button
          id="book-meeting"
          className="h-12 rounded bg-black text-white"
          data-cal-link={calLink}
          data-cal-namespace="booking"
          data-cal-config='{"layout":"month_view","theme":"auto"}'
        >
          {t("actions.bookCall")}
        </button>
        <button
          className="h-12 rounded bg-gray-100 hover:bg-gray-200"
          onClick={() => setBriefOpen(true)}
        >
          {t("actions.brief")}
        </button>
        <button
          className="h-12 rounded bg-gray-100 hover:bg-gray-200"
          onClick={() => onSkills(lang)}
        >
          {t("actions.whatICanDo")}
        </button>
        <button className="h-12 rounded bg-gray-100 hover:bg-gray-200" onClick={onTasks}>
          {t("actions.taskStatus")}
        </button>
      </div>
      <EmbedBriefPanel open={briefOpen} lang={lang} onClose={() => setBriefOpen(false)} />
    </>
  );
}


