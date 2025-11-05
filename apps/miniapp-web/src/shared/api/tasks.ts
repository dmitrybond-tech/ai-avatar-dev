export type PublicTask = {
  id: string; title: string; status: string; progressPct: number;
  reviewAt?: string; lastUpdated: string; tags: string[]; url: string;
};

const API = import.meta.env.VITE_API_BASE_URL ?? "";

export async function fetchPublicTasks(): Promise<PublicTask[]> {
  const r = await fetch(`${API}/api/tasks/public`, { credentials: "omit" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}


