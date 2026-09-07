import type { ContentItem } from "./types";

export const ARTICLE_TYPES = ["BLOG", "AI_BLOG", "ADVISORY", "ANALYSIS", "EDUCATION"];
export const PAGE_SIZE = 12;

function normalizedTitle(value?: string | null) {
  return (value || "")
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function isPresentableArticle(item: ContentItem) {
  const title = (item.title || "").trim();
  if (title.length < 6) return false;
  return !/^(a+|test(?:ing)?|demo|sample|untitled|draft)$/i.test(title);
}

export function articleItems(items: ContentItem[]) {
  const seen = new Set<string>();
  return items.filter((item) => {
    if (!ARTICLE_TYPES.includes(item.content_type) || !isPresentableArticle(item)) return false;
    const key = normalizedTitle(item.title) || item.slug;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function formatDate(value?: string) {
  if (!value) return "Date unavailable";
  return new Intl.DateTimeFormat("en", { day: "numeric", month: "long", year: "numeric" }).format(new Date(value));
}

export function readingMinutes(body?: string) {
  const words = (body || "").trim().split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.ceil(words / 220));
}
