export type PublicTask = {
  id: string;
  title: string;
  status: string;
  scope?: number | null;
  done?: number | null;
  progressPct: number;
  description?: string | null;
  tags: string[];
  reviewAt?: string | null;
  lastUpdated: string;
  url: string;
};

const API = import.meta.env.VITE_API_BASE_URL ?? "";

export async function fetchPublicTasks(): Promise<PublicTask[]> {
  const r = await fetch(`${API}/api/tasks/public`, { credentials: "omit" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function fetchOpenTasks(): Promise<PublicTask[]> {
  const r = await fetch(`${API}/api/tasks/public?statuses=In%20Progress,Review&limit=20`, { credentials: "omit" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}


