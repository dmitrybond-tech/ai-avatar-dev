export type SkillItem = {
  id: string;
  title: string;
  desc?: string;
  tags?: string[];
};

export type RulesResponse = { items: SkillItem[] };

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


