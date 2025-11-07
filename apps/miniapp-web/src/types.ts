export type Skill = {
  id: string;
  slug: string;
  name: string;
  short: string;
  long: string;
  tags: string[];
  category?: string | null;
  icon?: string | null;
  order?: number | null;
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


