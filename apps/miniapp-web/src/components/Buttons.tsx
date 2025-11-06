import { useState } from "react";
import { normalizeCalLink } from "../shared/cal";
import { createI18n } from "../lib/i18n";
import { BriefUploadModal } from "./BriefUploadModal";

type Props = {
  onSkills: () => void;
  onTasks: () => void;
};

const i18n = createI18n();

export function PrimaryActions({ onSkills, onTasks }: Props) {
  const calLink = normalizeCalLink(
    import.meta.env.VITE_CAL_LINK || "dmitrybond/intro-30m"
  );
  const [uploadOpen, setUploadOpen] = useState(false);

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
          {i18n.t("actions.bookCall")}
        </button>
        <button
          className="h-12 rounded bg-gray-100 hover:bg-gray-200"
          onClick={() => setUploadOpen(true)}
        >
          {i18n.t("actions.brief")}
        </button>
        <button className="h-12 rounded bg-gray-100 hover:bg-gray-200" onClick={onSkills}>
          {i18n.t("actions.whatICanDo")}
        </button>
        <button className="h-12 rounded bg-gray-100 hover:bg-gray-200" onClick={onTasks}>
          {i18n.t("actions.taskStatus")}
        </button>
      </div>
      <BriefUploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} />
    </>
  );
}


