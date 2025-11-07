export type Skill = {
  id: string;
  slug: string;
  title: string;
  short: string;
  long?: string | null;
  bullets: string[];
  examples: string[];
  tags: string[];
  order?: number | null;
  category?: string | null;
  level?: string | null;
};

export type TaskItem = {
  id: string;
  title: string;
  status: 'todo' | 'in_progress' | 'done';
  updatedAt: string;
};

export type TasksStatusResponse = { items: TaskItem[] };

export type ChatIn = { text: string };
export type ChatOut = { reply: string };

export type CalLinkResponse = { url: string };


