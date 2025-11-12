/**
 * Skills API data adapter - normalizes API responses to UI model.
 * Tolerant to legacy fields (key/name/summary) but outputs unified format.
 */

export type SkillListItem = {
  slug: string;
  title: string;
  short: string;
  tags: string[];
};

export type SkillDetail = SkillListItem & {
  bullets: string[];
  examples: string[];
};

/**
 * Map API list response to SkillListItem array.
 * Handles both array and {items,count} shapes.
 */
export function mapList(api: any[]): SkillListItem[] {
  return (api ?? [])
    .map((x) => ({
      slug: String(x.slug ?? x.key ?? "").trim(),
      title: String(x.title ?? x.name ?? "").trim(),
      short: String(x.short ?? x.summary ?? "").trim(),
      tags: Array.isArray(x.tags) ? x.tags : [],
    }))
    .filter((x) => x.slug && x.title);
}

/**
 * Map API detail response to SkillDetail.
 * Tolerant to legacy field names.
 */
export function mapDetail(x: any): SkillDetail {
  return {
    slug: String(x.slug ?? x.key ?? "").trim(),
    title: String(x.title ?? x.name ?? "").trim(),
    short: String(x.short ?? x.summary ?? "").trim(),
    tags: Array.isArray(x.tags) ? x.tags : [],
    bullets: Array.isArray(x.bullets) ? x.bullets : [],
    examples: Array.isArray(x.examples) ? x.examples : [],
  };
}

