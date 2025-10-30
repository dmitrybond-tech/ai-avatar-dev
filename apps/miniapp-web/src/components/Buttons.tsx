import { getCal } from "../api/client";

type Props = {
  onSkills: () => void;
  onTasks: () => void;
};

export function PrimaryActions({ onSkills, onTasks }: Props) {
  const onBook = async () => {
    try {
      const { url } = await getCal();
      window.open(url, "_blank");
    } catch {
      window.open("https://cal.com/dmitrybond/intro-30m", "_blank");
    }
  };

  return (
    <div className="grid grid-cols-1 gap-2">
      <button className="h-12 rounded bg-black text-white" onClick={onBook}>Book a meeting</button>
      <button className="h-12 rounded bg-gray-100" onClick={onSkills}>What I can do?</button>
      <button className="h-12 rounded bg-gray-100" onClick={onTasks}>Task status</button>
    </div>
  );
}


