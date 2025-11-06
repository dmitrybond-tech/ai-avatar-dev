export type Skill = {
  slug: string;
  title_en: string;
  title_ru: string;
  short_en: string;
  short_ru: string;
  icon?: string | null;
  tags: string[];
};

export type SkillDetail = Skill & {
  bullets_en: string[];
  bullets_ru: string[];
  examples_en: string[];
  examples_ru: string[];
};

// Projected shape when server is called with ?lang=ru|en
export type ProjectedSkill = {
  slug: string;
  title: string;
  short: string;
  icon?: string | null;
  tags: string[];
};

export type ProjectedSkillDetail = ProjectedSkill & {
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


