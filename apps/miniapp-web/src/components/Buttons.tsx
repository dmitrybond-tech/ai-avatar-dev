type Props = {
  onSkills: () => void;
  onTasks: () => void;
};

import { normalizeCalLink } from "../shared/cal";

export function PrimaryActions({ onSkills, onTasks }: Props) {
  const calLink = normalizeCalLink(
    import.meta.env.VITE_CAL_LINK || "dmitrybond/intro-30m"
  );

  return (
    <div className="grid grid-cols-1 gap-2">
      <button
        id="book-meeting"
        className="h-12 rounded bg-black text-white"
        data-cal-link={calLink}
        data-cal-namespace="booking"
        data-cal-config='{"layout":"month_view","theme":"auto"}'
      >
        Book a meeting
      </button>
      <button className="h-12 rounded bg-gray-100" onClick={onSkills}>What I can do?</button>
      <button className="h-12 rounded bg-gray-100" onClick={onTasks}>Task status</button>
    </div>
  );
}


