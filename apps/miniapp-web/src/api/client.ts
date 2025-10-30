import { apiUrl } from "../lib/apiBase.ts";
import type { RulesResponse, TasksStatusResponse, CalLinkResponse, ChatOut } from "../types";

export async function getRules(): Promise<RulesResponse> {
  const r = await fetch(apiUrl("/rules"));
  return r.json();
}

export async function getTasks(): Promise<TasksStatusResponse> {
  const r = await fetch(apiUrl("/tasks/status"));
  return r.json();
}

export async function getCal(): Promise<CalLinkResponse> {
  const r = await fetch(apiUrl("/cal/link"));
  return r.json();
}

export async function postChat(text: string): Promise<ChatOut> {
  const r = await fetch(apiUrl("/api/chat/stub"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  return r.json();
}


