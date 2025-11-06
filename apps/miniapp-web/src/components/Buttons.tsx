type Props = {
  onSkills: () => void;
  onTasks: () => void;
};

export function PrimaryActions({ onSkills, onTasks }: Props) {
  const calLink = import.meta.env.VITE_CAL_LINK || "dmitrybond/intro-call";

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


