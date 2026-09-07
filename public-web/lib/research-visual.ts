import type { ContentItem } from "@/lib/types";

type ResearchVisualInput = Pick<ContentItem, "slug" | "title" | "content_type" | "category_title" | "image_url">;

const GENERAL_XAUUSD_VISUALS = [
  "/images/research/xauusd-market-structure.svg",
  "/images/research/xauusd-risk-control.svg",
  "/images/research/ai-gold-research.svg",
  "/images/research/gold-timing-context.svg",
] as const;

function stableIndex(value: string, size: number) {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  return hash % size;
}

export function researchVisual(item: ResearchVisualInput): string {
  if (item.image_url) return item.image_url;

  const subject = `${item.slug} ${item.title} ${item.category_title || ""}`.toLowerCase();
  const variant = stableIndex(item.slug || item.title, GENERAL_XAUUSD_VISUALS.length);

  // Prefer the actual article subject over the broad AI_BLOG content type.
  // This prevents every AI-assisted XAUUSD article from receiving the same AI artwork.
  const hasRisk = /risk|stop[- ]?loss|invalidation|capital|reward/.test(subject);
  const hasStructure = /structure|support|resistance|trend|technical|price action/.test(subject);
  const hasTiming = /astro|timing|cycle|planet|lunar|moon/.test(subject);
  const hasAi = /artificial intelligence|\bai\b|machine learning|model/.test(subject);

  if (hasTiming) return "/images/research/gold-timing-context.svg";
  if (hasRisk && hasStructure) return variant % 2 === 0 ? "/images/research/xauusd-risk-control.svg" : "/images/research/xauusd-market-structure.svg";
  if (hasRisk) return "/images/research/xauusd-risk-control.svg";
  if (hasStructure) return variant % 2 === 0 ? "/images/research/xauusd-market-structure.svg" : "/images/research/ai-gold-research.svg";
  if (hasAi) return "/images/research/ai-gold-research.svg";

  // AI_BLOG is only a fallback signal; rotate the visual by slug so adjacent
  // articles do not look duplicated in the homepage/blog grid.
  if (item.content_type === "AI_BLOG") return GENERAL_XAUUSD_VISUALS[variant];
  return GENERAL_XAUUSD_VISUALS[variant];
}

export function isSparseResearchBody(body?: string | null): boolean {
  const text = (body || "").replace(/[#*_>`\[\]()\-]/g, " ").replace(/\s+/g, " ").trim();
  return text.length < 900;
}
