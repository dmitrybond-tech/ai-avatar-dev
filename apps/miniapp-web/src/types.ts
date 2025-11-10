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

export type ChatSource = { id: string; title: string; score: number };
export type ChatOut = { reply: string; sources: ChatSource[]; mode: 'extractive' | 'llm' };
export type ChatConfig = { smart_default: boolean; rag_mode: 'extractive' | 'llm'; topk: number };
export type ChatAskPayload = { text: string; lang?: 'ru' | 'en'; llm?: boolean };

export type CalLinkResponse = { url: string };


