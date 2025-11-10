export type SkillCard = {
  slug: string;
  title: string;
  short: string;
  tags: string[];
};

export type SkillDetail = {
  slug: string;
  title: string;
  short?: string | null;
  tags: string[];
  bullets: string[];
  examples: string[];
};

export type TaskItem = {
  id: string;
  title: string;
  status: 'todo' | 'in_progress' | 'done';
  updatedAt: string;
};

export type TasksStatusResponse = { items: TaskItem[] };

export type ChatMode = "stub" | "llm";
export type ChatOut = { reply: string; mode: ChatMode; session_id: string; persona: string };
export type ChatConfig = {
  persona: string;
  smart_chat: boolean;
  rag_mode: "extractive" | "llm";
  provider: string;
  model: string;
};
export type ChatAskPayload = {
  text: string;
  lang?: "ru" | "en";
  llm?: boolean;
  session_id?: string;
  tg_init_data?: string | null;
};
export type ChatExportPayload = {
  session_id: string;
  tg_init_data?: string | null;
};

export type CalLinkResponse = { url: string };


