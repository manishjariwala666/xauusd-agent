import type { ContentItem } from "@/lib/types";
import { ContentCard } from "./content-card";

export function ContentGrid({ items, empty = "No published posts are available yet.", compact = false }: { items: ContentItem[]; empty?: string; compact?: boolean }) {
  if (!items.length) return <div className="empty-state">{empty}</div>;
  return <div className={`content-grid${compact ? " content-grid-compact" : ""}`}>{items.map((item) => <ContentCard item={item} key={item.id} />)}</div>;
}
