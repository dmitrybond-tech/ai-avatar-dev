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

export type ChatMessageRole = "user" | "assistant" | "system";

export type ChatMessageDto = {
  role: ChatMessageRole;
  content: string;
};

export type ChatConfig = {
  persona: string;
  llmAvailable: boolean;
  notion: boolean;
  csvFallback: boolean;
  telegramExport: boolean;
  model?: string;
};

export type ChatAskPayload = {
  messages: ChatMessageDto[];
  lang: "ru" | "en";
  top_k?: number;
  use_llm?: boolean;
};

export type ChatAskResponse = {
  answer: string;
  sources: string[];
  used_llm: boolean;
  persona?: string;
};

export type ChatExportPayload = {
  conv_id?: string;
  lang?: "ru" | "en";
  messages: ChatMessageDto[];
  meta?: {
    title?: string | null;
    session_id?: string;
    lang?: "ru" | "en";
    tg_init_data?: string | null;
    persona?: string;
  };
};

export type CalLinkResponse = { url: string };


