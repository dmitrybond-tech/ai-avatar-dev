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

export type ChatIn = { text: string };
export type ChatOut = { reply: string };

export type CalLinkResponse = { url: string };


