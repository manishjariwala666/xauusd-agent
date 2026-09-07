import type { ContentItem } from "@/lib/types";

type ResearchVisualInput = Pick<ContentItem, "slug" | "title" | "content_type" | "category_title" | "image_url">;

export function researchVisual(item: ResearchVisualInput): string {
  if (item.image_url) return item.image_url;
  const text = `${item.slug} ${item.title} ${item.category_title || ""} ${item.content_type}`.toLowerCase();
  if (text.includes("ai") || text.includes("artificial intelligence")) return "/images/research/ai-gold-research.svg";
  if (text.includes("astro") || text.includes("timing") || text.includes("cycle")) return "/images/research/gold-timing-context.svg";
  if (text.includes("risk") || text.includes("stop") || text.includes("invalidation")) return "/images/research/xauusd-risk-control.svg";
  return "/images/research/xauusd-market-structure.svg";
}

export function isSparseResearchBody(body?: string | null): boolean {
  const text = (body || "").replace(/[#*_>`\[\]()\-]/g, " ").replace(/\s+/g, " ").trim();
  return text.length < 900;
}
