export function normalizeCalLink(raw: string): string {
  if (!raw) return "dmitrybond/intro-30m";
  let s = raw.trim();
  // strip protocol+host if full URL provided
  s = s.replace(/^https?:\/\/(www\.)?cal\.com\//i, "");
  // remove leading/trailing slashes
  s = s.replace(/^\/+/, "").replace(/\/+$/, "");
  return s || "dmitrybond/intro-30m";
}


