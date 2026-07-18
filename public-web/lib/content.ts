import type { ContentItem } from "./types";

export const ARTICLE_TYPES = ["BLOG", "AI_BLOG", "ADVISORY", "ANALYSIS", "EDUCATION"];
export const PAGE_SIZE = 12;

export function articleItems(items: ContentItem[]) {
  return items.filter((item) => ARTICLE_TYPES.includes(item.content_type));
}

export function formatDate(value?: string) {
  if (!value) return "Date unavailable";
  return new Intl.DateTimeFormat("en", { day: "numeric", month: "long", year: "numeric" }).format(new Date(value));
}

export function readingMinutes(body?: string) {
  const words = (body || "").trim().split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.ceil(words / 220));
}
